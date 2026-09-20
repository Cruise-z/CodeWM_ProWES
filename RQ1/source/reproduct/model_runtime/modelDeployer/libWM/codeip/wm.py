import json
import os.path
from pathlib import Path

import torch
from tqdm import tqdm
from typing import List
from datasets import load_from_disk, load_dataset, Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import LogitsProcessorList, MinLengthLogitsProcessor, NoRepeatNGramLogitsProcessor, RepetitionPenaltyLogitsProcessor
from .wm_arg_class import WmBaseArgs
from .message_model_processor import WmProcessorRandomMessageModel
from .message_model import RandomMessageModel

from .PDA_model_processor import PDAProcessorMessageModel
from .PDA_message_model import PDAMessageModel
import torch.nn as nn

ROOT_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def truncate(d, max_length=200):
    for k, v in d.items():
        if isinstance(v, torch.Tensor) and len(v.shape) == 2:
            d[k] = v[:, :max_length]
    return d


def main(args: WmBaseArgs):
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForCausalLM.from_pretrained(args.model_name)

    model = model.to(args.device)
    lm_tokenizer = tokenizer

    class LSTMModel(nn.Module):
        def __init__(self, vocab_size, embed_size, hidden_size, output_size):
            super(LSTMModel, self).__init__()
            self.embedding = nn.Embedding(vocab_size, embed_size)
            self.lstm = nn.LSTM(embed_size, hidden_size, batch_first=True)
            self.fc = nn.Linear(hidden_size, output_size)

        def forward(self, x):
            embedded = self.embedding(x)  
            _, (hn, cn) = self.lstm(embedded)
            output = self.fc(hn[-1, :, :])
            return output
        
    seq_length = 30
    vocab_size = 79
    embed_size = 128
    hidden_size = 256
    output_size = vocab_size
    batch_size = 128

    lstm_model = LSTMModel(vocab_size, embed_size, hidden_size, output_size)

    checkpoint_path = (
        Path(__file__).resolve().parent
        / "checkpoints"
        / f"lstm_model_{args.language}.pth"
    )
    lstm_model.load_state_dict(
        torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    )
    lstm_model.to(args.device)

    # Use the allenai/c4 hub dataset with current datasets releases.
    # The first run downloads the dataset and may take considerable time.
    
    # Select the dataset from the command-line configuration.
    if args.dataset_name == 'codebleu':
        # Load CodeBLEU from the Hugging Face Hub for the requested language.
        try:
            codebleu_dataset = load_dataset('neulab/codebleu', args.language, split='train', streaming=True)
        except:
            # Try the CodeSearchNet source if the primary dataset is unavailable.
            print(f"Warning: Could not load 'neulab/codebleu' for language '{args.language}'")
            print("Trying alternative CodeBLEU dataset source...")
            try:
                codebleu_dataset = load_dataset('code_search_net', args.language, split='train', streaming=True)
            except:
                print("Failed to load CodeBLEU dataset, falling back to C4")
                codebleu_dataset = None

        if codebleu_dataset is not None:
            # Materialize an indexable subset.
            codebleu_list = []
            for i, sample in enumerate(codebleu_dataset):
                if i >= args.sample_num:
                    break
                codebleu_list.append(sample)

            if not codebleu_list:
                print("No samples found in CodeBLEU dataset, falling back to C4")
                codebleu_dataset = None
            else:
                # Convert the list to Dataset form and resolve common code fields.
                first_sample = codebleu_list[0]
                if 'code' in first_sample:
                    code_field = 'code'
                elif 'func' in first_sample:
                    code_field = 'func'
                elif 'text' in first_sample:
                    code_field = 'text'
                elif 'whole_func_string' in first_sample:  # CodeSearchNet
                    code_field = 'whole_func_string'
                elif 'func_code_string' in first_sample:  # CodeSearchNet
                    code_field = 'func_code_string'
                else:
                    # Print available fields for diagnostics.
                    print(f"Available fields in dataset: {list(first_sample.keys())}")
                    # Try common code-field names.
                    for field in ['code', 'func', 'text', 'content', 'body', 'whole_func_string', 'func_code_string']:
                        if field in first_sample:
                            code_field = field
                            break
                    else:
                        print("Could not find code field in dataset, falling back to C4")
                        codebleu_dataset = None
                        codebleu_list = []

                if codebleu_list:
                    c4_sliced_and_filted = Dataset.from_dict({
                        'original_string': [item[code_field] for item in codebleu_list]
                    })
                else:
                    # Fall back to C4.
                    c4_sliced_and_filted = load_dataset('allenai/c4', 'en', split='train', streaming=True)
                    c4_list = []
                    for i, sample in enumerate(c4_sliced_and_filted):
                        if i >= args.sample_num:
                            break
                        c4_list.append(sample)
                    c4_sliced_and_filted = Dataset.from_dict({
                        'original_string': [item['text'] for item in c4_list]
                    })
        else:
            # Fall back to C4.
            c4_sliced_and_filted = load_dataset('allenai/c4', 'en', split='train', streaming=True)
            c4_list = []
            for i, sample in enumerate(c4_sliced_and_filted):
                if i >= args.sample_num:
                    break
                c4_list.append(sample)
            c4_sliced_and_filted = Dataset.from_dict({
                'original_string': [item['text'] for item in c4_list]
            })
    else:
        # Use C4 by default.
        c4_sliced_and_filted = load_dataset('allenai/c4', 'en', split='train', streaming=True)

        # Materialize an indexable subset from the streaming dataset.
        c4_list = []
        for i, sample in enumerate(c4_sliced_and_filted):
            if i >= args.sample_num:
                break
            c4_list.append(sample)

        # Convert the list back to Dataset form.
        c4_sliced_and_filted = Dataset.from_dict({
            'original_string': [item['text'] for item in c4_list]
        })

    lm_message_model = RandomMessageModel(tokenizer=tokenizer,
                                          lm_tokenizer=lm_tokenizer,
                                          delta=args.delta,
                                          message_code_len=args.message_code_len,
                                          device=model.device,
                                          )

    watermark_processor = WmProcessorRandomMessageModel(message_model=lm_message_model,
                                                        tokenizer=tokenizer,
                                                        encode_ratio=args.encode_ratio,
                                                        message=args.message,
                                                        top_k=args.top_k,
                                                        )

    min_length_processor = MinLengthLogitsProcessor(min_length=10000,
                                                    eos_token_id=tokenizer.eos_token_id)
    # Keep eos_token_id on the model device.
    if hasattr(min_length_processor, 'eos_token_id'):
        min_length_processor.eos_token_id = torch.tensor(min_length_processor.eos_token_id, device=model.device)
    rep_processor = RepetitionPenaltyLogitsProcessor(penalty=args.repeat_penalty)

    ngram_processor = NoRepeatNGramLogitsProcessor(ngram_size=args.ngram_size) 

    pda_model = PDAMessageModel(
        tokenizer=tokenizer,
        pda_model=lstm_model,
        delta=args.delta,
        language=args.language,
        device=args.device,
    )
    
    pda_processor = PDAProcessorMessageModel(message_model=pda_model,tokenizer=tokenizer, gamma=args.gamma)

    # Select whether to enable the PDA predictor.
    if args.use_pda:
        logit_processor = LogitsProcessorList(
            [min_length_processor, rep_processor, ngram_processor, watermark_processor, pda_processor])
    else:
        logit_processor = LogitsProcessorList(
            [min_length_processor, rep_processor, ngram_processor, watermark_processor])

    results = {
        'text': [],
        'prefix_and_output_text': [],
        'output_text': [],
        'reference_text': [],  # Ground-truth continuation aligned with output_text.
        'decoded_message': [],
        'acc': []
    }

    try:
        for text in tqdm(c4_sliced_and_filted["original_string"]):
            # Use one tokenization configuration throughout.
            full = tokenizer(text, return_tensors="pt", add_special_tokens=False)
            full_ids = full["input_ids"][0]  # shape: [T]

            # Resolve prompt length in the full-token coordinate system.
            prompt_len = min(int(args.prompt_length), full_ids.size(0))

            # Slice the reference continuation in the same coordinate system.
            ref_ids = full_ids[prompt_len : prompt_len + int(args.generated_length)]
            reference_text = tokenizer.decode(ref_ids, skip_special_tokens=True)

            # Slice the prompt directly without a second tokenize/truncate pass.
            input_ids = full_ids[:prompt_len].unsqueeze(0).to(model.device)
            attention_mask = torch.ones_like(input_ids, device=model.device)

            tokenized_input = {"input_ids": input_ids, "attention_mask": attention_mask}

            watermark_processor.start_length = prompt_len
            output_tokens = model.generate(
                **tokenized_input,
                temperature=args.temperature,
                max_new_tokens=args.generated_length,
                num_beams=args.num_beams,
                logits_processor=logit_processor,
            )

            output_text = tokenizer.batch_decode(
                output_tokens[:, prompt_len:],
                skip_special_tokens=True
            )[0]

            prefix_and_output_text = tokenizer.batch_decode(
                output_tokens,
                skip_special_tokens=True
            )[0]

            results["text"].append(text)
            results["output_text"].append(output_text)
            results["prefix_and_output_text"].append(prefix_and_output_text)
            results["reference_text"].append(reference_text)

            decoded_message = watermark_processor.decode(output_text, disable_tqdm=True)[0]
            available_message_num = args.generated_length // (int(args.message_code_len * args.encode_ratio))
            acc = decoded_message[:available_message_num] == args.message[:available_message_num]

            results['decoded_message'].append(decoded_message)
            results['acc'].append(acc)

            print(prefix_and_output_text)
            print(decoded_message, acc)
            torch.cuda.empty_cache()

    except KeyboardInterrupt:
        pass

    args_dict = vars(args)
    results['args'] = args_dict
    with open(args.save_path, 'w') as f:
        json.dump(results, f, indent=4)
