from typing import Union
from transformers import PreTrainedTokenizerFast, PreTrainedTokenizer
import torch
import threading

from .hash_fn import Hash1
from .wm_arg_class import WmBaseArgs

HfTokenizer = Union[PreTrainedTokenizerFast, PreTrainedTokenizer]

import torch.nn.functional as F
from pygments.lexers import PythonLexer, GoLexer, JavaLexer, JavascriptLexer, PhpLexer
from pygments.token import  STANDARD_TYPES


class PDAMessageModel():
    _token_type_cache = {}
    _token_type_cache_lock = threading.Lock()

    def __init__(self, tokenizer: HfTokenizer, pda_model,
                 delta, seed=42, lm_topk=1000, message_code_len=10,
                 random_permutation_num=100, hash_prefix_len=1, hash_fn=Hash1,
                 language=None, device=None):
        self.tokenizer = tokenizer
        self.delta = delta
        self.message_code_len = message_code_len
        self.language = str(language or WmBaseArgs.language).strip().lower()
        self._device = torch.device(device or WmBaseArgs.device)
        lexer_types = {
            "python": PythonLexer,
            "go": GoLexer,
            "java": JavaLexer,
            "javascript": JavascriptLexer,
            "php": PhpLexer,
        }
        if self.language not in lexer_types:
            raise ValueError(f"unsupported CodeIP PDA language: {self.language}")
        self.lexer = lexer_types[self.language]()
        self.nonterminal2id = {nonterminal: i for i, nonterminal in enumerate(STANDARD_TYPES.values())}
        cache_key = (id(tokenizer), self.language, int(tokenizer.vocab_size))
        with self._token_type_cache_lock:
            cached_entry = self._token_type_cache.get(cache_key)
        cached_token_types = (
            cached_entry[1]
            if cached_entry is not None and cached_entry[0] is tokenizer
            else None
        )
        if cached_token_types is None:
            cached_token_types = self.construct_lex_and_tokenizer_id_list()
            with self._token_type_cache_lock:
                cached_entry = self._token_type_cache.setdefault(
                    cache_key, (tokenizer, cached_token_types)
                )
                cached_token_types = cached_entry[1]
        self.lex_and_tokenizer_id_list = cached_token_types
        self.max_vocab_size = 100000
        self.pda_model = pda_model


    @property
    def random_delta(self):
        return self.delta * 1.

    @property
    def device(self):
        return self._device

    def set_random_state(self):
        pass
    
    def construct_lex_and_tokenizer_id_list(self):
        lex_and_tokenizer_id_list = [set() for i in range(len(self.nonterminal2id))]
        for i in range(self.tokenizer.vocab_size):
            v = self.tokenizer.decode([i])
            tokens = self.lexer.get_tokens(v)
            for token in tokens:
                token_type, value = token
                lex_and_tokenizer_id_list[self.nonterminal2id[STANDARD_TYPES[token_type]]].add(i)

        return lex_and_tokenizer_id_list
    
    def get_pda_predictions(self, strings):
        tokens = self.lexer.get_tokens(strings[0])
        lex_array = [self.nonterminal2id[STANDARD_TYPES[token_type]] for token_type, value in tokens]
        lex_array = torch.tensor([lex_array]).to(self._device)
        score = self.pda_model(lex_array)
        output_probs = F.log_softmax(score, dim=1)
        predicted_class = torch.argmax(output_probs, dim=1)      
        return predicted_class
        


    def cal_addition_scores(self, x_prefix: torch.LongTensor, 
                   lm_predictions, scores: torch.Tensor, gamma
                   ):
        selected_idx = list(self.lex_and_tokenizer_id_list[lm_predictions])
        scores[:, selected_idx] += gamma
        return scores
