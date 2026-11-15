import os
import re
import random
import socket
import copy  
import string

from logger import logger
from FlintParser import FlintParser
from storage.dataset import DatasetStorage

class FlintNPC:
    """
    FlintNPC - Giovanni Blu Mitolo 2026 (see LICENSE for licensing details) 
    
    This is a for creating ultra-lightweight NLU agents. 
    It has very low latency, minimal memory footprint and supports native 
    execution on operating systems.
    
    It adheres to NDF 0.0 (NPC-Forge Dataset Format) and supports tool 
    calls and thinking mode. 
    
    FlintNPC implements a novel deterministic approach to achieve 
    NLU (Natural Language Understanding) and intent resolution:
    
    1. Raw text sanitization (strips insults, emojis, interjections)
    2. Deterministic exact match lookup using bare string comparison
       A successful match triggers sentiment analysis and intent resolution
    3. If the exact match fails, the prompt is processed as a 
       semantic map, extracting arguments if present (template matching).
    4. If Template matching fails, the prompt is processed as
       a BOW (Bag of Words), ignoring order and estimating similarity by 
       computing word matches and Levenshtein distance to accommodate typos
    """
    
    _ctx_word_idx = {}
    _ctx_tag_idx = {}
    
    SENTIMENT_KEYS = (
        "expletives", "interjections", "thanking_words",
        "encouraging_words", "discouraging_words",
    )

    POSITIVE_CATEGORIES = ["encouraging_words", "discouraging_words", "thanking_words"]
    
    def __init__(self, npc_name, log_level="INFO"):
        logger.setLevel(log_level)
        self.name = npc_name
        
        npc_dir = f"npcs/{npc_name}"
        dataset_dir = f"{npc_dir}/dataset"
        vocab_dir = os.path.join(dataset_dir, "vocabulary")
        self.storage = DatasetStorage()
        self.config = self.storage.load_json(npc_dir, "config.json") or {}
        self.variable_types = self.storage.load_json(dataset_dir, "types.json") or {}
        self.templates_vocabulary = self.storage.load_json(vocab_dir, "templates.json") or {}
        self.vocabulary = self.storage.load_json(vocab_dir, "vocabulary.json") or {}
        
        self.dataset, self.personality, self.templates = [], [], []
        self.exact_match_map, self.metadata = {}, {}
        self.active_context_map = {}
        self._precomputed_context_intents = {}
        
        self.sentiment = {
            k: 0 for k in [
                "expletives", 
                "interjections", 
                "thanking_words", 
                "encouraging_words", 
                "discouraging_words"
            ]
        }
        
        self.rejection = {"output": ["<||unknown||>"], "permission": "yolo"}
        self.threshold = float(self.config.get("threshold", 0.75))
        
        self.load_data(dataset_dir)
        
        self.nlp = FlintParser(
            self.name, 
            self.vocabulary,
            self.templates,
            self.templates_vocabulary,
            self.variable_types,
            log_level,
            [
                block for block in self.dataset + self.personality if isinstance(
                    block, dict
                ) and "input" in block
            ]
        )
        
        self._build_intent_signatures()

    def load_data(self, dataset_dir):
        self.personality = self.storage.load_json(dataset_dir, "personality.json") or []
        self.dataset = self.storage.load_json_recursive(dataset_dir, "dataset_*")
        self.templates = self.storage.load_json_recursive(dataset_dir, "templates_*")
    
        v_lists = [
            "expletives", 
            "interjection", 
            "thanking_words", 
            "encouraging_words", 
            "discouraging_words", 
            "greetings"
        ]
        
        for v_file in v_lists:
            base_name = v_file.replace("_words", "")
            data_list = self.vocabulary.get(v_file, [])
            setattr(self, f"{base_name}_list", data_list)
            if data_list:
                self.metadata[v_file] = data_list
                self.metadata[base_name] = data_list
            
        for block in self.dataset + self.personality + self.templates:
            if isinstance(block, dict):
                for k, v in block.items():
                    if k not in ["input"]: 
                        self.metadata[k] = v

        self.metadata.update({
            "username": str(os.environ.get("USER", "user")),
            "npc_name": str(self.config.get("name", "NPC")),
            "response_classes": str(len(self.dataset + self.personality + self.templates)),
            "computer_name": str(socket.gethostname()),
            "creation_date": str(self.config.get("creation_date", "2026-07-12")),
            "creator": str(self.config.get("creator", "Unknown")),
        })

        for block in self.dataset + self.personality + self.templates:
            if isinstance(block, dict) and "input" in block:
                for inp in block["input"]:
                    self.exact_match_map[str(inp).lower().strip()] = block
        
        logger.info(f"[FlintNPC.py][{self.name}][load_data] Engine initialized.")

    def _build_signatures(self, match_map):
        syn_w = float(self.config.get("synonym_contribution", 0.0))
        sigs, word_idx, tag_idx = {}, {}, {}
        for order, (inp, block) in enumerate(match_map.items()):
            sig = self.nlp.precompute_intent_signature(inp, block, syn_w)
            sig["_order"] = order
            sigs[inp] = sig
            seen = set()
            for t in sig["tokens"]:
                if t not in seen:
                    seen.add(t)
                    word_idx.setdefault(t, []).append(sig)
            for t in sig["tag_set"]:
                tag_idx.setdefault(t, []).append(sig)
        return sigs, word_idx, tag_idx

    def _build_intent_signatures(self):
        self._precomputed_intents, self._word_idx, self._tag_idx = \
            self._build_signatures(self._get_merged_match_map())

    def update_context(self, block):
        if "context" not in block:
            return
        self.active_context_map = {}
        if isinstance(block["context"], list):
            for cb in block["context"]:
                if isinstance(cb, dict) and "input" in cb:
                    for inp in cb["input"]:
                        self.active_context_map[str(inp).lower().strip()] = cb
        self._precomputed_context_intents, self._ctx_word_idx, self._ctx_tag_idx = \
            self._build_signatures(self.active_context_map)

    def _match_exact(self, key):
        """Live lookup; context overrides exact. Returns (block, is_context)."""
        if key in self.active_context_map:
            return self.active_context_map[key], True
        if key in self.exact_match_map:
            return self.exact_match_map[key], False
        return None, False

    def _get_merged_match_map(self):
        # only used to build signatures (init / context change) — always fresh
        return {**self.exact_match_map, **self.active_context_map}

    def _candidates(self, sigs, word_idx, tag_idx, rarest_word):
        if not rarest_word: return list(sigs.values())
        seen, out = set(), []
        tag = self.nlp._synonym_map.get(rarest_word)
        for sig in word_idx.get(rarest_word, []) + (tag_idx.get(tag, []) if tag else []):
            if id(sig) not in seen:
                seen.add(id(sig)); out.append(sig)
        out.sort(key=lambda s: s["_order"])
        return out
    
    def _fuzzy_best(self, query_tokens, sigs, word_idx, tag_idx, cutoff, rarest_word):
        q = len(query_tokens)
        if not q: return None, -1.0
        eps = float(self.config.get("tie_break_epsilon", 0.05))
        scored, best = [], -1.0
        for sig in self._candidates(sigs, word_idx, tag_idx, rarest_word):
            t = sig.get("token_count", 0)
            if not t: continue
            bound = sig["max_weight_sums"][min(q, t) - 1] / sig["max_score"]
            if bound < cutoff or bound < best - eps: continue
            score, matched = self.nlp._score_and_matched(query_tokens, sig, cutoff)
            if score > best: best = score
            scored.append((score, matched, sig))
        if not scored or best < cutoff: return None, best
        floor = max(cutoff, best - eps)
        pool = [x for x in scored if x[0] >= floor]
        if not pool: return None, best
        pool.sort(key=lambda x: (x[1], x[0], -x[2]["_order"]), reverse=True)
        score, matched, sig = pool[0]
        return sig["block"], score

    def process_message(self, user_prompt: str):
        logger.info(f"[FlintNPC.py][{self.name}][process_message] Prompt: {user_prompt}")
        self.sentiment = {k: 0 for k in self.SENTIMENT_KEYS}          # FIX #8
        stripped, _ = self.nlp.strip_and_sentiment(
            user_prompt, self.vocabulary, self.sentiment, ["expletives", "interjections"])

        lookup = stripped.lower().strip()
        block, is_ctx = self._match_exact(lookup)
        if block is None:
            block, is_ctx = self._match_exact(lookup.rstrip(string.punctuation).strip())
        if block is not None:
            status = "context match" if is_ctx else "exact match"
            self.update_context(block)
            self.nlp.strip_and_sentiment(stripped, self.vocabulary, self.sentiment, self.POSITIVE_CATEGORIES)
            return self.generate_response(block, {}, 1.0, status)

        structure, slots = self.nlp.parse_structure(user_prompt, self.threshold)   # template BEFORE gate
        matched_template = self.nlp.match_structure(self.templates, structure)
        if matched_template:
            logger.info(f"[Template Match] {matched_template.get('intent')}")
            self.update_context(matched_template)
            cum = dict(slots)
            if "content" not in cum and "string" in cum:
                cum["content"] = cum["string"]
            self.nlp.strip_and_sentiment(user_prompt, self.vocabulary, self.sentiment)
            return self.generate_response(matched_template, cum, 1.0, "template match")

        rarest_word = self.nlp.get_rarest_word(user_prompt)             # gate only guards fuzzy
        if not rarest_word:
            return self.generate_response(self.rejection, {}, 0.0, "rejected")

        clean, _ = self.nlp.strip_and_sentiment(stripped, self.vocabulary, self.sentiment, self.POSITIVE_CATEGORIES)
        
        query_tokens = clean.lower().split()
        
        block, score = self._fuzzy_best(query_tokens, self._precomputed_context_intents,
                                        self._ctx_word_idx, self._ctx_tag_idx, self.threshold, None)
        if score >= self.threshold:
            self.update_context(block)
            return self.generate_response(block, {}, score, "probabilistic match")

        block, score = self._fuzzy_best(query_tokens, self._precomputed_intents,
                                        self._word_idx, self._tag_idx, self.threshold, rarest_word)
        if score >= self.threshold and block:
            self.update_context(block)
            return self.generate_response(block, {}, score, "probabilistic match")

        min_rel = 0.25
        q = len(query_tokens)
        max_scored = int(self.config.get("max_suggestions_scored", 200))
        pool = []
        for sig in self._candidates(self._precomputed_intents, self._word_idx, self._tag_idx, rarest_word):
            t = sig.get("token_count", 0)
            if not q or not t: continue
            bound = sig["max_weight_sums"][min(q, t) - 1] / sig["max_score"]
            if bound < min_rel: continue
            pool.append((bound, sig))
        pool.sort(key=lambda x: -x[0])
        top = []
        for bound, sig in pool[:max_scored]:
            score = self.nlp.fast_score_calculation(query_tokens, sig, min_rel)
            if score >= min_rel: top.append((score, sig["token_count"], sig["block"]))
        top.sort(key=lambda x: (-x[0], x[1]))
        related, seen = [], set()
        max_sug = int(self.config.get("suggestions", 5))
        for score, t, block in top:
            inputs = block.get("input", [])
            sig_key = str(inputs[0]).lower() if inputs and isinstance(inputs, list) else str(block)
            if sig_key not in seen: related.append(block); seen.add(sig_key)
            if len(related) >= max_sug: break
        return self.generate_response(self.rejection, {}, 0.0, "rejected", related)
    
    def process_messages(self, user_prompt: str):
        parts = re.split(r"(<\|\|.*?\|\|>|\"[^\"\\]*(?:\\.[^\"\\]*)*\"|'.*?')", user_prompt)
        segments, buf = [], ""
        for i, part in enumerate(parts):
            if i % 2 == 1: buf += part
            else:
                pieces = re.split(r"\n+|\d+\)|[;!?]", part)
                for j, pc in enumerate(pieces):
                    if j == 0: buf += pc
                    else: segments.append(buf); buf = pc
        segments.append(buf)
        sub_prompts = [s.strip() for s in segments if s.strip()]
        if not sub_prompts:
            return self.generate_response(self.rejection, {}, 0.0, "rejected")

        responses, tools, descs, statuses, perms = [], [], [], [], []
        merged_slots = {}
        lowest = 1.0
        agg = {k: 0 for k in self.sentiment}
        for sp in sub_prompts:
            res = self.process_message(sp)
            conf = res.get("confidence", 0.0)
            if conf < self.threshold or res.get("status") == "rejected":
                logger.warning(f"[FlintNPC.py][{self.name}][process_messages] Rejected '{sp}', confidence {conf:.4f}")
                return self.generate_response(self.rejection, {}, 0, "rejected", res.get("related", []))
            lowest = min(lowest, conf)
            merged_slots.update(res.get("slots", {}))          # FIX #14
            if "response" in res: responses.append(res["response"])
            if "tools" in res: tools.append(res["tools"])
            if "description" in res: descs.append(res["description"])
            if "status" in res: statuses.append(res["status"])
            if "permission" in res: perms.append(res["permission"])
            for k in agg:
                agg[k] += self.sentiment.get(k, 0)
        status = statuses[0] if statuses and all(s == statuses[0] for s in statuses) else ", ".join(statuses)
        permission = ""
        for p in perms:
            p = str(p).lower().strip()
            if p == "ask":
                permission = "ask"
            elif p in ("yolo", "auto") and permission != "ask":
                permission = p
        permission = permission or "ask"
        out = dict(res)
        out.update({
            "description": " ".join(descs), "tools": tools,
            "response": " ".join(responses), "confidence": lowest,
            "status": status, "permission": permission,
            "sentiment": agg, "slots": merged_slots,
        })
        logger.info(f"[FlintNPC.py][{self.name}][process_messages] Output: '{out['response']}'")
        return out

    def generate_response(self, block, slots, confidence, status, related=None):
        if related is None: related = []
        if not block:
            return {
                "status": status, 
                "confidence": confidence, 
                "response": "Intent not understood.", 
                "slots": slots, 
                "sentiment": self.sentiment
            }
            
        def render_tags(text):
            if not text: return ""
            text = str(text)
            
            def replacer(match):
                tag = match.group(1)
                if tag in ("completion", "unknown", "related") and tag not in slots:
                    slots[tag] = random.choice(self.metadata.get(tag, [""]))
                
                if tag in slots: return str(slots[tag])
                elif tag in self.metadata:
                    val = self.metadata[tag]
                    return str(random.choice(val) if isinstance(val, list) else val)
                return ""
            
            prev_text = ""
            while text != prev_text and "<||" in text:
                prev_text = text
                text = re.sub(r'<\|\|(.*?)\|\|>', replacer, text)
            return text
        
        def render_all_tags(data):
            if isinstance(data, dict):
                return {k: render_all_tags(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [render_all_tags(item) for item in data]
            elif isinstance(data, str): return render_tags(data)
            return data

        output_data = block.get("output", "")
        
        raw_output = random.choice(output_data) if isinstance(
            output_data, list
        ) else output_data

        if related and status == "rejected": 
            raw_output = "<||related||>"
        
        final_output = render_tags(raw_output)
        thinking_data = block.get("thinking")        
        
        thinking = random.choice(thinking_data) if isinstance(
            thinking_data, list
        ) else thinking_data
        
        if thinking: thinking = render_tags(thinking)
        
        payload = {
            "npc": self.config.get("name", "NPC"),
            "confidence": confidence, 
            "response": final_output,
            "related": related,
            "permission": block.get("permission", "ask"), 
            "sentiment": self.sentiment,
            "emoji": self.nlp.sentiment_emoji(self.sentiment),
            "slots": slots, 
            "status": status, 
            "thinking": thinking
        }        
        
        if "description" in block:
            payload["description"] = render_tags(block["description"])

        if "tools" in block and isinstance(block["tools"], list):
            payload["tools"] = render_all_tags(copy.deepcopy(block["tools"]))
            
        logger.info(f"[FlintNPC.py][{self.name}][generate_response] Payload: {payload}")
        return payload