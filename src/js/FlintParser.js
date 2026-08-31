/**
 * FlintParser - Natural Language Understanding Engine
 * Giovanni Blu Mitolo 2026
 *
 * Ports the deterministic behavior, token filtering, 
 * similarity metrics, and slot extraction of the Python implementation.
 */
class FlintParser {
    /**
     * Initializes FlintParser with vocabulary, templates, and intents.
     *
     * @param {string} name - Identifier used for logging
     * @param {Object} vocabulary - Vocabulary containing stop_words and sentiment indicators
     * @param {Array} templates - Structural definitions of templates
     * @param {Object} templates_vocabulary - Synonym mapping for template tokens
     * @param {Object} variable_types - Regex patterns for parameter extraction (<||type||>)
     * @param {string} [log_level='INFO'] - Logging level threshold
     * @param {Array} [intents=null] - Intent dataset used for computing auto IDF weights
     */
    constructor(
        name, vocabulary, templates, templates_vocabulary,
        variable_types, log_level = "INFO", intents = null
    ) {
        this.log_level = log_level;
        this.variable_types = variable_types;
        this.vocabulary = vocabulary;
        this.templates = templates;
        this.templates_vocabulary = templates_vocabulary;
        this.log_info = `[${name}][nlp.js]`;
        this.weights = this.calculate_auto_weights(intents || []);
    }

    /**
     * Checks if a target value matches a specific template tag.
     * Supports both single strings and arrays of acceptable tags.
     */
    tag_matches(value, tag) {
        if (Array.isArray(tag)) {
            return tag.includes(value);
        }
        return value === tag;
    }

    /**
     * Computes IDF (Inverse Document Frequency) for every unique word across the intent dataset.
     * Normalized so that the maximum possible weight is scaled to 1.0.
     */
    calculate_auto_weights(intents) {
        const totalIntents = intents.length;
        if (!totalIntents) return {};

        const wordIntentCounts = {};
        for (const entry of intents) {
            const uniqueWordsInIntent = new Set();
            const inputs = entry.input || [];
            
            for (const sentence of inputs) {
                const words = String(sentence).toLowerCase().trim().split(/\s+/).filter(Boolean);
                for (const word of words) {
                    uniqueWordsInIntent.add(word);
                }
            }
            for (const word of uniqueWordsInIntent) {
                wordIntentCounts[word] = (wordIntentCounts[word] || 0) + 1;
            }
        }

        const weights = {};
        for (const [word, count] of Object.entries(wordIntentCounts)) {
            weights[word] = Math.log(totalIntents / count) + 0.1;
        }

        const values = Object.values(weights);
        const maxIdf = values.length ? Math.max(...values) : 1.0;

        const normalizedWeights = {};
        for (const [word, idf] of Object.entries(weights)) {
            normalizedWeights[word] = idf / maxIdf;
        }
        return normalizedWeights;
    }

    /**
     * Extracts the token with the highest IDF weight (the rarest/most specific word) from a prompt.
     */
    get_rarest_word(prompt) {
        if (!prompt || !this.weights) return null;
        const tokens = String(prompt).toLowerCase().split(/\s+/).filter(Boolean);
        if (!tokens.length) return null;

        let rarest = tokens[0];
        let maxWeight = this.weights[rarest] || 0.0;

        for (let i = 1; i < tokens.length; i++) {
            const token = tokens[i];
            const weight = this.weights[token] || 0.0;
            if (weight > maxWeight) {
                maxWeight = weight;
                rarest = token;
            }
        }
        return maxWeight > 0.0 ? rarest : null;
    }

    /**
     * Sanitization utility that strips specific vocabulary words outside strings and tags.
     * Uses a regex-callback atomic replacement pattern to avoid Javascript infinite loops.
     */
    strip_and_count(text, words_list) {
        if (!words_list || words_list.length === 0) {
            return [String(text).trim(), 0];
        }

        // Split text preventing removal of tags or literal strings content
        const tokens = String(text).split(/(<\|\|.*?\|\|>|".*?"|'.*?')/g);

        // Escape dictionary tokens to align with raw structure structures safely
        const escapedWords = words_list.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
        const anywherePattern = new RegExp(`\\s*\\b(?:${escapedWords})\\b\\s*`, 'gi');
        let totalRemoved = 0;

        for (let idx = 0; idx < tokens.length; idx++) {
            let t = tokens[idx];
            if (!t) {
                tokens[idx] = "";
                continue;
            }

            // Skip protected format chunks
            if ((t.startsWith("<||") && t.endsWith("||>")) ||
                (t.startsWith('"') && t.endsWith('"')) ||
                (t.startsWith("'") && t.endsWith("'"))) {
                continue;
            }

            // Atomic recursive substitution simulation tracking execution counts
            t = t.replace(anywherePattern, () => {
                totalRemoved++;
                return " ";
            });
            tokens[idx] = t;
        }

        // Reconstruct string structure layout normalizing spaces
        let cleanedText = tokens.join("").trim();
        cleanedText = cleanedText.replace(/\s+/g, ' ');
        return [cleanedText, totalRemoved];
    }

    /**
     * Processes user prompt extracting custom categorical metrics matching vocabulary keys.
     */
    strip_and_sentiment(user_prompt, sentiment_json, current_sentiment, target_categories = null) {
        const category_mapping = {
            "expletives": "expletives",
            "interjections": "interjection",
            "thanking_words": "thanking_words",
            "encouraging_words": "encouraging_words",
            "discouraging_words": "discouraging_words"
        };

        if (target_categories === null) {
            target_categories = Object.keys(category_mapping);
        }

        let current_prompt = user_prompt;

        for (const [key, json_key] of Object.entries(category_mapping)) {
            if (target_categories.includes(key)) {
                const word_list = sentiment_json[json_key] || [];
                const [cleaned, count] = this.strip_and_count(current_prompt, word_list);
                current_prompt = cleaned;
                current_sentiment[key] = count;
            }
        }

        // Emulates string.punctuation stripping behavior from Python
        const punctuationPattern = /^[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]/;
        while (current_prompt && punctuationPattern.test(current_prompt)) {
            current_prompt = current_prompt.substring(1);
        }

        // Normalize layout whitespaces immediately preceding standard punctuation marks
        const cleaned_prompt = current_prompt.replace(/\s+([,.!?;])/g, '$1');

        return [cleaned_prompt, current_sentiment];
    }

    /**
     * Generates a structural cynical face emoji mapped matching target emotion densities.
     */
    sentiment_emoji(sentiment) {
        if (!sentiment || typeof sentiment !== 'object') {
            return "😑";
        }

        const enc = sentiment.encouraging_words || 0;
        const thx = sentiment.thanking_words || 0;
        const dis = sentiment.discouraging_words || 0;
        const exp = sentiment.expletives || 0;
        const inj = sentiment.interjections || 0;

        const total_pos = enc + thx;

        if (!dis && !thx) {
            if (exp === 1) return "😒";
            if (exp === 2) return "😔";
            if (exp === 3) return "😞";
            if (exp === 4) return "😨";
            if (exp >= 5) return "😱";
        }

        if (!thx) {
            if (dis === 1) return "😠";
            if (dis === 2) return "😤";
            if (dis === 3) return "😪";
            if (dis === 4) return "😭";
            if (dis >= 5) return "😵";
        }

        if (exp > 0 && dis > 0) return "😡";
        if (exp > 0 && total_pos > 0) return "🤨";
        if (thx === 1 || enc === 1) return "😁";
        if (thx === 2 || enc === 2) return "😃";
        if (thx === 3 || enc === 3) return "😆";
        if (thx === 4 || enc === 4) return "😜";
        if (thx >= 5 || enc === 5) return "😘";
        if (inj === 1) return "😏";
        if (inj === 2) return "😒";
        if (inj === 3) return "🧐";
        if (inj === 4) return "😲";
        if (inj >= 5) return "😵";
        return "😑";
    }

    /**
     * Computes optimized Levenshtein distance similarity with rows vector strategy and early-exit.
     * Fixes row min calculation initialization to ensure precise bounds metrics.
     */
    levenshtein_similarity(s1, s2, threshold = 0.0) {
        s1 = String(s1).toLowerCase().trim();
        s2 = String(s2).toLowerCase().trim();
        let len1 = s1.length, len2 = s2.length;
        let max_len = Math.max(len1, len2);
        if (max_len === 0) return 1.0;

        // Pre-calculate maximum possible structural score bounds
        let max_possible_score = 1.0 - (Math.abs(len1 - len2) / max_len);
        if (max_possible_score < threshold) return 0.0;

        // Enforce s1 to represent the longest string item
        if (len1 < len2) {
            [s1, s2] = [s2, s1];
            [len1, len2] = [len2, len1];
        }

        let current_row = Array.from({ length: len2 + 1 }, (_, k) => k);
        let max_dist = Math.floor((1.0 - threshold) * max_len);

        for (let i = 1; i <= len1; i++) {
            let prev_cell = i;
            let c1 = s1[i - 1];
            let min_row_dist = Infinity; // Corrected initialization to capture accurate matrix row values minimums

            for (let j = 1; j <= len2; j++) {
                let substitutions = current_row[j - 1] + (c1 !== s2[j - 1] ? 1 : 0);
                let insertions = current_row[j] + 1;
                let deletions = prev_cell + 1;

                let current_value = Math.min(insertions, deletions, substitutions);
                current_row[j - 1] = prev_cell;
                prev_cell = current_value;

                if (current_value < min_row_dist) {
                    min_row_dist = current_value;
                }
            }

            current_row[len2] = prev_cell;

            // Trigger early-exit evaluations safely against true active minima bounds
            if (min_row_dist > max_dist) return 0.0;
        }

        return 1.0 - (current_row[len2] / max_len);
    }

    /**
     * Computes an asymmetric, order-independent sentence similarity score weighted by IDF specificity.
     */
    sentence_similarity(s1, s2, threshold = 0.0) {
        const anchor_tokens = String(s2).toLowerCase().trim().split(/\s+/).filter(Boolean);
        const query_tokens = String(s1).toLowerCase().trim().split(/\s+/).filter(Boolean);

        if (!anchor_tokens.length || !query_tokens.length) {
            return anchor_tokens.length === query_tokens.length ? 1.0 : 0.0;
        }

        const matched_indices = new Set();
        let total_score = 0.0;
        let max_possible_score = 0.0;

        for (const t_anchor of anchor_tokens) {
            let anchor_weight;
            if (t_anchor.length < 3) {
                anchor_weight = t_anchor in this.weights ? this.weights[t_anchor] : 0.05;
            } else {
                anchor_weight = t_anchor in this.weights ? this.weights[t_anchor] : 1.0;
                if (t_anchor.length === 3) {
                    anchor_weight *= 1.5;
                }
            }

            max_possible_score += anchor_weight;
            let best_word_sim = 0.0;
            let best_match_idx = -1;

            for (let idx = 0; idx < query_tokens.length; idx++) {
                if (matched_indices.has(idx)) continue;

                const t_query = query_tokens[idx];
                if (t_anchor === t_query) {
                    best_word_sim = 1.0;
                    best_match_idx = idx;
                    break;
                }

                const sim = this.levenshtein_similarity(t_anchor, t_query, threshold);
                if (sim > best_word_sim) {
                    best_word_sim = sim;
                    best_match_idx = idx;
                }
            }

            if (best_word_sim >= threshold) {
                total_score += best_word_sim * anchor_weight;
                if (best_match_idx !== -1) {
                    matched_indices.add(best_match_idx);
                }
            }
        }

        // Penalize unmatched query tokens absent from vocabulary
        for (const t_query of query_tokens) {
            if (t_query.length >= 3 && !(t_query in this.weights)) {
                max_possible_score += 0.5;
            }
        }

        return max_possible_score ? total_score / max_possible_score : 0.0;
    }
    /**
     * Resolves upcoming structural slots using step inspection paths across template criteria.
     * Aligns with match_structure to prevent index locking on vocabulary tokens.
     */
    find_candidates(structure, candidates) {
        // FIX: Track all structural tokens (both vocabs and variables) to properly advance the path pointer
        const clean_user = structure;
        const u_len = clean_user.length;

        for (const template of this.templates) {
            if (!template || !template.structure) continue;
            for (const path of template.structure) {
                let p_idx = 0;
                let u_idx = 0;

                while (p_idx < path.length && u_idx < u_len) {
                    const currentNode = path[p_idx];
                    const nodeTag = currentNode?.tag || currentNode?.["tag"];
                    
                    if (this.tag_matches(clean_user[u_idx], nodeTag)) {
                        u_idx += 1;
                        p_idx += 1;
                    } else if (currentNode && !currentNode.required && currentNode.required !== undefined) {
                        p_idx += 1;
                    } else {
                        break;
                    }
                }

                if (u_idx === u_len) {
                    if (p_idx < path.length) {
                        const target_node = path[p_idx];
                        const type = target_node?.type || target_node?.["type"];
                        const normalized_tag = target_node?.tag || target_node?.["tag"];

                        if (!type || !normalized_tag) continue;

                        let exists = candidates.some(([cType, cTag]) => 
                            cType === type && JSON.stringify(cTag) === JSON.stringify(normalized_tag)
                        );
                        if (!exists) {
                            candidates.push([type, normalized_tag]);
                        }

                        const isRequired = target_node.required !== undefined ? target_node.required : true;
                        if (!isRequired && (p_idx + 1) < path.length) {
                            const next_node = path[p_idx + 1];
                            const next_type = next_node?.type || next_node?.["type"];
                            const next_normalized_tag = next_node?.tag || next_node?.["tag"];

                            let next_exists = candidates.some(([cType, cTag]) => 
                                cType === next_type && JSON.stringify(cTag) === JSON.stringify(next_normalized_tag)
                            );
                            if (!next_exists) {
                                candidates.push([next_type, next_normalized_tag]);
                            }
                        }
                    }
                }
            }
        }
    }


    /**
     * Resolves matching template vocabulary keys exploiting Levenshtein text evaluations.
     */
    find_template(token, threshold) {
        if (!this.templates_vocabulary) return null;
        let match = null;
        let similarity = 0.0;

        for (const [tag, synonyms] of Object.entries(this.templates_vocabulary)) {
            for (const synonym of synonyms) {
                if (token === synonym) {
                    match = tag;
                    similarity = 1.0;
                    break;
                }

                if (token.length > 4 && synonym.length >= 4) {
                    const sim = this.levenshtein_similarity(token, synonym);
                    if (sim >= threshold && sim > similarity) {
                        similarity = sim;
                        match = tag;
                    }
                }
            }
            if (similarity === 1.0) break;
        }

        if (match && similarity < 1.0) {
            console.log(`${this.log_info}[find_template] Typo: '${token}' matched to '${match}' (Confidence: ${similarity.toFixed(2)})`);
        }
        return match;
    }
    
    /**
     * Transforms text arrays streams into parsed semantic tokens structure mappings.
     * Ensures strict compliance with Python's vocabulary validation logic.
     */
    parse_structure(sub_prompt, threshold) {
        const log_info = `${this.log_info}[abstract_input]`;

        const token_pattern = /"[^"\\]*(?:\\.[^"\\]*)*"|\S+/g;
        const raw_words = (String(sub_prompt).match(token_pattern) || [])
            .map(w => w.trim())
            .filter(Boolean);

        const stop_words = this.vocabulary?.stop_words || [];
        const expletives = this.expletives_list || this.vocabulary?.expletives || [];
        const interjections = this.interjection_list || this.vocabulary?.interjections || [];

        const working_tokens = raw_words.filter(w =>
            !stop_words.includes(w) &&
            !expletives.includes(w) &&
            !interjections.includes(w)
        );

        const structure = [];
        const slots = {};
        let i = 0;

        while (i < working_tokens.length) {
            let token = working_tokens[i].trim();
            const candidates = [];
            this.find_candidates(structure, candidates);

            const expects_variable = candidates.some(([type, _]) => {
                const rgxp = `<||${type}||>`;
                return rgxp in this.variable_types;
            });

            const is_explicit_multi_word = token.includes(" ");
            let match = null;

            if (!is_explicit_multi_word) {
                const hasVocab = candidates.some(([tType, _]) => tType === "vocab");
                if (hasVocab) {
                    const possible_match = this.find_template(token, threshold);
                    
                    if (possible_match) {
                        const expects_this_vocab = candidates.some(([type, tag]) => 
                            type === "vocab" && this.tag_matches(possible_match, tag)
                        );

                        // Preserves accurate matching fallback sequence mapping from Python
                        match = possible_match;
                        if (structure.length > 0 && expects_variable && !expects_this_vocab) {
                            match = null;
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
                    let python_regex = this.variable_types[rgxp];
                    let js_regex_string = python_regex
                        .replace(/\\A/g, '^')
                        .replace(/\\Z/g, '$');

                    const regex_pattern = new RegExp(js_regex_string, 'i');
                    const slot_name = tag.replace(/<\|\||\|\|>/g, "");

                    if (type === "string" && !token.startsWith('"')) {
                        let remainder = working_tokens.slice(i).join(" ");
                        if (regex_pattern.test(remainder)) {
                            structure.push(tag);
                            remainder = remainder.replace(/'/g, "'\\''");
                            slots[slot_name] = remainder;
                            
                            // FORZA L'USCITA IMMEDIATA DAL WHILE ESTERNO
                            i = working_tokens.length; 
                            matched_variable = true;
                            break; 
                        }
                    }

                    if (regex_pattern.test(token)) {
                        structure.push(tag);
                        token = token.replace(/^"+|"+$/g, '').replace(/'/g, "'\\''");
                        slots[slot_name] = token;
                        i++;
                        matched_variable = true;
                        break;
                    }
                }
            }

                      // Se abbiamo estratto una stringa e impostato i alla fine, usciamo dal while
            if (i >= working_tokens.length) {
                break;
            }

            if (matched_variable) {
                continue; // Ora è posizionato correttamente dentro l'iterazione del while
            }
            
            i++;
        }

        console.log(`${log_info} Slots finali: ${JSON.stringify(slots)}.`);
        return [structure, slots];
    }

    /**
     * Compares structural parsing tokens against listed intent path configurations.
     */
    match_structure(templates, structure) {
        let match = null;
        for (const b of templates) {
            if (!b || !b.structure) continue;
            for (const path of b.structure) {
                let prompt_i = 0;
                let template_i = 0;
                let template_match = true;

                while (template_i < path.length) {
                    const node = path[template_i];
                    const is_required = node.required !== undefined ? node.required : true;
                    if (
                        prompt_i < structure.length &&
                        this.tag_matches(structure[prompt_i], node.tag)
                    ) {
                        prompt_i++;
                        template_i++;
                    } else if (!is_required) {
                        template_i++;
                    } else {
                        template_match = false;
                        break;
                    }
                }

                if (template_match && prompt_i === structure.length) {
                    match = b;
                    break;
                }
            }
            if (match) break;
        }
        return match;
    }
}
