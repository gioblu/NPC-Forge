/**
 * FlintParser - Natural Language Understanding Engine
 * Giovanni Blu Mitolo 2026
 * Optimized for high-performance browser execution
 * Aligned 1:1 with Python FlintParser.py behavior
 */
class FlintParser {
    constructor(name, vocabulary, templates, templates_vocabulary, variable_types, log_level = "INFO", intents = null) {
        this.log_level = log_level;
        
        // FIX: Provide sensible defaults for variable types. 
        // If bundleData.types is omitted, this ensures template matching still works.
        this.variable_types = {
            "<||string||>": ".*",
            "<||number||>": "[0-9]+",
            ...(variable_types || {})
        };
        
        this.vocabulary = vocabulary;
        this.templates = templates;
        this.templates_vocabulary = templates_vocabulary || {};
        this.log_info = `[${name}][nlp.js]`;
        
        this._tokenize_cache = new Map();
        this._regex_cache = new Map();
        
        console.log(`[FlintParser] Initializing with ${intents ? intents.length : 0} intent blocks.`);
        this.weights = this.calculate_auto_weights(intents || []);
        this._compiled_paths = this._compile_templates(templates);
        
        this._synonym_map = new Map();
        if (this.templates_vocabulary) {
            for (const [tag, synonyms] of Object.entries(this.templates_vocabulary)) {
                const normalized_tag = String(tag).toLowerCase().trim();
                this._synonym_map.set(normalized_tag, normalized_tag);
                for (const syn of synonyms) {
                    this._synonym_map.set(String(syn).toLowerCase().trim(), normalized_tag);
                }
            }
        }
    }

    _tokenize(text) {
        if (typeof text !== 'string') text = String(text ?? "");
        if (this._tokenize_cache.has(text)) return this._tokenize_cache.get(text);
        const tokens = text.toLowerCase().trim().split(/\s+/).filter(Boolean);
        if (this._tokenize_cache.size > 10000) this._tokenize_cache.clear();
        this._tokenize_cache.set(text, tokens);
        return tokens;
    }

    _get_word_pattern(words_list) {
        const key = words_list.join('|');
        if (this._regex_cache.has(key)) return this._regex_cache.get(key);
        
        const escapedWords = words_list.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
        const pattern = new RegExp(`\\s*\\b(?:${escapedWords})\\b\\s*`, 'gi');
        
        if (this._regex_cache.size > 1000) this._regex_cache.clear();
        this._regex_cache.set(key, pattern);
        return pattern;
    }

    _compile_templates(templates) {
        const compiled = [];
        if (!templates) return compiled;
        for (const b of templates) {
            if (!b || !b.structure) continue;
            for (const path of b.structure) {
                const required_count = path.reduce((count, node) => count + (node.required !== false ? 1 : 0), 0);
                compiled.push({ template: b, path, required_count, total_length: path.length });
            }
        }
        compiled.sort((a, b) => b.total_length !== a.total_length ? b.total_length - a.total_length : b.required_count - a.required_count);
        return compiled;
    }

    tag_matches(value, tag) {
        if (Array.isArray(tag)) return tag.includes(value);
        return value === tag;
    }

    calculate_auto_weights(intents) {
        const totalIntents = intents.length;
        if (!totalIntents) {
            console.warn(`[FlintParser] WARNING: Received 0 valid intents.`);
            return {};
        }

        const wordIntentCounts = {};
        for (const entry of intents) {
            const uniqueWordsInIntent = new Set();
            const inputs = entry.input || entry.prompt || entry.query || [];
            const inputArray = Array.isArray(inputs) ? inputs : [inputs];
            
            for (const sentence of inputArray) {
                if (typeof sentence !== 'string') continue;
                const words = this._tokenize(sentence);
                for (const word of words) uniqueWordsInIntent.add(word);
            }
            for (const word of uniqueWordsInIntent) {
                wordIntentCounts[word] = (wordIntentCounts[word] || 0) + 1;
            }
        }

        const counts = Object.values(wordIntentCounts);
        let maxCount = 1;
        if (counts.length > 0) {
            maxCount = counts.reduce((max, current) => (current > max ? current : max), 1);
        }

        const weights = {};
        for (const [word, count] of Object.entries(wordIntentCounts)) {
            weights[word] = Math.max(0.05, 1.0 - (count / maxCount));
        }
        
        return weights;
    }

    get_rarest_word(prompt) {
        if (!prompt || !this.weights || Object.keys(this.weights).length === 0) return null;
        
        const tokens = this._tokenize(prompt);
        if (!tokens.length) return null;

        let rarest = tokens[0];
        let maxWeight = this.weights[rarest] !== undefined ? this.weights[rarest] : 0.0;

        for (let i = 1; i < tokens.length; i++) {
            const token = tokens[i];
            const weight = this.weights[token] !== undefined ? this.weights[token] : 0.0;
            if (weight > maxWeight) {
                maxWeight = weight;
                rarest = token;
            }
        }
        
        return maxWeight > 0.0 ? rarest : null;
    }

    strip_and_count(text, words_list) {
        if (!words_list || words_list.length === 0) return [String(text).trim(), 0];
        const tokens = String(text).split(/(<\|\|.*?\|\|>|".*?"|'.*?')/g);
        const anywherePattern = this._get_word_pattern(words_list);
        let totalRemoved = 0;

        for (let idx = 0; idx < tokens.length; idx++) {
            let t = tokens[idx];
            if (!t) { tokens[idx] = ""; continue; }
            if ((t.startsWith("<||") && t.endsWith("||>")) || (t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) continue;
            
            const matches = t.match(anywherePattern);
            if (matches) totalRemoved += matches.length;
            tokens[idx] = t.replace(anywherePattern, " ");
        }
        return [tokens.join("").trim().replace(/\s+/g, ' '), totalRemoved];
    }

    strip_and_sentiment(user_prompt, sentiment_json, current_sentiment, target_categories = null) {
        const category_mapping = { "expletives": "expletives", "interjections": "interjection", "thanking_words": "thanking_words", "encouraging_words": "encouraging_words", "discouraging_words": "discouraging_words" };
        if (target_categories === null) target_categories = Object.keys(category_mapping);
        let current_prompt = user_prompt;

        for (const [key, json_key] of Object.entries(category_mapping)) {
            if (target_categories.includes(key)) {
                const word_list = sentiment_json[json_key] || [];
                const [cleaned, count] = this.strip_and_count(current_prompt, word_list);
                current_prompt = cleaned;
                current_sentiment[key] = count;
            }
        }
        const punctuationPattern = /^[!"#$%&'()*+,\-./:;<=>?@[\]^_`{|}~]/;
        while (current_prompt && punctuationPattern.test(current_prompt)) current_prompt = current_prompt.substring(1);
        return [current_prompt.replace(/\s+([,.!?;])/g, '$1'), current_sentiment];
    }

    sentiment_emoji(sentiment) {
        if (!sentiment || typeof sentiment !== 'object') return "😑";
        const enc = sentiment.encouraging_words || 0, thx = sentiment.thanking_words || 0, dis = sentiment.discouraging_words || 0, exp = sentiment.expletives || 0, inj = sentiment.interjections || 0, total_pos = enc + thx;
        if (!dis && !thx) { if (exp === 1) return "😒"; if (exp === 2) return "😔"; if (exp === 3) return "😞"; if (exp === 4) return "😨"; if (exp >= 5) return "😱"; }
        if (!thx) { if (dis === 1) return "😠"; if (dis === 2) return "😤"; if (dis === 3) return "😪"; if (dis === 4) return "😭"; if (dis >= 5) return "😵"; }
        if (exp > 0 && dis > 0) return "😡"; if (exp > 0 && total_pos > 0) return "🤨";
        if (thx === 1 || enc === 1) return "😁"; if (thx === 2 || enc === 2) return "😃"; if (thx === 3 || enc === 3) return "😆"; if (thx === 4 || enc === 4) return "😜"; if (thx >= 5 || enc >= 5) return "😘";
        if (inj === 1) return "😏"; if (inj === 2) return "😒"; if (inj === 3) return "🧐"; if (inj === 4) return "😲"; if (inj >= 5) return "😵";
        return "😑";
    }

    levenshtein_similarity(s1, s2, threshold = 0.0) {
        const len1 = s1.length;
        const len2 = s2.length;
        const max_len = len1 > len2 ? len1 : len2;
        if (max_len === 0) return 1.0;
        
        const diff = len1 > len2 ? len1 - len2 : len2 - len1;
        if (1.0 - (diff / max_len) < threshold) return 0.0;

        let str1 = s1, str2 = s2;
        let l1 = len1, l2 = len2;
        if (l1 < l2) { str1 = s2; str2 = s1; l1 = len2; l2 = len1; }

        const current_row = new Array(l2 + 1);
        for (let k = 0; k <= l2; k++) current_row[k] = k;
        const max_dist = Math.floor((1.0 - threshold) * l1);

        for (let i = 1; i <= l1; i++) {
            let prev_cell = i;
            const c1 = str1.charCodeAt(i - 1);
            let min_row_dist = i; 
            
            for (let j = 1; j <= l2; j++) {
                const cost = c1 === str2.charCodeAt(j - 1) ? 0 : 1;
                let current_value = current_row[j - 1] + cost;
                
                const del = prev_cell + 1;
                if (del < current_value) current_value = del;
                
                const ins = current_row[j] + 1;
                if (ins < current_value) current_value = ins;

                current_row[j - 1] = prev_cell;
                prev_cell = current_value;
                if (current_value < min_row_dist) min_row_dist = current_value;
            }
            current_row[l2] = prev_cell;
            if (min_row_dist > max_dist) return 0.0;
        }
        return 1.0 - (current_row[l2] / l1);
    }

    precompute_intent_signature(target_input, block, synonym_weight = 0.0) {
        const tokens = this._tokenize(target_input);
        const anchor_info = [], token_set = new Set(tokens), tag_set = new Set(), weights_list = [];
        let max_score = 0.0;
        for (const t of tokens) {
            const weight = this.weights[t] !== undefined ? this.weights[t] : 1.0;
            anchor_info.push([t, weight, t.length]); max_score += weight; weights_list.push(weight);
            const tag = this._synonym_map.get(t); if (tag) tag_set.add(tag);
        }
        weights_list.sort((a, b) => b - a);
        const max_weight_sums = []; let current_sum = 0.0;
        for (const w of weights_list) { current_sum += w; max_weight_sums.push(current_sum); }
        return { block, token_set, tag_set, anchor_info, max_score, synonym_weight, token_count: tokens.length, max_weight_sums };
    }

    fast_score_calculation(query_tokens, data, threshold) {
        let total_score = 0.0;
        const matched_indices = new Array(query_tokens.length).fill(false);
        let effective_max_score = data.max_score;
        
        const synonym_weight = (
            data.synonym_weight !== undefined && data.synonym_weight > 0
        ) ? data.synonym_weight : 1.0;
        
        for (const [t_anchor, anchor_weight, t_anchor_len] of data.anchor_info) {
            let best_word_sim = 0.0;
            let best_match_idx = -1;
            const max_diff = Math.floor(Math.max(t_anchor_len, 10) * (1.0 - threshold)) + 2;
            
            for (let idx = 0; idx < query_tokens.length; idx++) {
                if (matched_indices[idx]) continue;
                const t_query = query_tokens[idx];
                const t_query_len = t_query.length;

                if (t_anchor === t_query) { 
                    best_word_sim = 1.0; 
                    best_match_idx = idx; 
                    break; 
                }

                const anchor_tag = this._synonym_map.get(t_anchor);
                const query_tag = this._synonym_map.get(t_query);
                
                if (anchor_tag && query_tag && anchor_tag === query_tag) { 
                    best_word_sim = synonym_weight; 
                    best_match_idx = idx; 
                    break; 
                }

                if (Math.abs(t_anchor_len - t_query_len) > max_diff) continue;

                if (t_anchor_len > 3 && t_query_len > 3) {
                    let hasOverlap = false;
                    for (let i = 0; i < t_anchor_len; i++) {
                        if (t_query.indexOf(t_anchor[i]) !== -1) { hasOverlap = true; break; }
                    }
                    if (!hasOverlap) continue;
                }

                const sim = this.levenshtein_similarity(t_anchor, t_query, threshold);
                if (sim > best_word_sim) { 
                    best_word_sim = sim; 
                    best_match_idx = idx; 
                }
            }

            if (best_word_sim >= threshold) {
                total_score += best_word_sim * anchor_weight;
                if (best_match_idx !== -1) matched_indices[best_match_idx] = true;
            }
        }

        for (let idx = 0; idx < query_tokens.length; idx++) {
            const t_query = query_tokens[idx];
            if (!matched_indices[idx] && t_query.length >= 3 && !(t_query in this.weights) && !this._synonym_map.has(t_query)) {
                effective_max_score += 0.5;
            }
        }

        return effective_max_score ? total_score / effective_max_score : 0.0;
    }

    find_candidates(structure, candidates) {
        const clean_user = structure.filter(tag => typeof tag === 'string' && tag.startsWith("<||"));
        const u_len = clean_user.length;
        
        for (const template of this.templates) {
            if (!template || !template.structure) continue;
            for (const path of template.structure) {
                let p_idx = 0;
                let u_idx = 0;

                while (p_idx < path.length && u_idx < u_len) {
                    if (this.tag_matches(clean_user[u_idx], path[p_idx].tag)) {
                        u_idx += 1;
                        p_idx += 1;
                    } else if (path[p_idx].required !== false) {
                        break;
                    } else {
                        p_idx += 1;
                    }
                }
                
                if (u_idx === u_len) {
                    if (p_idx < path.length) {
                        const target_node = path[p_idx];
                        const type = target_node.type !== undefined ? target_node.type : target_node["type"];
                        const normalized_tag = Array.isArray(target_node.tag) ? target_node.tag : target_node.tag;
                        
                        if (!candidates.some(([cType, cTag]) => cType === type && JSON.stringify(cTag) === JSON.stringify(normalized_tag))) {
                            candidates.push([type, normalized_tag]);
                        }
                        
                        if (target_node.required === false && (p_idx + 1) < path.length) {
                            const next_node = path[p_idx + 1];
                            const next_type = next_node.type !== undefined ? next_node.type : next_node["type"];
                            const next_normalized_tag = Array.isArray(next_node.tag) ? next_node.tag : next_node.tag;
                            
                            if (!candidates.some(([cType, cTag]) => cType === next_type && JSON.stringify(cTag) === JSON.stringify(next_normalized_tag))) {
                                candidates.push([next_type, next_normalized_tag]);
                            }
                        }
                    }
                }
            }
        }
    }

    find_template(token, threshold) {
        if (!this.templates_vocabulary) return null;
        let match = null, similarity = 0.0;
        for (const [tag, synonyms] of Object.entries(this.templates_vocabulary)) {
            for (const synonym of synonyms) {
                if (token === synonym) { match = tag; similarity = 1.0; break; }
                if (token.length > 4 && synonym.length >= 4) {
                    const sim = this.levenshtein_similarity(token, synonym);
                    if (sim >= threshold && sim > similarity) { similarity = sim; match = tag; }
                }
            }
            if (similarity === 1.0) break;
        }
        return match;
    }
    
    parse_structure(sub_prompt, threshold) {
        const token_pattern = /"[^"]*(?:.[^"]*)*"|\S+/g;
        const raw_words = (String(sub_prompt).match(token_pattern) || []).map(w => w.trim()).filter(Boolean);
        const stop_words = this.vocabulary?.stop_words || [];
        const expletives = this.vocabulary?.expletives || [];
        const interjections = this.vocabulary?.interjections || [];
        
        const working_tokens = [];
        for (let i = 0; i < raw_words.length; i++) {
            const w = raw_words[i];
            if (!stop_words.includes(w) && !expletives.includes(w) && !interjections.includes(w)) {
                working_tokens.push(w);
            }
        }
        
        const structure = [], slots = {};
        let i = 0;
        while (i < working_tokens.length) {
            let token = working_tokens[i].trim();
            const candidates = [];
            this.find_candidates(structure, candidates);
            
            const expects_variable = candidates.some(([type, tag]) => typeof tag === 'string' && tag in this.variable_types);
            let match = null;
            
            if (!token.includes(" ")) {
                const hasVocab = candidates.some(([type, _]) => type === "vocab");
                if (hasVocab) {
                    const possible_match = this.find_template(token, threshold);
                    if (possible_match) {
                        const expects_this_vocab = candidates.some(
                            ([type, tag]) => type === "vocab" && this.tag_matches(possible_match, tag)
                        );
                        
                        if (structure.length > 0 && expects_variable && !expects_this_vocab) {
                            match = null;
                        } else {
                            match = possible_match;
                        }
                    }
                }
            }
            
            if (match) { 
                structure.push(match); 
                i++; 
                continue; 
            }
            
            let matched_variable = false;
            for (const [type, tag] of candidates) {
                if (type === "vocab") continue;
                
                const rgxp = `<||${type}||>`;
                if (rgxp in this.variable_types) {
                    const regex_pattern = new RegExp(this.variable_types[rgxp], 'i');
                    const slot_name = String(tag).replace(/<\|\||\|\|>/g, "");
                    
                    if (type === "string" && !token.startsWith('"')) {
                        const remainder = working_tokens.slice(i).join(" ");
                        if (regex_pattern.test(remainder)) {
                            structure.push(tag);
                            slots[slot_name] = remainder.replace(/'/g, "'''");
                            i = working_tokens.length;
                            matched_variable = true;
                            break;
                        }
                    }
                    if (regex_pattern.test(token)) {
                        structure.push(tag);
                        slots[slot_name] = token.replace(/^"+|"+$/g, '').replace(/'/g, "'''");
                        i++;
                        matched_variable = true;
                        break;
                    }
                }
            }
            if (i >= working_tokens.length) break;
            if (matched_variable) continue;
            
            // If no match and no variable matched, ignore the unknown token (1:1 Python alignment)
            i++;
        }
        if (this.log_level === "INFO") console.log(`${this.log_info}[abstract_input] Slots: ${JSON.stringify(slots)}.`);
        return [structure, slots];
    }

    match_structure(templates, structure) {
        const struct_len = structure.length;
        const compiledPaths = (templates === this.templates && this._compiled_paths) ? this._compiled_paths : this._compile_templates(templates);
        for (const item of compiledPaths) {
            if (item.required_count > struct_len) continue;
            let prompt_i = 0, template_i = 0, template_match = true;
            while (template_i < item.path.length) {
                const node = item.path[template_i];
                const is_required = node.required !== false;
                if (prompt_i < struct_len && this.tag_matches(structure[prompt_i], node.tag)) { prompt_i += 1; template_i += 1; continue; }
                if (!is_required) { template_i += 1; } else { template_match = false; break; }
            }
            if (template_match && prompt_i === struct_len) return item.template;
        }
        return null;
    }
}