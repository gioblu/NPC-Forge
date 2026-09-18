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
        logger.error(f"JSON file load error. Filename: {name} Error: {e}")
        return {}
    
def load_json_recursive(path, name):
    templates = []
    for f in glob.glob(os.path.join(path, "**", name), recursive=True):
        templates.extend(load_json(os.path.dirname(f), os.path.basename(f)))
    return templates

class FlintNPC:
    """
    FlintNPC - Giovanni Blu Mitolo 2026 (see LICENSE for licensing details) 
    
    This is a very simple class for creating ultra-lightweight NLU agents. 
    It has very low latency, minimal memory footprint and supports native 
    execution on operating systems.
    
    It adheres to NDF 0.0 (NPC-Forge Dataset Format) and supports tool 
    calls and thinking mode. 
    
    FlintNPC uses the a white-space tokenizer and implements a novel 
    deterministic approach to achieve NLU (Natural Language Understanding) 
    and intent resolution:
    
    1. Raw text sanitization (strips insults, emojis, interjections)
    2. Deterministic exact match lookup using bare string comparison
       A successful match triggers sentiment analysis and intent resolution
    3. If the exact match fails, the prompt is processesed as a 
       semantic map, extracting arguments if present.
    4. if the semantic map parsing fails, the prompt is processed as
       a BOW (Bag of Words), ignoring order and estimating similarity by 
       computing word matches and Levenshtein distance to accomodate typos
    
    Development Notes:

    While this approach is exceptionally fast and lightweight, it is highly
    sensitive to very short prompts (1-3 words) where a single typo can
    drastically alter the meaning. To prevent false positives, the default
    thresholds are set to impede typo tolerance for sentences of 3 words or 
    fewer. For longer inputs, the error tolerance grows linearly allowing 
    more typos as the sentence length increases.
    """

    def __init__(self, npc_name, log_level="INFO"):
        
        logger.setLevel(log_level)
        self.name = npc_name
        
        npc_dir = f"npcs/{npc_name}"
        dataset_dir = f"{npc_dir}/dataset"
            
        vocab_dir = os.path.join(dataset_dir, "vocabulary")
        
        self.config = load_json(npc_dir, "config.json")
        self.variable_types = load_json(dataset_dir, "types.json")
        self.templates_vocabulary = load_json(vocab_dir, "templates.json")
        self.vocabulary = load_json(vocab_dir, "vocabulary.json")
        
        # Data store properties
        self.dataset, self.personality, self.templates = [], [], []
        self.exact_match_map, self.metadata = {}, {}
        
        # Active conversational context map
        self.active_context_map = {}
        
        # Sentiment tracking counters
        self.expletives_list, self.interjection_list = [], []
        self.thanking_list, self.encouraging_list, self.discouraging_list = [], [], []
        
        self.sentiment = {
            k: 0 for k in [
                "expletives", "interjections", 
                "thanking_words", "encouraging_words", 
                "discouraging_words"
            ]
        }
        
        self.rejection = {
            "message": [ "<||unknown||>"], "permission": "yolo"
        }
        
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
                block for block in self.dataset + self.personality
                if isinstance(block, dict) and "input" in block
            ]
        )
        
        self._build_intent_signatures()

    def load_data(self, dataset_dir):
        """
            Loads configurations, vocabularies, metadata, dataset 
            intents and templates.
        """
            
        self.personality = load_json(dataset_dir, "personality.json")
        self.dataset = load_json_recursive(dataset_dir, "dataset_*.json")
        self.templates = load_json_recursive(dataset_dir, "templates_*.json")
    
        v_lists = [
            "expletives", "interjection", "thanking_words", 
            "encouraging_words", "discouraging_words", "greetings"
        ]
        
        for v_file in v_lists:
            base_name = v_file.replace("_words", "")
            data_list = self.vocabulary.get(v_file, [])
            setattr(self, f"{base_name}_list", data_list)
            if data_list:
                self.metadata[v_file] = data_list
                self.metadata[base_name] = data_list
            
        # Extract context tags from available dictionary nodes
        for block in self.dataset + self.personality + self.templates:
            if isinstance(block, dict):
                for k, v in block.items():
                    if k not in ["input", "message"]: self.metadata[k] = v

        self.metadata.update({
            "username": str(os.environ.get("USER", "user")),
            "npc_name": str(self.config.get("npc_name", "NPC")),
            "response_classes": str(
                len(self.dataset + self.personality + self.templates)
            ),
            "computer_name": str(socket.gethostname()),
            "creation_date": str(
                self.config.get("creation_date", "2026-07-12")
            ),
            "creator": str(self.config.get("creator", "Unknown")),
        })

        # Map of all prompt variants used to implement exact match later.
        for block in self.dataset + self.personality + self.templates:
            if isinstance(block, dict) and "input" in block:
                for inp in block["input"]:
                    self.exact_match_map[str(inp).lower().strip()] = block
        
        logger.info(f"[chatbot.py][{self.name}][load_data] Engine initialized.")

    def _fast_score_calculation(self, query_tokens, precomputed, threshold):
        """Fast similarity check using pre-computed intent signatures."""
        total_score = 0.0
        matched_indices = set()

        for t_anchor, anchor_weight, t_anchor_len in precomputed["anchor_info"]:
            best_word_sim = 0.0
            best_match_idx = -1

            # Fast length pruning before paying for Levenshtein
            max_diff = int(max(t_anchor_len, 10) * (1.0 - threshold)) + 2

            for idx, t_query in enumerate(query_tokens):
                if idx in matched_indices:
                    continue

                if t_anchor == t_query:
                    best_word_sim = 1.0
                    best_match_idx = idx
                    break

                t_query_len = len(t_query)
                if abs(t_anchor_len - t_query_len) > max_diff:continue

                sim = self.nlp.levenshtein_similarity(t_anchor, t_query, threshold)
                if sim > best_word_sim:
                    best_word_sim = sim
                    best_match_idx = idx

            if best_word_sim >= threshold:
                total_score += best_word_sim * anchor_weight
                if best_match_idx != -1:
                    matched_indices.add(best_match_idx)

        return total_score / precomputed["max_score"] if precomputed["max_score"] else 0.0

    def _build_intent_signatures(self):
        """Pre-calculates token weights for all intents ONCE at startup."""
        self._precomputed_intents = {}
        merged_map = self._get_merged_match_map()

        for target_input, block in merged_map.items():
            tokens = target_input.lower().split()
            anchor_info = []
            max_score = 0.0

            for t in tokens:
                t_len = len(t)
                if t_len < 3: weight = self.nlp.weights.get(t, 0.05)
                else:
                    weight = self.nlp.weights.get(t, 1.0)
                    if t_len == 3:
                        weight *= 1.5
                anchor_info.append((t, weight, t_len))
                max_score += weight

            self._precomputed_intents[target_input] = {
                "block": block,
                "tokens": tokens,
                "anchor_info": anchor_info,
                "max_score": max_score
            }

    def update_context(self, block):
        """
        Updates the active conversational context.
        
        - "context": [...]  -> overwrites active context with new entries
        - "context": []     -> explicitly clears the context
        - no "context" key  -> context persists unchanged
        
        This allows context entries to remain active after one is
        consumed, enabling flows like: "create dir" -> "move it" -> "delete it".
        """
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
        """
        Returns a unified lookup map merging active context entries with
        the global dataset. Context entries override dataset entries on
        key collision, giving them priority.
        """
        return {**self.exact_match_map, **self.active_context_map}

    def process_message(self, user_prompt: str):
        """
            Splits composite prompts, unifies their structural matrices 
            and renders the matched JSON template.
        """
        
        logger.info(f"[chatbot.py][{self.name}][process_message] Prompt: {user_prompt}")                    
        
        rarest_word = self.nlp.get_rarest_word(user_prompt)
        
        logger.info(f"[chatbot.py][{self.name}][process_message] Rarest word: '{rarest_word}'")
        
        if not user_prompt:
            return self.generate_response(self.rejection, {}, 0.0, "rejected")
        
        # Strip expletives and interjections to enhance exact match
        stripped, self.sentiment = self.nlp.strip_and_sentiment(
            user_prompt,
            self.vocabulary,
            self.sentiment,
            ["expletives", "interjections"]
        )

        # EXACT MATCH (context overrides dataset)
        merged_map = self._get_merged_match_map()
        
        if stripped in merged_map:
            matched_block = merged_map[stripped]
            is_context = stripped in self.active_context_map
            match_status = "context match" if is_context else "exact match"
            
            logger.info(f"[chatbot.py][{self.name}][process_message] {match_status}: {stripped}")
            
            self.update_context(matched_block)
            
            stripped, self.sentiment = self.nlp.strip_and_sentiment(
                stripped,
                self.vocabulary,
                self.sentiment,
                ["encouraging_words", "discouraging_words", "thanking_words"]
            )
            return self.generate_response(matched_block, {}, 1.0, match_status)

        # TEMPLATE MATCH
        structure, slots = self.nlp.parse_structure(
            user_prompt, 
            self.sentence_threshold
        )

        matched_template = self.nlp.match_structure(
            self.templates, 
            structure
        )

        if matched_template:
            logger.info(f"[Template Match] {matched_template.get('intent')}")
            self.update_context(matched_template)
            
            cumulative_slots = dict(slots)
            if "content" not in cumulative_slots and "string" in cumulative_slots:
                cumulative_slots["content"] = cumulative_slots["string"]
                
            _, self.sentiment = self.nlp.strip_and_sentiment(
                user_prompt, 
                self.vocabulary,
                self.sentiment
            )                
            
            return self.generate_response(
                matched_template, 
                cumulative_slots, 
                1.0, 
                "template match"
            )

        logger.info(f"[chatbot.py][{self.name}][process_message] NLP fallback: {user_prompt}")                    

        # PROBABILISTIC MATCH (Context + Dataset)
        best_block, best_score = None, -1.0
        related_intents = []
        seen_categories = set()

        user_prompt_clean, self.sentiment = self.nlp.strip_and_sentiment(
            stripped, self.vocabulary, self.sentiment,
            ["thanking_words", "encouraging_words", "discouraging_words"]
        )

        query_tokens = user_prompt_clean.lower().split()
        threshold = self.word_threshold if len(query_tokens) <= 3 else self.sentence_threshold

        for target_input, precomputed in self._precomputed_intents.items():
            # FAST PRE-FILTER: If the rarest word is known, and it's completely missing
            # from this intent's tokens, the IDF math guarantees it cannot beat the
            # threshold. Skip the expensive Levenshtein check entirely!
            if rarest_word and rarest_word not in precomputed["tokens"]: continue

            score = self._fast_score_calculation(
                query_tokens, precomputed, max(threshold, best_score)
            )

            if score > best_score:
                best_score = score
                best_block = precomputed["block"]

            if (
                len(related_intents) < int(self.config.get("suggestions", 5)) and
                rarest_word and isinstance(precomputed["block"], dict)
            ):
                category = precomputed["block"].get("category", "")
                found_match = False

                if rarest_word in category.split("_") or rarest_word in category.lower():
                    found_match = True

                if not found_match:
                    inputs = precomputed["block"].get("input", [])
                    if inputs and isinstance(inputs, list) and inputs[0]:
                        input_words = str(inputs[0]).lower().split()
                        if rarest_word in input_words:
                            found_match = True

                if found_match and category not in seen_categories:
                    related_intents.append(precomputed["block"])
                    seen_categories.add(category)
            
        logger.info(f"[chatbot.py][{self.name}][process_message] Best score: {best_score}")                    

        if best_score >= self.sentence_threshold and best_block:
            self.update_context(best_block)
            return self.generate_response(
                best_block, {}, best_score, "probabilistic match"
            )

        return self.generate_response(
            self.rejection, 
            {}, 
            0.0, 
            "rejected", 
            related_intents
        )
    
    def process_messages(self, user_prompt: str):
        """Splits prompts into sub-tasks and processes each."""
        separator_pattern = r"\n+|\d+\)|[;!?]"
        raw_segments = re.split(separator_pattern, user_prompt)
        
        sub_prompts = [seg.strip() for seg in raw_segments if seg.strip()]
        if not sub_prompts:
            return self.generate_response(
                self.rejection, {}, 0.0, "rejected"
            )

        responses_list = []
        tools_list = []
        desc_list = []
        status_list = []
        lowest_confidence = 1.0
        
        aggregated_sentiment = {
            "expletives": 0,
            "interjections": 0,
            "thanking_words": 0,
            "encouraging_words": 0,
            "discouraging_words": 0
        }

        res = {}
        for sub_prompt in sub_prompts:
            res = self.process_message(sub_prompt)
            current_conf = res.get("confidence", 0.0)
            
            if current_conf < self.sentence_threshold or res.get("status") == "rejected":
                logger.warning(
                    f"[chatbot.py][{self.name}][process_messages] "
                    f"Rejected '{sub_prompt}', confidence {current_conf:.4f}"
                )
                return self.generate_response(
                    self.rejection, {}, 0, "rejected", res.get("related", [])
                )

            if current_conf < lowest_confidence:
                lowest_confidence = current_conf

            if "response" in res: responses_list.append(res["response"])
            if "tools" in res: tools_list.append(res["tools"])
            if "description" in res: desc_list.append(res["description"])
            if "status" in res: status_list.append(res["status"])
                        
            if hasattr(self, 'sentiment') and isinstance(self.sentiment, dict):
                for key in aggregated_sentiment:
                    aggregated_sentiment[key] += self.sentiment.get(key, 0)

        concatenated_response = " ".join(responses_list)
        concatenated_description = " ".join(responses_list)
        concatenated_status = (
            status_list[0] if status_list and all(s == status_list[0] for s in status_list) 
            else ", ".join(status_list)
        )

        final_output = dict(res)
        final_output["description"] = concatenated_description
        final_output["tools"] = tools_list
        final_output["response"] = concatenated_response
        final_output["confidence"] = lowest_confidence
        final_output["status"] = concatenated_status
        final_output["sentiment"] = aggregated_sentiment
        
        logger.info(
            f"[chatbot.py][{self.name}][process_messages] "
            f"Output: '{concatenated_response} - {aggregated_sentiment}'"
        )
        return final_output

    def generate_response(self, block, slots, confidence, status, related=None):
        """
            Compiles output payload blocks by rendering static macro 
            keys against operational values.
        """
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
            current_tags = re.findall(r'<\|\|(.*?)\|\|>', text)
            if not current_tags: return text
            previous_text = text
            
            for tag in current_tags:
                for type in ["completion", "unknown", "related"]:    
                    if tag == type and type not in slots:
                        slots[type] = random.choice(self.metadata[type])

                if tag in slots: 
                    text = text.replace(f"<||{tag}||>", str(slots[tag]))
                elif tag in self.metadata:
                    val = self.metadata[tag]
                    text = text.replace(
                        f"<||{tag}||>", 
                        str(random.choice(val) if isinstance(val, list) else val)
                    )
                else: 
                    text = text.replace(f"<||{tag}||>", "")
            
            if text == previous_text: return text
            if re.findall(r'<\|\|(.*?)\|\|>', text): return render_tags(text)
            return text
        
        def render_all_tags(data):
            if isinstance(data, dict):
                return {k: render_all_tags(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [render_all_tags(item) for item in data]
            elif isinstance(data, str):
                return render_tags(data)
            return data

        output_data = block.get("message", block.get("output", ""))
        raw_output = random.choice(output_data) if isinstance(output_data, list) else output_data

        if related and status == "rejected": 
            raw_output = "<||related||>"
        
        final_output = render_tags(raw_output)

        thinking_data = block.get("thinking")        
        thinking = random.choice(thinking_data) if isinstance(thinking_data, list) else thinking_data
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
            tools_copy = copy.deepcopy(block["tools"])
            payload["tools"] = render_all_tags(tools_copy)

        logger.info(f"[chatbot.py][{self.name}][generate_response] Payload: {payload}")
        return payload