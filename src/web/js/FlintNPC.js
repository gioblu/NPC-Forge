/**
 * FlintNPC - Intelligent Chatbot Agent
 * Giovanni Blu Mitolo 2026
 * Aligned with Python NDF 0.0 specification.
 */
class FlintNPC {
    constructor(npcName, bundleData = {}, logLevel = "INFO") {
        this.log_level = logLevel;
        this.name = npcName;
        
        this.config = bundleData.config || {};
        this.variable_types = bundleData.types || {};
        this.templates_vocabulary = bundleData.templates_vocabulary || {};
        this.vocabulary = bundleData.vocabulary || {};
        
        this._base_dataset = [...(bundleData.dataset || [])];
        this.loaded_datasets = new Map();
        
        this.dataset = [...this._base_dataset];
        this.personality = bundleData.personality || [];
        this.templates = bundleData.templates || [];
        this.exact_match_map = {};
        this.metadata = {};
        
        this.active_context_map = {};
        this._precomputed_context_intents = {};
        
        this.sentiment = {
            "expletives": 0, "interjections": 0, "thanking_words": 0,
            "encouraging_words": 0, "discouraging_words": 0
        };
        
        this.rejection = { "output": ["<||unknown||>"], "permission": "yolo" };
        this.threshold = parseFloat(this.config.threshold ?? 0.75);
        
        this.load_data();
        this._build_nlp();
    }

    set_bundle_data(bundleData = {}) {
        this.config = bundleData.config || {};
        this.variable_types = bundleData.types || {};
        this.templates_vocabulary = bundleData.templates_vocabulary || {};
        this.vocabulary = bundleData.vocabulary || {};
        
        this._base_dataset = [...(bundleData.dataset || [])];
        this.loaded_datasets = new Map();
        
        this.dataset = [...this._base_dataset];
        this.personality = bundleData.personality || [];
        this.templates = bundleData.templates || [];
        this.threshold = parseFloat(this.config.threshold ?? 0.75);

        this.load_data();
        this._build_nlp();
    }

    load_data() {
        const v_lists = ["expletives", "interjection", "thanking_words", "encouraging_words", "discouraging_words", "greetings"];
        for (const v_file of v_lists) {
            const base_name = v_file.replace("_words", "");
            const data_list = this.vocabulary[v_file] || [];
            this[`${base_name}_list`] = data_list;
            if (data_list.length > 0) {
                this.metadata[v_file] = data_list;
                this.metadata[base_name] = data_list;
            }
        }
    
        const allBlocks = [...this.dataset, ...this.personality, ...this.templates];
        for (const block of allBlocks) {
            if (block && typeof block === 'object' && !Array.isArray(block)) {
                for (const [k, v] of Object.entries(block)) {
                    if (k !== "input") this.metadata[k] = v;
                }
            }
        }

        Object.assign(this.metadata, {
            "username": typeof process !== 'undefined' && process.env ? (process.env.USER || "user") : "user",
            "npc_name": String(this.config.name || "NPC"),
            "response_classes": String(allBlocks.length),
            "computer_name": "LocalContext",
            "creation_date": String(this.config.creation_date || "2026-07-12"),
            "creator": String(this.config.creator || "Unknown"),
        });

        for (const block of allBlocks) {
            if (block && block.input && Array.isArray(block.input)) {
                for (const inp of block.input) {
                    if (typeof inp === 'string') {
                        this.exact_match_map[inp.toLowerCase().trim()] = block;
                    }
                }
            }
        }
        
        if (this.log_level === "INFO") {
            console.log(`[FlintNPC.js][${this.name}][load_data] Engine initialized.`);
        }
    }

    _build_intent_signatures() {
        this._precomputed_intents = {};
        this._precomputed_context_intents = {};
        const merged_map = this._get_merged_match_map();
        const synonym_weight = parseFloat(this.config.synonym_contribution ?? 0.0);
        
        for (const [target_input, block] of Object.entries(merged_map)) {
            this._precomputed_intents[target_input] = this.nlp.precompute_intent_signature(
                target_input, block, synonym_weight
            );
        }
    }

    update_context(block) {
        if ("context" in block) {
            this.active_context_map = {};
            this._precomputed_context_intents = {};
            
            if (Array.isArray(block.context) && block.context.length > 0) {
                const synonym_weight = parseFloat(this.config.synonym_contribution ?? 0.0);
                for (const ctx_block of block.context) {
                    if (ctx_block && typeof ctx_block === 'object' && "input" in ctx_block) {
                        for (const inp of ctx_block.input) {
                            const clean_inp = String(inp).toLowerCase().trim();
                            this.active_context_map[clean_inp] = ctx_block;
                            this._precomputed_context_intents[clean_inp] = this.nlp.precompute_intent_signature(
                                clean_inp, ctx_block, synonym_weight
                            );
                        }
                    }
                }
            }
        }
    }

    _get_merged_match_map() {
        return { ...this.exact_match_map, ...this.active_context_map };
    }

    process_message(user_prompt) {
        if (this.log_level === "INFO") {
            console.log(`[FlintNPC.js][${this.name}][process_message] Prompt: ${user_prompt}`);
        }
        
        const rarest_word = this.nlp.get_rarest_word(user_prompt);
        if (!rarest_word) {
            return this.generate_response(this.rejection, {}, 0.0, "rejected", []);
        }

        if (!user_prompt) {
            return this.generate_response(this.rejection, {}, 0.0, "rejected");
        }
        
        let [stripped, newSentiment] = this.nlp.strip_and_sentiment(
            user_prompt, this.vocabulary, this.sentiment, ["expletives", "interjections"]
        );
        this.sentiment = newSentiment;

        const merged_map = this._get_merged_match_map();
        const lookup = stripped.toLowerCase().trim();
        
        if (lookup in merged_map) {
            const matched_block = merged_map[lookup];
            const match_status = (lookup in this.active_context_map) ? "context match" : "exact match";
            
            this.update_context(matched_block);
            [, this.sentiment] = this.nlp.strip_and_sentiment(
                stripped, this.vocabulary, this.sentiment, 
                ["encouraging_words", "discouraging_words", "thanking_words"]
            );
            return this.generate_response(matched_block, {}, 1.0, match_status);
        }

        const [structure, slots] = this.nlp.parse_structure(user_prompt, this.threshold);
        const matched_template = this.nlp.match_structure(this.templates, structure);

        if (matched_template) {
            if (this.log_level === "INFO") {
                console.log(`[Template Match] ${matched_template.intent || ""}`);
            }
            this.update_context(matched_template);
            const cumulative_slots = { ...slots };
            if (!("content" in cumulative_slots) && ("string" in cumulative_slots)) {
                cumulative_slots["content"] = cumulative_slots["string"];
            }
            [, this.sentiment] = this.nlp.strip_and_sentiment(user_prompt, this.vocabulary, this.sentiment);
            return this.generate_response(matched_template, cumulative_slots, 1.0, "template match");
        }

        let [user_prompt_clean, probSentiment] = this.nlp.strip_and_sentiment(
            stripped, this.vocabulary, this.sentiment, 
            ["encouraging_words", "discouraging_words", "thanking_words"]
        );
        this.sentiment = probSentiment;
        
        const query_tokens = user_prompt_clean.toLowerCase().split(/\s+/).filter(Boolean);
        const query_token_count = query_tokens.length;
        
        const threshold = this.threshold;
        const min_related_score = 0.25;

        let best_context_block = null;
        let best_context_score = -1.0;
        
        for (const [inp, precomputed] of Object.entries(this._precomputed_context_intents)) {
            const target_token_count = precomputed.token_count || 0;
            if (query_token_count === 0 || target_token_count === 0) continue;

            const q_idx = Math.min(query_token_count, target_token_count) - 1;
            const max_possible_score = precomputed.max_weight_sums[q_idx] / precomputed.max_score;
            
            if (max_possible_score < threshold) continue;
                
            const score = this.nlp.fast_score_calculation(
                query_tokens, precomputed, Math.max(threshold, best_context_score)
            );
            if (score > best_context_score) {
                best_context_score = score;
                best_context_block = precomputed.block;
            }
        }

        if (best_context_score >= this.threshold) {
            this.update_context(best_context_block);
            return this.generate_response(best_context_block, {}, best_context_score, "probabilistic match");
        }

        let best_block = null;
        let best_score = -1.0;

        for (const [target_input, precomputed] of Object.entries(this._precomputed_intents)) {
            const target_token_count = precomputed.token_count || 0;
            if (query_token_count === 0 || target_token_count === 0) continue;

            const q_idx = Math.min(query_token_count, target_token_count) - 1;
            const max_possible_score = precomputed.max_weight_sums[q_idx] / precomputed.max_score;
            if (max_possible_score < threshold) continue;

            if (rarest_word) {
                if (!precomputed.token_set.has(rarest_word)) {
                    const rarest_tag = this.nlp._synonym_map.get(rarest_word);
                    if (!rarest_tag || !precomputed.tag_set.has(rarest_tag)) {
                        continue;
                    }
                }
            }

            const score = this.nlp.fast_score_calculation(
                query_tokens, precomputed, Math.max(threshold, best_score)
            );

            if (score > best_score) {
                best_score = score;
                best_block = precomputed.block;
            }
        }

        if (best_score >= this.threshold && best_block) {
            this.update_context(best_block);
            return this.generate_response(best_block, {}, best_score, "probabilistic match");
        }

        const top_related = [];
        const max_suggestions = parseInt(this.config.suggestions ?? 5, 10);

        for (const [target_input, precomputed] of Object.entries(this._precomputed_intents)) {
            const target_token_count = precomputed.token_count || 0;
            if (query_token_count === 0 || target_token_count === 0) continue;

            const q_idx = Math.min(query_token_count, target_token_count) - 1;
            const max_possible_score = precomputed.max_weight_sums[q_idx] / precomputed.max_score;
            
            if (max_possible_score < min_related_score) continue;

            if (rarest_word) {
                if (!precomputed.token_set.has(rarest_word)) {
                    const rarest_tag = this.nlp._synonym_map.get(rarest_word);
                    if (!rarest_tag || !precomputed.tag_set.has(rarest_tag)) {
                        continue;
                    }
                }
            }

            const score = this.nlp.fast_score_calculation(query_tokens, precomputed, min_related_score);
            if (score >= min_related_score) {
                top_related.push([score, precomputed.token_count || 0, precomputed.block]);
            }
        }

        top_related.sort((a, b) => {
            if (b[0] !== a[0]) return b[0] - a[0];
            return a[1] - b[1];
        });
        
        const related_intents = [];
        const seen_blocks = new Set();
        for (const [score, token_count, block] of top_related) {
            const inputs = block.input || [];
            const input_sig = (inputs.length > 0 && Array.isArray(inputs)) ? String(inputs[0]).toLowerCase() : String(block);
            
            if (!seen_blocks.has(input_sig)) {
                related_intents.push(block);
                seen_blocks.add(input_sig);
            }
            
            if (related_intents.length >= max_suggestions) break;
        }
        
        return this.generate_response(this.rejection, {}, 0.0, "rejected", related_intents);
    }

    process_messages(user_prompt) {
        const separator_pattern = /\n+|\d+\)|[;!?]/g;
        const raw_segments = String(user_prompt).split(separator_pattern);
        const sub_prompts = raw_segments.map(seg => seg.trim()).filter(Boolean);
        
        if (!sub_prompts.length) {
            return this.generate_response(this.rejection, {}, 0.0, "rejected");
        }

        const responses_list = [], tools_list = [], desc_list = [], status_list = [], permission_list = [];
        let lowest_confidence = 1.0;
        let lastRes = {};
        
        const aggregated_sentiment = { "expletives": 0, "interjections": 0, "thanking_words": 0, "encouraging_words": 0, "discouraging_words": 0 };

        for (const sub_prompt of sub_prompts) {
            const res = this.process_message(sub_prompt);
            const current_conf = res.confidence ?? 0.0;
            
            if (current_conf < this.threshold || res.status === "rejected") {
                if (this.log_level === "WARNING" || this.log_level === "INFO") {
                    console.warn(`[FlintNPC.js][${this.name}][process_messages] Rejected '${sub_prompt}', confidence ${current_conf.toFixed(4)}`);
                }
                return this.generate_response(this.rejection, {}, 0.0, "rejected", res.related || []);
            }

            if (current_conf < lowest_confidence) lowest_confidence = current_conf;

            if ("response" in res) responses_list.push(res.response);
            if ("tools" in res && Array.isArray(res.tools)) tools_list.push(res.tools);
            if ("description" in res) desc_list.push(res.description);
            if ("status" in res) status_list.push(res.status);
            if ("permission" in res) permission_list.push(res.permission);
            
            lastRes = res;
            if (this.sentiment && typeof this.sentiment === 'object') {
                for (const key of Object.keys(aggregated_sentiment)) {
                    aggregated_sentiment[key] += (this.sentiment[key] || 0);
                }
            }
        }

        const concatenated_response = responses_list.join(" ");
        const concatenated_description = desc_list.join(" "); 
        const concatenated_status = (status_list.length > 0 && status_list.every(s => s === status_list[0])) 
            ? status_list[0] 
            : status_list.join(", ");

        let permission = "ask";
        for (const p of permission_list) {
            const p_lower = String(p).toLowerCase().trim();
            if (p_lower === "ask") permission = "ask";
            if ((p_lower === "yolo" || p_lower === "auto") && permission !== "ask") {
                permission = p_lower;
            }
        }

        const final_output = Object.assign({}, lastRes);
        final_output["description"] = concatenated_description;
        final_output["tools"] = tools_list;
        final_output["response"] = concatenated_response;
        final_output["confidence"] = lowest_confidence;
        final_output["status"] = concatenated_status;
        final_output["permission"] = permission;
        final_output["sentiment"] = aggregated_sentiment;
        
        if (this.log_level === "INFO") {
            console.log(`[FlintNPC.js][${this.name}][process_messages] Output: '${concatenated_response}'`);
        }
        return final_output;
    }

    generate_response(block, slots, confidence, status, related = []) {
        if (!block) {
            return { "status": status, "confidence": confidence, "response": "Intent not understood.", "slots": slots, "sentiment": this.sentiment };
        }
            
        const _choice = (item) => Array.isArray(item) ? (item.length === 0 ? "" : item[Math.floor(Math.random() * item.length)]) : item;
            
        const render_tags = (text) => {
            if (!text) return "";
            text = String(text);
            const current_tags = text.match(/<\|\|(.*?)\|\|>/g);
            if (!current_tags) return text;
            const previous_text = text;
            
            for (const rawTag of current_tags) {
                const tag = rawTag.replace(/<\|\||\|\|>/g, "");
                
                for (const type of ["completion", "unknown", "related"]) {    
                    if (tag === type && !(type in slots) && this.metadata[type]) {
                        slots[type] = _choice(this.metadata[type]);
                    }
                }

                if (tag in slots) {
                    text = text.split(rawTag).join(String(slots[tag]));
                } else if (tag in this.metadata) {
                    const val = this.metadata[tag];
                    text = text.split(rawTag).join(String(Array.isArray(val) ? _choice(val) : val));
                } else {
                    text = text.split(rawTag).join("");
                }
            }
            
            if (text === previous_text) return text; 
            return text.match(/<\|\|(.*?)\|\|>/) ? render_tags(text) : text;
        };
        
        const render_all_tags = (data) => {
            if (data && typeof data === 'object' && !Array.isArray(data)) {
                const resObj = {};
                for (const [k, v] of Object.entries(data)) resObj[k] = render_all_tags(v);
                return resObj;
            } else if (Array.isArray(data)) {
                return data.map(item => render_all_tags(item));
            } else if (typeof data === 'string') {
                return render_tags(data);
            }
            return data;
        };

        let output_data = block.output !== undefined ? block.output : "";
        let raw_output = _choice(output_data);

        if (related && related.length > 0 && status === "rejected") { 
            if (!raw_output || raw_output.trim() === "" || raw_output.includes("<||related||>") || raw_output.includes("<||unknown||>")) {
                raw_output = "I'm not quite sure I understand, but perhaps one of these is what you're looking for:";
            }
        }
        
        const final_output = render_tags(raw_output);
        const thinking_data = block.thinking;        
        let thinking = _choice(thinking_data);
        if (thinking) thinking = render_tags(thinking);
        
        const payload = {
            "npc": this.config.name || "NPC",
            "confidence": confidence, 
            "response": final_output,
            "related": related,
            "permission": block.permission || "ask", 
            "sentiment": Object.assign({}, this.sentiment),
            "emoji": this.nlp.sentiment_emoji(this.sentiment),
            "slots": slots, 
            "status": status, 
            "thinking": thinking || undefined
        };        
        
        if ("description" in block) payload["description"] = render_tags(block["description"]);

        if ("tools" in block && Array.isArray(block.tools)) {
            const tools_copy = JSON.parse(JSON.stringify(block.tools));
            payload["tools"] = render_all_tags(tools_copy);
            const commands_config = this.config.commands || {};
            for (const tool of payload["tools"]) {
                if (tool && typeof tool === 'object' && "arguments" in tool) {
                    const args = tool.arguments;
                    if ("command" in args && "language" in args) {
                        const lang = String(args.language).toLowerCase();
                        if (lang in commands_config) {
                            const wrapper = commands_config[lang];
                            const head = wrapper.head || "";
                            const tail = wrapper.tail || "";
                            args.command = `${head}${args.command}${tail}`;
                        }
                    }
                }
            }
        }

        if (this.log_level === "INFO") {
            console.log(`[FlintNPC.js][${this.name}][generate_response] Payload: ${JSON.stringify(payload)}`);
        }
        return payload;
    }

    async addRemoteDataset(datasetInfo) {
        if (this.log_level === "INFO") {
            console.log(`[FlintNPC.js][${this.name}] Fetching remote dataset: ${datasetInfo.id} from ${datasetInfo.url}`);
        }

        if (this.loaded_datasets.has(datasetInfo.id)) {
            return { success: false, message: "Dataset already loaded" };
        }

        try {
            const response = await fetch(datasetInfo.url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
            }
            
            const contentType = response.headers.get("content-type") || "";
            const text = await response.text();

            // GUARD 1: Catch HTML error pages (e.g., GitHub 404, rate limits, or CORS blocks)
            if (text.trim().startsWith("<")) {
                throw new Error("Received HTML instead of JSON/JSONL. The URL may be incorrect, private, or rate-limited.");
            }

            let newEntries = [];

            // GUARD 2: Try standard JSON array first if it looks like one
            if (contentType.includes("application/json") || text.trim().startsWith("[")) {
                try {
                    const parsed = JSON.parse(text);
                    if (Array.isArray(parsed)) {
                        newEntries = parsed;
                    } else if (parsed && typeof parsed === 'object') {
                        newEntries = [parsed];
                    }
                } catch (e) {
                    console.warn(`[FlintNPC] Standard JSON parse failed, falling back to JSONL. Error:`, e.message);
                }
            }

            // GUARD 3: Memory-efficient JSONL line-by-line parsing
            if (newEntries.length === 0) {
                console.log(`[FlintNPC] Parsing file as JSONL...`);
                const lines = text.split('\n');
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (line.length > 0) {
                        try {
                            const entry = JSON.parse(line);
                            if (entry && typeof entry === 'object') {
                                newEntries.push(entry);
                            }
                        } catch (err) {
                            // Log the first few malformed lines to help debug, then stay silent
                            if (newEntries.length === 0 && i < 5) {
                                console.warn(`[FlintNPC] Failed to parse JSONL line ${i + 1}:`, line.substring(0, 100));
                            }
                        }
                    }
                }
            }

            if (newEntries.length === 0) {
                throw new Error("Parsed dataset is empty. The file may be empty, completely malformed, or an HTML error page.");
            }

            console.log(`[FlintNPC] ✅ Successfully parsed ${newEntries.length} entries from ${datasetInfo.id}.`);

            this.loaded_datasets.set(datasetInfo.id, newEntries);
            
            this.config.active_datasets = this.config.active_datasets || [];
            if (!this.config.active_datasets.includes(datasetInfo.id)) {
                this.config.active_datasets.push(datasetInfo.id);
            }

            // Rebuild the engine with the new data
            this._rebuild_engine();

            return { 
                success: true, 
                message: `Successfully loaded ${newEntries.length} entries from ${datasetInfo.id}`,
                count: newEntries.length
            };
        } catch (error) {
            console.error(`[FlintNPC.js][${this.name}] ❌ Failed to load dataset:`, error);
            return { success: false, message: error.message };
        }
    }

    removeRemoteDataset(datasetId) {
        if (this.loaded_datasets.has(datasetId)) {
            this.loaded_datasets.delete(datasetId);
            if (this.config.active_datasets) {
                this.config.active_datasets = this.config.active_datasets.filter(id => id !== datasetId);
            }
            this._rebuild_engine();
            return { success: true, message: `Removed ${datasetId}` };
        }
        return { success: false, message: "Dataset not found" };
    }

    _build_nlp() {
        const intents = [...this.dataset, ...this.personality].filter(
            block => block && typeof block === 'object' && ("input" in block || "prompt" in block || "query" in block)
        );

        console.log(`[FlintNPC] _build_nlp: total dataset entries=${this.dataset.length}, valid intents=${intents.length}`);

        this.nlp = new FlintParser(
            this.name, 
            this.vocabulary,
            this.templates,
            this.templates_vocabulary,
            this.variable_types,
            this.log_level,
            intents
        );
        
        this._build_intent_signatures();
    }

    _rebuild_engine() {
        let combined_dataset = [...this._base_dataset];
        for (const entries of this.loaded_datasets.values()) {
            combined_dataset = combined_dataset.concat(entries);
        }
        
        this.dataset = combined_dataset;
        this.load_data();
        this._build_nlp();
        
        if (this.log_level === "INFO") {
            console.log(`[FlintNPC.js][${this.name}] Engine rebuilt with ${this.dataset.length} total dataset entries.`);
        }
    }
}