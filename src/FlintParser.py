from array import array
import re
import string
from functools import lru_cache
import sys
from logger import logger

class FlintParser:
    """
        FlintParser - Giovanni Blu Mitolo 2026 
        (see LICENSE for licensing details)
        
        This is a very compact semantic parser designed for 
        lightweight NLU (Naturual Language Understanding) agents. 
        
        It implements the minimum features required for a working 
        conversational agent. It supports both static and template
        questions specified by the NDF 0.0 (NPC-Forge Dataset Format) 
        and operates with a white-space tokenizer.
        
        Features:
        - Text sanitization (strips insults, emojis, interjections)
        - Template semantic parsing
        - Sentence similarity (BOW IDF + Levenshtein)
        - Subject identification via IDF
        - Sentiment analysis
        - Emojii generation according to sentiment
    """
    def __init__(
        self, 
        name, 
        vocabulary,
        templates,
        templates_vocabulary,
        variable_types,
        log_level="INFO",
        intents=None
    ):
        self.log_level = log_level
        self.variable_types = variable_types
        self.vocabulary = vocabulary
        self.templates = templates
        self.templates_vocabulary = templates_vocabulary or {}
        self.log_info = f"[{name}][nlp.py]"
        self.weights = self.calculate_auto_weights(intents or [])
        
        self._compiled_paths = self._compile_templates(templates)
        
        # Pre-compute O(1) normalized synonym lookup map
        self._synonym_map = {}
        if self.templates_vocabulary:
            for tag, synonyms in self.templates_vocabulary.items():
                normalized_tag = str(tag).lower().strip()
                self._synonym_map[normalized_tag] = normalized_tag
                for syn in synonyms:
                    self._synonym_map[str(syn).lower().strip()] = normalized_tag  
        
        self._strip_cache = {}
        self._cand_cache = {}
        # word-pair similarity is a pure function, we cache it
        self._word_sim = lru_cache(maxsize=100000)(self.levenshtein_similarity)                
        return

    def _compile_templates(self, templates):
        """
        Pre-compiles templates into a sorted list of paths for O(1) pruning 
        and O(N) early-exit matching.
        """
        compiled = []
        if not templates: return compiled
            
        for b in templates:
            if not b or "structure" not in b: continue
            for path in b["structure"]:
                required_count = sum(1 for node in path if node.get("required", True))
                total_length = len(path)
                compiled.append({
                    "template": b,
                    "path": path,
                    "required_count": required_count,
                    "total_length": total_length
                })
        
        # Sort by total_length descending then required_count descending.
        # This guarantees the first valid match found is the most specific 
        # path allowing for an early exit.
        
        compiled.sort(
            key=lambda x: (
                x["total_length"], 
                x["required_count"]
            ), 
            reverse=True
        )
        
        return compiled
    
    def tag_matches(self, value, tag):
        """
        Checks if a value matches a tag. Tag can be a string or list of strings.
        If tag is a list, returns True if value matches any element.
        """
        if isinstance(tag, list):
            return value in tag
        return value == tag

    def calculate_auto_weights(self, intents):
        """
        Computes Document Frequency weights for every unique word across 
        the intent dataset's "input" key. Rarest words approach 1.0, 
        most common scaffolding approaches ~0.05. Stable regardless of 
        dataset size (unlike log(N/k) which degenerates as N grows).
        """
        total_intents = len(intents)
        if not total_intents:
            return {}

        word_intent_counts = {}
        for entry in intents:
            unique_words_in_intent = set()
            for sentence in entry.get("input", []) or []:
                for word in str(sentence).lower().strip().split():
                    unique_words_in_intent.add(word)

            for word in unique_words_in_intent:
                word_intent_counts[word] = word_intent_counts.get(word, 0) + 1

        # Document Frequency: ratio of intents containing the word
        max_count = max(word_intent_counts.values()) if word_intent_counts else 1
        
        weights = {}
        for word, count in word_intent_counts.items():
            # Rarest words (count=1) -> 1.0, most common words -> ~0.05
            # Epsilon (0.05) prevents stop words from having exactly 0 weight
            weights[word] = max(0.05, 1.0 - (count / max_count))
            
        return weights
    
    def get_rarest_word(self, prompt: str) -> str | None:
        if not prompt or not self.weights:
            return None
        tokens = prompt.lower().split()
        if not tokens:
            return None
        rarest = max(tokens, key=lambda w: self.weights.get(w, 0.0))
        return rarest if self.weights.get(rarest, 0.0) > 0.0 else None
    
    def strip_and_count(self, text, words_list):
        if not words_list: return str(text).strip(), 0
        key = tuple(words_list)
        pattern = self._strip_cache.get(key)
        if pattern is None:
            parts = []
            for w in sorted(set(words_list), key=len, reverse=True):
                if not w: continue
                pre = r"\b" if (w[0].isalnum() or w[0] == "_") else ""
                post = r"\b" if (w[-1].isalnum() or w[-1] == "_") else ""
                parts.append(pre + re.escape(w) + post)
            pattern = re.compile(r"\s*(?:" + "|".join(parts) + r")\s*", re.IGNORECASE) if parts else None
            self._strip_cache[key] = pattern
        if pattern is None:
            return str(text).strip(), 0
        tokens = re.split(r"(<\|\|.*?\|\|>|\".*?\"|'.*?')", str(text))
        edges = (("<||", "||>"), ('"', '"'), ("'", "'"))
        total = 0
        for idx, t in enumerate(tokens):
            if any(t.startswith(a) and t.endswith(b) for a, b in edges):
                continue
            while True:
                cleaned, n = pattern.subn(" ", t)
                if n == 0: break
                total += n
                t = cleaned
            tokens[idx] = t
        return re.sub(r"\s+", " ", "".join(tokens).strip()), total
    
    def strip_and_sentiment(
        self,
        user_prompt, 
        sentiment_json, 
        current_sentiment, 
        target_categories=None
    ):
        """
            Processes user prompt and extracts sentiment metrics using 
            a JSON dictionary. Only modifies keys that are processed.
        """
        
        category_mapping = {
            "expletives": "expletives",
            "interjections": "interjection",
            "thanking_words": "thanking_words",
            "encouraging_words": "encouraging_words",
            "discouraging_words": "discouraging_words"
        }

        if target_categories is None:
            target_categories = list(category_mapping.keys())

        current_prompt = user_prompt

        for key, json_key in category_mapping.items():
            if key in target_categories:
                word_list = sentiment_json.get(json_key, [])
                current_prompt, count = self.strip_and_count(
                    current_prompt, word_list
                )
                current_sentiment[key] = count

        # Trimming of leading punctuation
        while current_prompt and current_prompt[0] in string.punctuation:
            current_prompt = current_prompt[1:]
            
        # Normalize whitespaces preceding punctuation
        cleaned_prompt = re.sub(r'\s+([,.!?;])', r'\1', current_prompt)

        return cleaned_prompt, current_sentiment
        
    def sentiment_emoji(self, sentiment: dict) -> str:
        """
        Generates a cynical, cold, and nerdy face emoji based on the 
        density and balance of detected user input tokens.
        """
        if not sentiment or not isinstance(sentiment, dict):
            return "😑"
        
        enc = sentiment.get("encouraging_words", 0)
        thx = sentiment.get("thanking_words", 0)
        dis = sentiment.get("discouraging_words", 0)
        exp = sentiment.get("expletives", 0)
        inj = sentiment.get("interjections", 0)
        
        total_pos = enc + thx

        if not dis and not thx:
            if exp == 1: return "😒"
            if exp == 2: return "😔"
            if exp == 3: return "😞"
            if exp == 4: return "😨"
            if exp >= 5: return "😱"
        
        if not thx:
            if dis == 1: return "😠"
            if dis == 2: return "😤"
            if dis == 3: return "😪"
            if dis == 4: return "😭"
            if dis >= 5: return "😵"
            
        if exp > 0 and dis > 0: return "😡"  
        if exp > 0 and total_pos > 0: return "🤨"  
        if thx == 1 or enc == 1: return "😁"
        if thx == 2 or enc == 2: return "😃"
        if thx == 3 or enc == 3: return "😆"
        if thx == 4 or enc == 4: return "😜"
        if thx >= 5 or enc >= 5: return "😘"
        if inj == 1: return "😏" 
        if inj == 2: return "😒" 
        if inj == 3: return "🧐" 
        if inj == 4: return "😲" 
        if inj >= 5: return "😵" 
        return "😑"

    def levenshtein_similarity(self, s1, s2, threshold=0.0):
        s1, s2 = s1.lower().strip(), s2.lower().strip()
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        len1, len2 = len(s1), len(s2)
        max_len = len1
        if max_len == 0: return 1.0
        if s1 == s2: return 1.0
        if 1.0 - (len1 - len2) / max_len < threshold: return 0.0
        max_dist = int((1.0 - threshold) * max_len + 1e-9)   # FIX #6
        p = 0
        while p < len2 and s1[p] == s2[p]: p += 1
        s1, s2 = s1[p:], s2[p:]
        q = 0
        while q < len(s2) and s1[-1 - q] == s2[-1 - q]: q += 1
        if q: s1, s2 = s1[:-q], s2[:-q]
        n1, n2 = len(s1), len(s2)
        if n2 == 0:
            return 1.0 - n1 / max_len if n1 <= max_dist else 0.0
        current_row = list(range(n2 + 1))
        for i in range(1, n1 + 1):
            prev_cell, c1, min_row_dist = i, s1[i - 1], i
            for j in range(1, n2 + 1):
                cur = min(current_row[j] + 1, prev_cell + 1,
                          current_row[j - 1] + (c1 != s2[j - 1]))
                current_row[j - 1] = prev_cell
                prev_cell = cur
                if cur < min_row_dist: min_row_dist = cur
            current_row[n2] = prev_cell
            if min_row_dist > max_dist: return 0.0
        return 1.0 - (current_row[n2] / max_len)

    def precompute_intent_signature(
        self, 
        target_input: str, 
        block: dict,
        synonym_weight: float = 0.0
    ) -> dict:
        tokens = tuple(sys.intern(t) for t in target_input.lower().split())
        weights_list = []
        max_score = 0.0
        tags = None
        for t in tokens:
            w = self.weights.get(t, 1.0)
            weights_list.append(w)
            max_score += w
            tag = self._synonym_map.get(t)
            if tag:
                if tags is None:
                    tags = set()
                tags.add(tag)

        weights_list.sort(reverse=True)
        bounds = array('d')
        s = 0.0
        for w in weights_list:
            s += w
            bounds.append(s)

        return {
            "block": block,
            "tokens": tokens,                      
            "tag_set": tuple(tags) if tags is not None else (),
            "max_score": max_score,
            "synonym_weight": synonym_weight,
            "token_count": len(tokens),
            "max_weight_sums": bounds,
        }
        
    def _score_and_matched(self, query_tokens, data, threshold):
        """Identical scoring to fast_score_calculation, plus matched-query-token count."""
        total_score = 0.0
        matched = [False] * len(query_tokens)
        eff_max = data["max_score"]
        syn_w = data.get("synonym_weight", 0.0)
        smap = self._synonym_map
        weights = self.weights
        q_info = [(t, smap.get(t), len(t)) for t in query_tokens]
        word_sim = self._word_sim

        for t_anchor in data["tokens"]:
            a_w = weights.get(t_anchor, 1.0)
            a_len = len(t_anchor)
            best_sim, best_idx = 0.0, -1
            max_diff = int(max(a_len, 10) * (1.0 - threshold)) + 2
            a_tag = smap.get(t_anchor)
            for idx, (t_q, q_tag, q_len) in enumerate(q_info):
                if matched[idx]: continue
                if t_anchor == t_q:
                    best_sim, best_idx = 1.0, idx; break
                if a_tag and q_tag and a_tag == q_tag:
                    best_sim, best_idx = syn_w, idx; break
                if abs(a_len - q_len) > max_diff: continue
                sim = word_sim(t_anchor, t_q, threshold)
                if sim > best_sim:
                    best_sim, best_idx = sim, idx
            if best_sim >= threshold:
                total_score += best_sim * a_w
                if best_idx != -1: matched[best_idx] = True

        for idx, (t_q, q_tag, _) in enumerate(q_info):
            if not matched[idx] and t_q not in weights and q_tag is None:
                eff_max += 0.5
        score = total_score / eff_max if eff_max else 0.0
        return score, sum(matched)

    def fast_score_calculation(self, query_tokens, data, threshold):
        return self._score_and_matched(query_tokens, data, threshold)[0]
    
    def find_candidates(self, structure, candidates):
        key = tuple(structure)
        cached = self._cand_cache.get(key)
        if cached is None:
            cached = []
            u_len = len(structure)
            for template in self.templates:
                if not template or "structure" not in template:
                    continue
                for path in template["structure"]:
                    p_idx = u_idx = 0
                    while p_idx < len(path) and u_idx < u_len:
                        if self.tag_matches(structure[u_idx], path[p_idx]["tag"]):
                            u_idx += 1; p_idx += 1
                        elif not path[p_idx].get("required", True):
                            p_idx += 1
                        else: break
                    if u_idx != u_len or p_idx >= len(path):
                        continue
                    node = path[p_idx]
                    nodes = [node]
                    if not node.get("required", True) and p_idx + 1 < len(path):
                        nodes.append(path[p_idx + 1])
                    for n in nodes:
                        k = (n["type"], n["tag"])
                        if k not in cached:
                            cached.append(k)
            self._cand_cache[key] = cached
        candidates.extend(cached)
            
    def find_template(self, token, threshold):
        """
            Finds token in templates_vocabulary.json 
            if the Levenshtein similarity is more than
            threshold the matched template is returned
            otherise None is retuned
        """
        low = token.lower()
        exact = self._synonym_map.get(low)
        if exact: return exact
        match, similarity = None, 0.0
        if len(low) > 4:
            for syn, tag in self._synonym_map.items():
                if len(syn) >= 4:
                    sim = self._word_sim(low, syn, threshold)
                    if sim >= threshold and sim > similarity:
                        similarity, match = sim, tag
                        if sim == 1.0: break
        if match and similarity < 1.0:
            logger.info(f"{self.log_info}[find_template] Typo: '{token}' matched to '{match}' (Confidence: {similarity:.2f})")
        return match
    
    def parse_structure(self, sub_prompt, threshold):
        """
        Converts text streams into structural tags,
        supporting overlapping paths and filtering out expletives.
        """
        log_info = f"{self.log_info}[abstract_input]"
        
        # words inside doublequotes are considered a single token
        # and the doublequotes are removed so the string tag will 
        # be captured properly

        token_pattern = r'"[^"\\]*(?:\\.[^"\\]*)*"|\S+'
        
        raw_words = [
            w.strip() for w in re.findall(
                token_pattern, sub_prompt
            ) if w.strip()
        ]

        stop_words = self.vocabulary.get("stop_words", [])
        expletives = getattr(self, "expletives_list", [])
        interjections = getattr(self, "interjection_list", [])
        
        working_tokens = [
            w for w in raw_words if (
                w not in stop_words and 
                w not in expletives and 
                w not in interjections
            )
        ]
        
        logger.info(f"{log_info} Tokens: {working_tokens}.")
        
        structure = []
        slots = {}
        i = 0
        
        while i < len(working_tokens):
            match = None
            token = working_tokens[i]
            candidates = []
            self.find_candidates(structure, candidates)
            
            expects_variable = any(
                isinstance(tag, str
            ) and tag in self.variable_types for _, tag in candidates)
            
            remainder = " ".join(working_tokens[i:])
            # if token does not contain spaces (it is not a string variable)
            if not " " in token:
                if any(type == "vocab" for type, _ in candidates):
                    possible_match = self.find_template(token, threshold)
                    if possible_match:
                        expects_this_vocab = any(
                            type == "vocab" and self.tag_matches(possible_match, tag) 
                            for type, tag in candidates
                        )
                        if (
                            len(structure) > 0 and 
                            expects_variable and 
                            not expects_this_vocab
                        ): match = None
                        else: match = possible_match
            
            if match:
                structure.append(match)
                i += 1
                continue     

            matched_variable = False
            for type, tag in candidates:
                if type == "vocab": continue
                rgxp = f"<||{type}||>"
                if rgxp in self.variable_types:
                    regex_pattern = self.variable_types[rgxp]
                    slot_name = tag.replace("<||", "").replace("||>", "")
                    
                    # Captures the following literal string if " 
                    # are present or otherwise the rest of the prompt  
                    if type == "string" and not token.startswith('"'):
                        if re.search(regex_pattern, remainder, re.IGNORECASE):
                            structure.append(tag)
                            remainder = remainder.replace("'", "'\\''")
                            slots[slot_name] = remainder
                            
                            i = len(working_tokens)
                            matched_variable = True
                            break
                        
                    # Captures atomic types 
                    if re.search(regex_pattern, token, re.IGNORECASE):
                        structure.append(tag)
                        # Rule 1 of NPC-Forge TCSS (Terminal Commands Security Standard) 
                        # Strip " then escape ' 
                        token = token.strip('"').replace("'", "'\\''")
                        slots[slot_name] = token
                        i += 1
                        matched_variable = True
                        break  # parameter extract successfully

            if matched_variable: continue
            i += 1 # ignore unkown token

        logger.info(f"{log_info} Slots: {slots}.")                    
        return structure, slots

    def match_structure(self, templates, structure):
        struct_len = len(structure)
        
        if templates is self.templates and hasattr(self, '_compiled_paths'):
            compiled_paths = self._compiled_paths
        else: compiled_paths = self._compile_templates(templates)
        
        for item in compiled_paths:
            # If the path requires more tokens than the structure has go to the next
            if item["required_count"] > struct_len: continue
                
            path = item["path"]
            prompt_i = 0
            template_i = 0
            template_match = True
            
            while template_i < len(path):
                node = path[template_i]
                tag = node["tag"]
                is_required = node.get("required", True)
                
                if prompt_i < struct_len:
                    struct_tag = structure[prompt_i]
                    # Inlined tag matching
                    if (isinstance(tag, list) and struct_tag in tag) or struct_tag == tag:
                        prompt_i += 1
                        template_i += 1
                        continue # Move to next node in both
                
                if not is_required: template_i += 1 
                else:
                    template_match = False
                    break # Required node failed, abort this path
                
            if template_match and prompt_i == struct_len:
                return item["template"]
            
        return None