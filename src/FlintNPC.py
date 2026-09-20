import glob
import json
import os
import re
import random
import socket
import copy  

from logger import logger
from FlintParser import FlintParser

def load_json(path, name):
    try:
        with open(os.path.join(path, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON file load error. Path: {os.path.join(path, name)} Error: {e}")
        return None

def load_json_recursive(path, name):
    templates = []
    for f in glob.glob(os.path.join(path, "**", name), recursive=True):
        data = load_json(os.path.dirname(f), os.path.basename(f))
        if isinstance(data, list): templates.extend(data)
        elif isinstance(data, dict): templates.append(data)
    return templates

class FlintNPC:
    def __init__(self, npc_name, log_level="INFO"):
        logger.setLevel(log_level)
        self.name = npc_name
        
        npc_dir = f"npcs/{npc_name}"
        dataset_dir = f"{npc_dir}/dataset"
        vocab_dir = os.path.join(dataset_dir, "vocabulary")
        
        self.config = load_json(npc_dir, "config.json") or {}
        self.variable_types = load_json(dataset_dir, "types.json") or {}
        self.templates_vocabulary = load_json(vocab_dir, "templates.json") or {}
        self.vocabulary = load_json(vocab_dir, "vocabulary.json") or {}
        
        self.dataset, self.personality, self.templates = [], [], []
        self.exact_match_map, self.metadata = {}, {}
        self.active_context_map = {}
        
        self.sentiment = {
            k: 0 for k in [
                "expletives", 
                "interjections", 
                "thanking_words", 
                "encouraging_words", 
                "discouraging_words"
            ]
        }
        
        self.rejection = {"message": ["<||unknown||>"], "permission": "yolo"}
        self.sentence_threshold = float(self.config.get("sentence_threshold", 0.75))
        self.word_threshold = float(self.config.get("word_threshold", 0.75))
        
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
        self.personality = load_json(dataset_dir, "personality.json") or []
        self.dataset = load_json_recursive(dataset_dir, "dataset_*.json")
        self.templates = load_json_recursive(dataset_dir, "templates_*.json")
    
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
                    if k not in ["input", "message"]: 
                        self.metadata[k] = v

        self.metadata.update({
            "username": str(os.environ.get("USER", "user")),
            "npc_name": str(self.config.get("npc_name", "NPC")),
            "response_classes": str(len(self.dataset + self.personality + self.templates)),
            "computer_name": str(socket.gethostname()),
            "creation_date": str(self.config.get("creation_date", "2026-07-12")),
            "creator": str(self.config.get("creator", "Unknown")),
        })

        for block in self.dataset + self.personality + self.templates:
            if isinstance(block, dict) and "input" in block:
                for inp in block["input"]:
                    self.exact_match_map[str(inp).lower().strip()] = block
        
        logger.info(f"[chatbot.py][{self.name}][load_data] Engine initialized.")

    def _fast_score_calculation(self, query, data, threshold):
        total_score = 0.0
        matched_indices = [False] * len(query)

        for t_anchor, anchor_weight, t_anchor_len in data["anchor_info"]:
            best_word_sim = 0.0
            best_match_idx = -1
            max_diff = int(max(t_anchor_len, 10) * (1.0 - threshold)) + 2

            for idx, t_query in enumerate(query):
                if matched_indices[idx]: continue

                if t_anchor == t_query:
                    best_word_sim = 1.0
                    best_match_idx = idx
                    break

                if abs(t_anchor_len - len(t_query)) > max_diff: continue

                sim = self.nlp.levenshtein_similarity(
                    t_anchor, t_query, threshold
                )
                
                if sim > best_word_sim:
                    best_word_sim = sim
                    best_match_idx = idx

            if best_word_sim >= threshold:
                total_score += best_word_sim * anchor_weight
                if best_match_idx != -1:
                    matched_indices[best_match_idx] = True

        return total_score / data["max_score"] if data["max_score"] else 0.0

    def _build_intent_signatures(self):
        self._precomputed_intents = {}
        merged_map = self._get_merged_match_map()

        for target_input, block in merged_map.items():
            tokens = target_input.lower().split()
            anchor_info = []
            max_score = 0.0

            for t in tokens:
                t_len = len(t)
                
                weight = self.nlp.weights.get(t, 0.05) if (
                    t_len < 3
                ) else self.nlp.weights.get(t, 1.0)
                
                if t_len == 3: weight *= 1.5
                anchor_info.append((t, weight, t_len))
                max_score += weight

            self._precomputed_intents[target_input] = {
                "block": block,
                "token_set": set(tokens),
                "anchor_info": anchor_info,
                "max_score": max_score
            }

    def update_context(self, block):
        if "context" in block:
            if isinstance(block["context"], list) and len(block["context"]) > 0:
                self.active_context_map = {}
                for ctx_block in block["context"]:
                    if isinstance(ctx_block, dict) and "input" in ctx_block:
                        for inp in ctx_block["input"]:
                            self.active_context_map[str(inp).lower().strip()] = ctx_block
            else:
                self.active_context_map = {}

    def _get_merged_match_map(self):
        return {**self.exact_match_map, **self.active_context_map}

    def process_message(self, user_prompt: str):
        logger.info(f"[chatbot.py][{self.name}][process_message] Prompt: {user_prompt}")                    
        rarest_word = self.nlp.get_rarest_word(user_prompt)
        
        if not user_prompt:
            return self.generate_response(self.rejection, {}, 0.0, "rejected")
        
        stripped, _ = self.nlp.strip_and_sentiment(
            user_prompt, 
            self.vocabulary, 
            self.sentiment, 
            ["expletives", "interjections"]
        )

        merged_map = self._get_merged_match_map()
        if stripped in merged_map:
            matched_block = merged_map[stripped]
            
            match_status = "context match" if (
                stripped in self.active_context_map
            ) else "exact match"
            
            self.update_context(matched_block)
            self.nlp.strip_and_sentiment(
                stripped, 
                self.vocabulary, 
                self.sentiment, 
                ["encouraging_words", "discouraging_words", "thanking_words"]
            )
            return self.generate_response(matched_block, {}, 1.0, match_status)

        structure, slots = self.nlp.parse_structure(
            user_prompt, self.sentence_threshold
        )
        
        matched_template = self.nlp.match_structure(self.templates, structure)

        if matched_template:
            logger.info(f"[Template Match] {matched_template.get('intent')}")
            self.update_context(matched_template)
            cumulative_slots = dict(slots)
            if "content" not in cumulative_slots and "string" in cumulative_slots:
                cumulative_slots["content"] = cumulative_slots["string"]
            self.nlp.strip_and_sentiment(user_prompt, self.vocabulary, self.sentiment)
            
            return self.generate_response(
                matched_template, cumulative_slots, 1.0, "template match"
            )

        user_prompt_clean, _ = self.nlp.strip_and_sentiment(
            stripped, 
            self.vocabulary, 
            self.sentiment, 
            ["encouraging_words", "discouraging_words", "thanking_words"]
        )
        
        query_tokens = user_prompt_clean.lower().split()

        threshold = self.word_threshold if len(query_tokens) <= 3 else self.sentence_threshold
        
        # First: try fuzzy match against ACTIVE CONTEXT
        best_context_block, best_context_score = None, -1.0
        for inp, block in self.active_context_map.items():
            score = self.nlp.sentence_similarity(user_prompt_clean, inp, threshold)
            if score > best_context_score:
                best_context_score = score
                best_context_block = block

        if best_context_score >= self.sentence_threshold:
            self.update_context(best_context_block)
            return self.generate_response(
                best_context_block, 
                {}, 
                best_context_score, 
                "probabilistic match"
            )

        best_block, best_score = None, -1.0
        related_intents = []
        seen_categories = set()
        max_suggestions = int(self.config.get("suggestions", 5))

        for target_input, precomputed in self._precomputed_intents.items():
            # PERF: O(1) set lookup instead of O(N) list search
            if rarest_word and rarest_word not in precomputed["token_set"]: 
                continue

            score = self._fast_score_calculation(
                query_tokens, precomputed, max(threshold, best_score)
            )

            if score > best_score:
                best_score = score
                best_block = precomputed["block"]

            if len(related_intents) < max_suggestions and rarest_word and isinstance(
                precomputed["block"], dict
            ):
                category = precomputed["block"].get("category", "")
                found_match = False
                if rarest_word in category.split("_"): found_match = True
                else:
                    inputs = precomputed["block"].get("input", [])
                    if inputs and isinstance(inputs, list) and inputs[0]:
                        if rarest_word in str(inputs[0]).lower():
                            found_match = True

                if found_match and category not in seen_categories:
                    related_intents.append(precomputed["block"])
                    seen_categories.add(category)
            
        if best_score >= self.sentence_threshold and best_block:
            self.update_context(best_block)
            return self.generate_response(best_block, {}, best_score, "probabilistic match")

        return self.generate_response(self.rejection, {}, 0.0, "rejected", related_intents)
    
    def process_messages(self, user_prompt: str):
        separator_pattern = r"\n+|\d+\)|[;!?]"
        raw_segments = re.split(separator_pattern, user_prompt)
        sub_prompts = [seg.strip() for seg in raw_segments if seg.strip()]
        
        if not sub_prompts:
            return self.generate_response(self.rejection, {}, 0.0, "rejected")

        responses_list, tools_list, desc_list, status_list = [], [], [], []
        lowest_confidence = 1.0
        aggregated_sentiment = {k: 0 for k in self.sentiment}

        for sub_prompt in sub_prompts:
            res = self.process_message(sub_prompt)
            current_conf = res.get("confidence", 0.0)
            
            if current_conf < self.sentence_threshold or res.get("status") == "rejected":
                logger.warning(f"[chatbot.py][{self.name}][process_messages] Rejected '{sub_prompt}', confidence {current_conf:.4f}")
                return self.generate_response(
                    self.rejection, 
                    {}, 
                    0, 
                    "rejected", 
                    res.get("related", [])
                )

            if current_conf < lowest_confidence: lowest_confidence = current_conf

            if "response" in res: responses_list.append(res["response"])
            if "tools" in res: tools_list.append(res["tools"])
            if "description" in res: desc_list.append(res["description"])
            if "status" in res: status_list.append(res["status"])
            
            for key in aggregated_sentiment:
                aggregated_sentiment[key] += self.sentiment.get(key, 0)

        concatenated_response = " ".join(responses_list)
        concatenated_description = " ".join(desc_list) 
        
        concatenated_status = status_list[0] if status_list and all(
            s == status_list[0] for s in status_list
        ) else ", ".join(status_list)

        final_output = dict(res)
        final_output.update({
            "description": concatenated_description,
            "tools": tools_list,
            "response": concatenated_response,
            "confidence": lowest_confidence,
            "status": concatenated_status,
            "sentiment": aggregated_sentiment
        })
        
        logger.info(f"[chatbot.py][{self.name}][process_messages] Output: '{concatenated_response}'")
        return final_output

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

        output_data = block.get("message", block.get("output", ""))
        
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

        logger.info(f"[chatbot.py][{self.name}][generate_response] Payload: {payload}")
        return payload