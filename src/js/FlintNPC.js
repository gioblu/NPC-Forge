/**
 * FlintNPC - Intelligent Chatbot Agent
 * Giovanni Blu Mitolo 2026
 *
 * Engine deterministico ad alta efficienza per agenti locali NLU.
 */
class FlintNPC {
    /**
     * Inizializza l'NPC con il bundle di dati del dataset e le impostazioni di configurazione.
     *
     * @param {String} npcName - Identificativo dell'agente NPC
     * @param {Object} bundleData - Dataset bundle strutturato contenente:
     *        { config, types, templates_vocabulary, vocabulary, dataset, personality, templates }
     * @param {String} [logLevel='INFO'] - Livello di verbosità del logging
     */
    constructor(npcName, bundleData = {}, logLevel = "INFO") {
        this.log_level = logLevel;
        this.name = npcName;
        
        this.config = bundleData.config || {};
        this.variable_types = bundleData.types || {};
        this.templates_vocabulary = bundleData.templates_vocabulary || {};
        this.vocabulary = bundleData.vocabulary || {};
        
        // Strutture dati interne
        this.dataset = bundleData.dataset || [];
        this.personality = bundleData.personality || [];
        this.templates = bundleData.templates || [];
        this.exact_match_map = {};
        this.metadata = {};
        
        // Active conversational context map
        this.active_context_map = {};
        
        // Liste di tracciamento sentiment
        this.expletives_list = [];
        this.interjection_list = [];
        this.thanking_list = [];
        this.encouraging_list = [];
        this.discouraging_list = [];
        
        this.sentiment = {
            "expletives": 0,
            "interjections": 0,
            "thanking_words": 0,
            "encouraging_words": 0,
            "discouraging_words": 0
        };
        
        this.rejection = {
            "message": ["<||unknown||>"],
            "permission": "yolo"
        };
        
        this.sentence_threshold = parseFloat(this.config.sentence_threshold ?? 0.75);
        this.word_threshold = parseFloat(this.config.word_threshold ?? 0.75);
        
        this.load_data();
        
        this.nlp = new FlintParser(
            this.name, 
            this.vocabulary,
            this.templates,
            this.templates_vocabulary,
            this.variable_types,
            this.log_level,
            [...this.dataset, ...this.personality].filter(block => block && typeof block === 'object' && "input" in block)
        );
    }

    /**
     * Aggiorna lo stato interno con un nuovo bundle di dati.
     * Ricarica il dataset, la personalità, i template e il vocabolario senza distruggere l'istanza.
     */
    set_bundle_data(bundleData = {}) {
        this.config = bundleData.config || {};
        this.variable_types = bundleData.types || {};
        this.templates_vocabulary = bundleData.templates_vocabulary || {};
        this.vocabulary = bundleData.vocabulary || {};

        this.dataset = bundleData.dataset || [];
        this.personality = bundleData.personality || [];
        this.templates = bundleData.templates || [];

        this.sentence_threshold = parseFloat(this.config.sentence_threshold ?? 0.75);
        this.word_threshold = parseFloat(this.config.word_threshold ?? 0.75);

        this.load_data();

        // Ristruttura l'istanza di FlintParser con i nuovi pesi IDF calcolati
        this.nlp = new FlintParser(
            this.name, 
            this.vocabulary,
            this.templates,
            this.templates_vocabulary,
            this.variable_types,
            this.log_level,
            [...this.dataset, ...this.personality].filter(block => block && typeof block === 'object' && "input" in block)
        );
    }

    /**
     * Carica configurazioni, vocabolari, metadati e indicizza gli intenti per il matching esatto.
     */
    load_data() {
        const v_lists = [
            "expletives", "interjection", "thanking_words", 
            "encouraging_words", "discouraging_words", "greetings"
        ];
        
        for (const v_file of v_lists) {
            const base_name = v_file.replace("_words", "");
            const data_list = this.vocabulary[v_file] || [];
            this[`${base_name}_list`] = data_list;
            if (data_list.length > 0) {
                this.metadata[v_file] = data_list;
                this.metadata[base_name] = data_list;
            }
        }
    
        // Estrazione dei tag di contesto dai nodi dizionario disponibili
        const allBlocks = [...this.dataset, ...this.personality, ...this.templates];
        for (const block of allBlocks) {
            if (block && typeof block === 'object' && !Array.isArray(block)) {
                for (const [k, v] of Object.entries(block)) {
                    if (k !== "input" && k !== "message") {
                        this.metadata[k] = v;
                    }
                }
            }
        }

        Object.assign(this.metadata, {
            "username": "user",
            "npc_name": String(this.config.npc_name || "NPC"),
            "response_classes": String(allBlocks.length),
            "computer_name": "LocalContext",
            "creation_date": String(this.config.creation_date || "2026-07-12"),
            "creator": String(this.config.creator || "Unknown"),
        });

        // Mappa delle varianti dei prompt per l'exact match deterministico
        // I blocchi di contesto NON vengono aggiunti qui; vengono caricati dinamicamente
        // in active_context_map a runtime quando il loro genitore viene matchato.
        for (const block of allBlocks) {
            if (block && block.input && Array.isArray(block.input)) {
                for (const inp of block.input) {
                    this.exact_match_map[String(inp).toLowerCase().trim()] = block;
                }
            }
        }
        
        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][load_data] Engine initialized.`);
        }
    }

    /**
     * Updates the active conversational context.
     * 
     * - "context": [...]  -> overwrites active context with new entries
     * - "context": []     -> explicitly clears the context
     * - no "context" key  -> context persists unchanged
     * 
     * This allows sibling context entries to remain active after one is consumed,
     * enabling flows like: "create dir" -> "move it" -> "delete it".
     */
    update_context(block) {
        if ("context" in block) {
            if (Array.isArray(block.context) && block.context.length > 0) {
                this.active_context_map = {};
                for (const ctx_block of block.context) {
                    if (ctx_block && typeof ctx_block === 'object' && "input" in ctx_block && Array.isArray(ctx_block.input)) {
                        for (const inp of ctx_block.input) {
                            this.active_context_map[String(inp).toLowerCase().trim()] = ctx_block;
                        }
                    }
                }
            } else {
                this.active_context_map = {};
            }
        }
    }

    /**
     * Returns a unified lookup map merging active context entries with
     * the global dataset. Context entries override dataset entries on
     * key collision, giving them priority.
     */
    _get_merged_match_map() {
        return { ...this.exact_match_map, ...this.active_context_map };
    }

    /**
     * Elabora un singolo messaggio utente eseguendo la pipeline deterministica ad albero.
     */
    process_message(user_prompt) {
        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][process_message] Prompt: ${user_prompt}`);
        }
        
        const rarest_word = this.nlp.get_rarest_word(user_prompt);
        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][process_message] Rarest word: '${rarest_word}'`);
        }

        if (!user_prompt) {
            return this.generate_response(this.rejection, {}, 0.0, "rejected");
        }
        
        // Pulisce imprecazioni e interiezioni per ottimizzare l'exact match
        let [stripped, newSentiment] = this.nlp.strip_and_sentiment(
            user_prompt,
            this.vocabulary,
            this.sentiment,
            ["expletives", "interjections"]
        );
        this.sentiment = newSentiment;

        // --- 1. UNIFIED EXACT MATCH (Context overrides Dataset) ---
        const merged_map = this._get_merged_match_map();
        
        if (stripped in merged_map) {
            const matched_block = merged_map[stripped];
            const is_context = stripped in this.active_context_map;
            const match_status = is_context ? "context match" : "exact match";
            
            if (this.log_level === "INFO") {
                console.log(`[chatbot.js][${this.name}][process_message] ${match_status}: ${stripped}`);
            }
            
            this.update_context(matched_block);
            
            [stripped, this.sentiment] = this.nlp.strip_and_sentiment(
                stripped,
                this.vocabulary,
                this.sentiment,
                ["encouraging_words", "discouraging_words", "thanking_words"]
            );
            return this.generate_response(matched_block, {}, 1.0, match_status);
        }

        // --- 2. TEMPLATE MATCH ---
        const [structure, slots] = this.nlp.parse_structure(user_prompt, this.sentence_threshold);
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
            
            const [, tsSentiment] = this.nlp.strip_and_sentiment(user_prompt, this.vocabulary, this.sentiment);                
            this.sentiment = tsSentiment;
            
            return this.generate_response(matched_template, cumulative_slots, 1.0, "template match");
        }

        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][process_message] NLP fallback: ${user_prompt}`);
        }

        // --- 3. UNIFIED PROBABILISTIC MATCH (Context + Dataset) ---
        let best_block = null;
        let best_score = -1.0;
        const related_intents = [];
        const seen_categories = new Set();
        
        // Pulisce il prompt dai connettivi sintattici non salienti
        let [sentiment_cleaned, probSentiment] = this.nlp.strip_and_sentiment(
            stripped, 
            this.vocabulary,
            this.sentiment,
            ["thanking_words", "encouraging_words", "discouraging_words"]
        );
        this.sentiment = probSentiment;

        // Regolazione lineare della soglia d'errore per stringhe ultra-brevi
        const tokenCount = sentiment_cleaned.split(/\s+/).filter(Boolean).length;
        const threshold = tokenCount <= 3 ? this.word_threshold : this.sentence_threshold;
        
        const maxSuggestions = parseInt(this.config.suggestions ?? 5, 10);

        // Itera sulla mappa unificata: il contesto sovrascrive il dataset in caso di collisione
        for (const [target_input, block] of Object.entries(merged_map)) {
            const score = this.nlp.sentence_similarity(
                sentiment_cleaned, 
                target_input, 
                Math.max(threshold, best_score)
            );
            if (score > best_score) {
                best_score = score;
                best_block = block;
            }
                
            if (related_intents.length < maxSuggestions && rarest_word && block && typeof block === 'object') {
                const category = block.category || "";
                let found_match = false;
                
                if (category.split("_").includes(rarest_word) || category.toLowerCase().includes(rarest_word)) {
                    found_match = true;
                }
            
                if (!found_match) {
                    const inputs = block.input || [];
                    if (Array.isArray(inputs) && inputs[0]) {
                        const input_words = String(inputs[0]).toLowerCase().split(/\s+/);
                        if (input_words.includes(rarest_word)) {
                            found_match = true;
                        }
                    }
                }
                
                if (found_match && !seen_categories.has(category)) {
                    related_intents.push(block);
                    seen_categories.add(category);
                }
            }
        }
            
        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][process_message] Best score: ${best_score}`);
        }

        if (best_score >= this.sentence_threshold && best_block) {
            this.update_context(best_block);
            return this.generate_response(best_block, {}, best_score, "probabilistic match");
        }

        // --- 4. REJECTION ---
        // Pulisce il contesto in caso di rigetto per prevenire follow-up obsoleti
        this.active_context_map = {};
        
        return this.generate_response(this.rejection, {}, 0.0, "rejected", related_intents);
    }

    /**
     * Scompone prompt composti complessi eseguendo in sequenza i compiti e aggregando le risposte.
     */
    process_messages(user_prompt) {
        const separator_pattern = /\n+|\d+\)|[;!?]/g;
        const raw_segments = String(user_prompt).split(separator_pattern);
        
        const sub_prompts = raw_segments.map(seg => seg.trim()).filter(Boolean);
        if (!sub_prompts.length) {
            return this.generate_response(this.rejection, {}, 0.0, "rejected");
        }

        const responses_list = [];
        const tools_list = [];
        const desc_list = [];
        const status_list = [];
        let lowest_confidence = 1.0;
        let lastRes = {};
        
        const aggregated_sentiment = {
            "expletives": 0,
            "interjections": 0,
            "thanking_words": 0,
            "encouraging_words": 0,
            "discouraging_words": 0
        };

        for (const sub_prompt of sub_prompts) {
            const res = this.process_message(sub_prompt);
            const current_conf = res.confidence ?? 0.0;
            
            if (current_conf < this.sentence_threshold || res.status === "rejected") {
                if (this.log_level === "WARNING" || this.log_level === "INFO") {
                    console.warn(`[chatbot.js][${this.name}][process_messages] Rejected '${sub_prompt}', confidence ${current_conf.toFixed(4)}`);
                }
                return this.generate_response(this.rejection, {}, 0, "rejected", res.related || []);
            }

            if (current_conf < lowest_confidence) {
                lowest_confidence = current_conf;
            }

            if ("response" in res) responses_list.push(res.response);
            
            // Mantiene la struttura a lista di liste (come .append in Python) e previene crash
            if ("tools" in res && Array.isArray(res.tools)) {
                tools_list.push(res.tools);
            }
            
            if ("description" in res) desc_list.push(res.description);
            if ("status" in res) status_list.push(res.status);
            
            lastRes = res;
            if (this.sentiment && typeof this.sentiment === 'object') {
                for (const key of Object.keys(aggregated_sentiment)) {
                    aggregated_sentiment[key] += (this.sentiment[key] || 0);
                }
            }
        }

        const concatenated_response = responses_list.join(" ");
        const concatenated_description = responses_list.join(" ");
        const concatenated_status = (status_list.length > 0 && status_list.every(s => s === status_list[0])) 
            ? status_list[0] 
            : status_list.join(", ");

        const final_output = Object.assign({}, lastRes);
        final_output["description"] = concatenated_description;
        final_output["tools"] = tools_list;
        final_output["response"] = concatenated_response;
        final_output["confidence"] = lowest_confidence;
        final_output["status"] = concatenated_status;
        final_output["sentiment"] = aggregated_sentiment;
        
        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][process_messages] Output: '${concatenated_response} - ${JSON.stringify(aggregated_sentiment)}'`);
        }
        return final_output;
    }

    /**
     * Compila i payload di output eseguendo il rendering macro ricorsivo e interpolando i parametri estratti.
     */
    generate_response(block, slots, confidence, status, related = []) {
        if (!block) {
            return {
                "status": status, 
                "confidence": confidence, 
                "response": "Intent not understood.", 
                "slots": slots, 
                "sentiment": this.sentiment
            };
        }
            
        const _choice = (item) => {
            if (Array.isArray(item)) {
                return item.length === 0 ? "" : item[Math.floor(Math.random() * item.length)];
            }
            return item;
        };
            
        // Renderizzatore ricorsivo dei segnaposto <||tag||>
        const render_tags = (text) => {
            if (!text) return "";
            text = String(text);
            const current_tags = text.match(/<\|\|(.*?)\|\|>/g);
            if (!current_tags) return text;
            const previous_text = text;
            
            for (const rawTag of current_tags) {
                const tag = rawTag.replace(/<\|\||\|\|>/g, "");
                
                for (const type of ["completion", "unknown"]) {    
                    if (tag === type && !(type in slots)) {
                        if (this.metadata[type]) {
                            slots[type] = _choice(this.metadata[type]);
                        }
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
        
        // Mappatura ricorsiva profonda per la struttura degli strumenti (Tools Schema Engine)
        const render_all_tags = (data) => {
            if (data && typeof data === 'object' && !Array.isArray(data)) {
                const resObj = {};
                for (const [k, v] of Object.entries(data)) {
                    resObj[k] = render_all_tags(v);
                }
                return resObj;
            } else if (Array.isArray(data)) {
                return data.map(item => render_all_tags(item));
            } else if (typeof data === 'string') {
                return render_tags(data);
            }
            return data;
        };

        const output_data = block.message !== undefined ? block.message : (block.output !== undefined ? block.output : "");
        const final_output = render_tags(_choice(output_data));
        const thinking_data = block.thinking;        
        let thinking = _choice(thinking_data);
        if (thinking) {
            thinking = render_tags(thinking);
        }
        
        const payload = {
            "confidence": confidence, 
            "response": final_output,
            "related" : related,
            "permission": block.permission || "ask", 
            "sentiment": Object.assign({}, this.sentiment),
            "emoji": this.nlp.sentiment_emoji(this.sentiment),
            "slots": slots, 
            "status": status, 
            "thinking": thinking || undefined
        };        
        
        if ("description" in block) {
            payload["description"] = render_tags(block["description"]);
        }

        if ("tools" in block && Array.isArray(block.tools)) {
            const tools_copy = JSON.parse(JSON.stringify(block.tools));
            payload["tools"] = render_all_tags(tools_copy);
        }

        if (this.log_level === "INFO") {
            console.log(`[chatbot.js][${this.name}][generate_response] Payload: ${JSON.stringify(payload)}`);
        }
        return payload;
    }
}