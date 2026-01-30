import os
# os.chdir("/home/zrz/Projects/Code_Watermark/SrcMarker")
import copy
import json
import time
import torch
import pickle
import random
import tree_sitter
from tqdm import tqdm
from collections import defaultdict
from argparse import ArgumentParser
from torch.utils.data import DataLoader

from models import (
    ConcatApproximator,
    TransformSelector,
    TransformerEncoderExtractor,
    GRUEncoder,
    ExtractGRUEncoder,
    WMLinearEncoder,
    MLP2,
)

from data_processing import CodeVocab
from metrics import calc_code_bleu
from metrics.syntax_match import check_tree_validity
from code_tokenizer import tokens_to_strings
from eval_utils import JitAdversarialTransformProvider, compute_msg_acc
from code_transform_provider import CodeTransformProvider
from runtime_data_manager import InMemoryJitRuntimeDataManager
from data_processing import JsonlWMDatasetProcessor_obfus, DynamicWMCollator
from logger_setup import setup_evaluation_logger
import mutable_tree.transformers as ast_transformers


def parse_args_for_evaluation():
    parser = ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=["github_c_funcs", "github_java_funcs", "csn_java", "csn_js"],
        default="github_c_funcs",
    )
    parser.add_argument("--lang", choices=["cpp", "java", "javascript"], default="c")
    parser.add_argument("--dataset_dir", type=str, default="./datasets/github_c_funcs")
    parser.add_argument("--n_bits", type=int, default=4)
    parser.add_argument("--checkpoint_path", type=str, default="./ckpts/something.pt")
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--trans_adv", action="store_true")
    parser.add_argument("--n_trans_adv", type=int, default=1)

    parser.add_argument("--var_adv", action="store_true")
    parser.add_argument("--var_nomask", action="store_true")
    parser.add_argument("--varmask_prob", type=float, default=0.5)
    parser.add_argument("--var_adv_proportion", type=float, default=None)
    parser.add_argument("--var_adv_budget", type=int, default=None)

    parser.add_argument("--all_adv", action="store_true")

    parser.add_argument("--model_arch", choices=["gru", "transformer"], default="gru")
    parser.add_argument("--shared_encoder", action="store_true")

    parser.add_argument(
        "--var_transform_mode", choices=["replace", "append"], default="replace"
    )

    parser.add_argument("--output_dir", type=str, default="./results_obfus")
    
    parser.add_argument("--output_filename", type=str)
    return parser.parse_args()

def write_to_file(file: str, filtered_data: list):
    """将筛选后的数据写入临时文件"""
    with open(file, 'w', encoding='utf-8') as file:
        for item in filtered_data:
            json_data = json.dumps(item, ensure_ascii=False)
            file.write(json_data + '\n')

def main(args):
    logger = setup_evaluation_logger(args)
    logger.info(args)

    LANG = args.lang
    DATASET = args.dataset
    DATASET_DIR = args.dataset_dir
    N_BITS = args.n_bits
    CKPT_PATH = args.checkpoint_path
    DEVICE = torch.device("cuda")
    MODEL_ARCH = args.model_arch
    SHARED_ENCODER = args.shared_encoder
    RANDOM_MASK = not args.var_nomask
    VAR_MASK_PROB = args.varmask_prob
    VAR_TRANSFORM_MODE = args.var_transform_mode
    OUTPUT_DIR = os.path.join(args.output_dir, args.lang)
    DESTFILE_NAME = args.output_filename
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # seed
    SEED = args.seed
    random.seed(SEED)
    torch.manual_seed(SEED)

    PARSER_LANG = tree_sitter.Language("parser/languages.so", args.lang)
    ts_parser = tree_sitter.Parser()
    ts_parser.set_language(PARSER_LANG)
    code_transformers = [
        ast_transformers.IfBlockSwapTransformer(),
        ast_transformers.CompoundIfTransformer(),
        ast_transformers.ConditionTransformer(),
        ast_transformers.LoopTransformer(),
        ast_transformers.InfiniteLoopTransformer(),
        ast_transformers.UpdateTransformer(),
        ast_transformers.SameTypeDeclarationTransformer(),
        ast_transformers.VarDeclLocationTransformer(),
        ast_transformers.VarInitTransformer(),
        ast_transformers.VarNameStyleTransformer(),
    ]

    transform_computer = CodeTransformProvider(LANG, ts_parser, code_transformers)
    adv = JitAdversarialTransformProvider(
        transform_computer,
        transforms_per_file=f"./datasets/transforms_per_file_{DATASET}.json",
        varname_path=f"./datasets/variable_names_{DATASET}.json",
        lang=LANG,
    )

    dataset_processor = JsonlWMDatasetProcessor_obfus(LANG)

    checkpoint_dict = torch.load(CKPT_PATH, map_location="cpu")
    vocab: CodeVocab = checkpoint_dict["vocab"]
    test_instances = dataset_processor.load_jsonl(DATASET_DIR, split="obfus")
    obfus_test_objs = dataset_processor.load_raw_jsonl(DATASET_DIR, split="obfus")
    test_dataset = dataset_processor.build_dataset(test_instances, vocab)
    new_test_objs = []
    adv_test_objs = []

    print(f"Vocab size: {len(vocab)}")
    print(f"Test size: {len(test_dataset)}")
    print(f"  Original test size: {len(test_instances)}")

    if VAR_TRANSFORM_MODE == "replace":
        vmask = vocab.get_valid_identifier_mask()
    else:
        vmask = vocab.get_valid_highfreq_mask(2**N_BITS * 32)

    print(f"  invalid mask size: {sum(vmask)}")
    print(f"  valid size: {len(vmask) - sum(vmask)}")

    transform_manager = InMemoryJitRuntimeDataManager(
        transform_computer, test_instances, LANG
    )
    transform_manager.register_vocab(vocab)
    transform_manager.load_transform_mask(
        f"./datasets/feasible_transform_{DATASET}.json"
    )
    transform_manager.load_varname_dict(f"./datasets/variable_names_{DATASET}.json")
    transform_capacity = transform_manager.get_transform_capacity()
    print(f"Transform capacity: {transform_capacity}")

    # build models
    print("building models")
    test_loader = DataLoader(
        test_dataset, batch_size=1, shuffle=False, collate_fn=DynamicWMCollator(N_BITS)
    )

    logger.info(f"Using {MODEL_ARCH}")
    if MODEL_ARCH == "gru":
        FEATURE_DIM = 768
        encoder = GRUEncoder(
            vocab_size=len(vocab), hidden_size=FEATURE_DIM, embedding_size=FEATURE_DIM
        )
    elif MODEL_ARCH == "transformer":
        FEATURE_DIM = 768
        encoder = TransformerEncoderExtractor(
            vocab_size=len(vocab), embedding_size=FEATURE_DIM, hidden_size=FEATURE_DIM
        )

    selector = TransformSelector(
        vocab_size=len(vocab),
        transform_capacity=transform_capacity,
        input_dim=FEATURE_DIM,
        vocab_mask=vmask,
        random_mask_prob=VAR_MASK_PROB,
    )
    approximator = ConcatApproximator(
        vocab_size=len(vocab),
        transform_capacity=transform_capacity,
        input_dim=FEATURE_DIM,
        output_dim=FEATURE_DIM,
    )
    wm_encoder = WMLinearEncoder(N_BITS, embedding_dim=FEATURE_DIM)
    wm_decoder = MLP2(output_dim=N_BITS, bn=False, input_dim=FEATURE_DIM)
    extract_encoder = None

    print(f"loading checkpoint from {CKPT_PATH}")
    ckpt_save = torch.load(CKPT_PATH, map_location="cpu")
    encoder.load_state_dict(ckpt_save["model"])
    if extract_encoder is not None:
        extract_encoder.load_state_dict(ckpt_save["extract_encoder"])
    wm_encoder.load_state_dict(ckpt_save["wm_encoder"])
    wm_decoder.load_state_dict(ckpt_save["wm_decoder"])
    selector.load_state_dict(ckpt_save["selector"])
    approximator.load_state_dict(ckpt_save["approximator"])

    tot_params = sum([p.numel() for p in encoder.parameters()])
    print(f"Total parameters: {tot_params:,}")

    encoder.to(DEVICE)
    if extract_encoder is not None:
        extract_encoder.to(DEVICE)
    selector.to(DEVICE)
    approximator.to(DEVICE)
    wm_encoder.to(DEVICE)
    wm_decoder.to(DEVICE)

    encoder.eval()
    if extract_encoder is not None:
        extract_encoder.eval()
    selector.eval()
    approximator.eval()
    wm_encoder.eval()
    wm_decoder.eval()

    n_samples = 0
    tot_acc = 0
    sadv_acc = 0
    vadv_acc = 0
    dcadv_acc = 0

    tot_msg_acc = 0
    sadv_msg_acc = 0
    vadv_msg_acc = 0
    dcadv_msg_acc = 0

    tot_embed_time = 0
    tot_extract_time = 0

    codebleu_res = defaultdict(int)
    adv_codebleu_res = defaultdict(int)
    repo_wise = DATASET in {"csn_java", "csn_js"}  # only for csn datasets
    repowise_long_msg = defaultdict(list)
    repowise_long_gt = defaultdict(list)
    repowise_long_msg_adv = defaultdict(list)

    valid_t = 0
    valid_all = len(test_dataset)

    print("beginning evaluation")
    
    results = []
    # eval starts from here
    with torch.no_grad():
        prog = tqdm(test_loader)
        for bid, batch in enumerate(prog):
            test_obj = copy.deepcopy(obfus_test_objs[bid])
            # print("obj is:" + test_obj)
            
            repo = test_obj["repo"] if "repo" in test_obj else None

            (x, lengths, src_mask, instance_ids, wms, wmids) = batch
            wms = wms.float()

            x = x.to(DEVICE)
            wms = wms.to(DEVICE)
            wmids = wmids.to(DEVICE)
            src_mask = src_mask.to(DEVICE)

            # 提取原始代码实例
            ori_instances = transform_manager.get_original_instances(instance_ids)
            if not ori_instances[0].source:
                continue
            # print("instance is:" + str(ori_instances[0].source))
            
            # 加载转换后的代码到张量
            dec_x, dec_l, dec_m = transform_manager.load_to_tensor(ori_instances)
            dec_x = dec_x.to(DEVICE)
            dec_m = dec_m.to(DEVICE)

            extract_start = time.time()
            if extract_encoder is not None:
                t_features = extract_encoder(dec_x, dec_l, dec_m)
            else:
                t_features = encoder(dec_x, dec_l, dec_m)
            outputs = wm_decoder(t_features)
            probs = torch.sigmoid(outputs)
            preds = (probs > 0.5).long()
            extract_time = time.time() - extract_start

            tot_extract_time += extract_time
            tot_acc += torch.sum(torch.mean((preds == wms).float(), dim=1)).item()
            tot_msg_acc += compute_msg_acc(preds, wms, n_bits=args.n_bits)

            if repo_wise:
                repowise_long_msg[repo].extend(preds[0].tolist())
                repowise_long_gt[repo].extend(wms[0].long().tolist())

            # 更新提取结果
            test_obj["obfus_extract"] = preds[0].tolist()
            # json_item = json.dumps(test_obj, ensure_ascii=False)
            results.append(test_obj)
    
    file_path = os.path.join(OUTPUT_DIR, DESTFILE_NAME)
    write_to_file(file_path, results)


if __name__ == "__main__":
    args = parse_args_for_evaluation()
    main(args)