import re
import string
import math
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
        self.templates_vocabulary = templates_vocabulary
        self.log_info = f"[{name}][nlp.py]"
        self.weights = self.calculate_auto_weights(intents or [])
        return

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
            Computes IDF (Inverse Document Frequency) for every 
            unique word across the intent dataset's "input" key. 
            Contribution of words that show up in many intents 
            ("is", "at", "it") is scaled down toward 0.0
            while words that are exclusive to an intent are
            scaled up toward 1.0. Runs once at initialization.
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

        weights = {
            word: math.log(total_intents / count) + 0.1
            for word, count in word_intent_counts.items()
        }

        # Normalize so that the maximum possible weight is 1.0
        max_idf = max(weights.values()) if weights else 1.0
        return {word: idf / max_idf for word, idf in weights.items()}
    
    def get_rarest_word(self, prompt: str) -> str | None:
        """Extract the word with highest IDF weight (rarest/most specific) from prompt."""
        if not prompt or not self.weights:
            return None
        tokens = prompt.lower().split()
        if not tokens:
            return None
        rarest = max(
            tokens, 
            key=lambda w: self.weights.get(w, 0.0)
        )
        weight = self.weights.get(rarest, 0.0)
        return rarest if weight > 0.0 else None
    
    def strip_and_count(self, text, words_list):
        """
        Sanitization function that strips words 
        outside strings and tags. While stripping it also
        counts the occurrences; this information is used
        later in the pipeline to compute the sentiment
        analysis.
        """
        if not words_list:
            return str(text).strip(), 0

        # avoid stripping tags or content of string literals
        protected_pattern = r"(<\|\|.*?\|\|>|\".*?\"|'.*?')"
        tokens = re.split(protected_pattern, str(text))
        
        # escape text tokens to match raw string vocabulary structures
        escaped_words = "|".join(map(re.escape, words_list))
        total_removed = 0

        # Clean occurrences anywhere handling boundaries 
        # leading and trailing spaces and punctuation
        anywhere_pattern = rf"\s*\b(?:{escaped_words})\b\s*"

        
        for idx in range(len(tokens)):
            t = tokens[idx]
            # Skip if token falls under protected formats
            if (
                t.startswith("<||") and 
                t.endswith("||>")
            ) or (
                t.startswith('"') and 
                t.endswith('"')
            ) or (t.startswith("'") and t.endswith("'")): continue
            
            # Recursive cleanup to catch sequential instances in the same token
            while True:
                cleaned, count = re.subn(
                    anywhere_pattern, " ", t, flags=re.IGNORECASE
                )
                if count == 0: break
                total_removed += count
                t = cleaned
            tokens[idx] = t

        # Final reconstruction and spacing normalization
        cleaned_text = "".join(tokens).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  
        return cleaned_text, total_removed
    
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
        if thx >= 5 or enc == 5: return "😘"
        if inj == 1: return "😏" 
        if inj == 2: return "😒" 
        if inj == 3: return "🧐" 
        if inj == 4: return "😲" 
        if inj >= 5: return "😵" 
        return "😑"

    def levenshtein_similarity(self, s1, s2, threshold=0.0):
        """
            Computes optimized Levenshtein distance with a single row vector 
            allocation and accurate early exit pruning based on the required 
            similarity cutoff score.
        """
        
        s1, s2 = s1.lower().strip(), s2.lower().strip()
        len1, len2 = len(s1), len(s2)
        max_len = max(len1, len2)
        if max_len == 0: return 1.0
        
        # Pre-calculate the maximum theoretical score possible
        max_possible_score = 1.0 - (abs(len1 - len2) / max_len)
        if max_possible_score < threshold: return 0.0

        # Ensure s1 is always the longer string
        if len1 < len2:
            s1, s2 = s2, s1
            len1, len2 = len2, len1

        current_row = list(range(len2 + 1))
        max_dist = int((1.0 - threshold) * max_len)

        for i in range(1, len1 + 1):
            prev_cell = i
            c1 = s1[i - 1]
            # Start with the vertical deletion cost
            min_row_dist = current_row[0] 
            
            for j in range(1, len2 + 1):
                substitutions = current_row[j - 1] + (c1 != s2[j - 1])
                insertions = current_row[j] + 1
                deletions = prev_cell + 1
                
                current_value = min(insertions, deletions, substitutions)
                current_row[j - 1] = prev_cell
                prev_cell = current_value
                
                if current_value < min_row_dist:
                    min_row_dist = current_value
                    
            current_row[len2] = prev_cell
            
            # The absolute minimum distance to reach the end 
            # from the current row i is: min_row_dist + (len1 - i)
            if min_row_dist > max_dist: return 0.0

        return 1.0 - (current_row[len2] / max_len)
    
    def sentence_similarity(self, 
        s1: str, 
        s2: str, 
        threshold: float = 0.0
    ) -> float:
        """
            Computes an asymmetric, order-independent sentence similarity 
            score. Tokens from s2 (the intent/reference phrase) anchor the 
            score and are weighted by their auto-computed IDF specificity, 
            so a rare word (e.g. "zombie", "syscall") that is missing from 
            s1 heavily reduces the final score, preventing very similar 
            common sentences from being confused with each other.

            Filler words (<3 chars, e.g. "is", "a") fall back to a low 
            default weight only when unseen in the intent corpus; 
            otherwise their own computed IDF weight is used, so a rare 
            short/single-letter identifier (e.g. "c", "r" as in the 
            programming languages) that only occurs in one or two intents 
            is still recognized as an important word rather than discarded. 
            3-letter words (e.g. "who", "how", "run") are additionally 
            boosted since they often carry the subject/action of the 
            phrase. A single-substitution typo on a 3-letter word scores 
            exactly 2/3 via Levenshtein, so short-word bleed (e.g. "who" 
            vs "how") is left to the caller's threshold: both shipped 
            NPCs use sentence_threshold=0.6668, just above 2/3, to reject it.
        """
        anchor_tokens = [w for w in s2.lower().strip().split() if w]
        query_tokens = [w for w in s1.lower().strip().split() if w]
        
        if not anchor_tokens or not query_tokens:
            return 1.0 if anchor_tokens == query_tokens else 0.0
            
        matched_indices = set()
        total_score = 0.0
        max_possible_score = 0.0
        
        for t_anchor in anchor_tokens:
            if len(t_anchor) < 3:
                anchor_weight = self.weights.get(t_anchor, 0.05)
            else:
                anchor_weight = self.weights.get(t_anchor, 1.0)
                if len(t_anchor) == 3:
                    anchor_weight *= 1.5

            max_possible_score += anchor_weight
            best_word_sim = 0.0
            best_match_idx = -1
            
            for idx, t_query in enumerate(query_tokens):
                if idx in matched_indices:
                    continue
                
                if t_anchor == t_query:
                    best_word_sim = 1.0
                    best_match_idx = idx
                    break
                
                sim = self.levenshtein_similarity(t_anchor, t_query, threshold)
                if sim > best_word_sim:
                    best_word_sim = sim
                    best_match_idx = idx
            
            if best_word_sim >= threshold:
                total_score += best_word_sim * anchor_weight
                if best_match_idx != -1:
                    matched_indices.add(best_match_idx)
        
        # Penalize unmatched query tokens that are entirely absent from 
        # the known vocabulary (typo/off-topic noise padding)
        for t_query in query_tokens:
            if len(t_query) >= 3 and t_query not in self.weights:
                max_possible_score += 0.5
                    
        return total_score / max_possible_score if max_possible_score else 0.0
    
    def find_candidates(self, structure, candidates):
        clean_user = [tag for tag in structure if tag.startswith("<||")]
        u_len = len(clean_user)
        
        for template in self.templates:
            if not template or "structure" not in template: continue
            for path in template["structure"]:
                p_idx = 0
                u_idx = 0

                while p_idx < len(path) and u_idx < u_len:
                    if self.tag_matches(clean_user[u_idx], path[p_idx]["tag"]):
                        u_idx += 1
                        p_idx += 1
                    elif not path[p_idx]["required"]: p_idx += 1
                    else: break
                    
                # If all nodes are processed gathers candidates 
                # compatible with the actual position
                if u_idx == u_len:
                    if p_idx < len(path):
                        target_node = path[p_idx]
                        type = target_node["type"]
                        normalized_tag = target_node["tag"] if isinstance(
                            target_node["tag"], list
                        ) else target_node["tag"]
                        
                        if (type, normalized_tag) not in candidates:
                            candidates.append((type, normalized_tag))
                        
                        # If the actual node is optional
                        # gather the next as an alternative
                        if not target_node["required"] and (p_idx + 1) < len(path):
                            next_node = path[p_idx + 1]
                            next_type = next_node["type"]
                            next_tag = next_node["tag"]
                            next_normalized_tag = next_tag if isinstance(next_tag, list) else next_tag
                            
                            if (next_type, next_normalized_tag) not in candidates:
                                candidates.append((next_type, next_normalized_tag))
            
    def find_template(self, token, threshold):
        """
            Finds token in templates_vocabulary.json 
            if the Levenshtein similarity is more than
            threshold the matched template is returned
            otherise None is retuned
        """
        if hasattr(self, 'templates_vocabulary'):
            match = None
            similarity = 0.0

            for tag, synonyms in self.templates_vocabulary.items():
                for synonym in synonyms:
                    if token == synonym:
                        match = tag
                        similarity = 1.0
                        break
                    
                    if len(token) > 4 and len(synonym) >= 4:
                        sim = self.levenshtein_similarity(token, synonym)
                        if sim >= threshold and sim > similarity:
                            similarity = sim
                            match = tag
                
                if similarity == 1.0: break

            if match:
                if similarity < 1.0:
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
            expects_variable = any(isinstance(tag, str) and tag in self.variable_types for _, tag in candidates)
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
        """
        Compares a parsed prompt structure against a list of templates.

        Args:
            templates (list[dict]): A list of templates.
            structure (list[str]): The parsed prompt structure.

        Returns:
            dict | None: The matching template emtry if a successful 
            match is found, otherwise None.
        """   
        match = None
        for b in templates:
            if not b or "structure" not in b: continue
            for path in b["structure"]:
                prompt_i = 0  # Index of prompt structure 
                template_i = 0  # Index of template structure
                template_match = True
                while template_i < len(path):
                    node = path[template_i]
                    is_required = node.get("required", True)
                    if (
                        prompt_i < len(structure) and 
                        self.tag_matches(structure[prompt_i], node["tag"])
                    ):
                        prompt_i += 1
                        template_i += 1
                    elif not is_required: template_i += 1
                    else:
                        template_match = False
                        break
                    
                if template_match and prompt_i == len(structure):
                    match = b
                    break
            
            if match: break
        return match
