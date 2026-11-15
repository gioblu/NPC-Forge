/**
 * FlintNPC - Intelligent Chatbot Agent (aligned to final Python FlintNPC.py)
 * Giovanni Blu Mitolo 2026 — NDF 0.0
 */
const _PUNCT = new Set([..."!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"]);
function _rstripPunct(s){ let e=s.length; while(e>0 && _PUNCT.has(s[e-1])) e--; return s.slice(0,e); }

class FlintNPC {
    static SENTIMENT_KEYS = ["expletives","interjections","thanking_words","encouraging_words","discouraging_words"];
    static POSITIVE_CATEGORIES = ["encouraging_words","discouraging_words","thanking_words"];

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
        this._ctx_word_idx = new Map();
        this._ctx_tag_idx = new Map();
        this.sentiment = {}; for (const k of FlintNPC.SENTIMENT_KEYS) this.sentiment[k]=0;
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
        const v_lists = ["expletives","interjection","thanking_words","encouraging_words","discouraging_words","greetings"];
        for (const v_file of v_lists) {
            const base_name = v_file.replace("_words","");
            const data_list = this.vocabulary[v_file] || [];
            this[`${base_name}_list`] = data_list;
            if (data_list.length > 0) { this.metadata[v_file]=data_list; this.metadata[base_name]=data_list; }
        }
        const allBlocks = [...this.dataset, ...this.personality, ...this.templates];
        for (const block of allBlocks) {
            if (block && typeof block==='object' && !Array.isArray(block)) {
                for (const [k,v] of Object.entries(block)) if (k!=="input") this.metadata[k]=v;
            }
        }
        Object.assign(this.metadata, {
            "username": typeof process!=='undefined' && process.env ? (process.env.USER||"user") : "user",
            "npc_name": String(this.config.name||"NPC"),
            "response_classes": String(allBlocks.length),
            "computer_name": "LocalContext",
            "creation_date": String(this.config.creation_date||"2026-07-12"),
            "creator": String(this.config.creator||"Unknown"),
        });
        for (const block of allBlocks) {
            if (block && block.input && Array.isArray(block.input)) {
                for (const inp of block.input) if (typeof inp==='string') this.exact_match_map[inp.toLowerCase().trim()]=block;
            }
        }
        if (this.log_level==="INFO") console.log(`[FlintNPC.js][${this.name}][load_data] Engine initialized.`);
    }

    // ---- inverted index ----
    _build_signatures(match_map) {
        const syn_w = parseFloat(this.config.synonym_contribution ?? 0.0);
        const sigs={}, word_idx=new Map(), tag_idx=new Map();
        let order=0;
        for (const [inp,block] of Object.entries(match_map)) {
            const sig=this.nlp.precompute_intent_signature(inp,block,syn_w);
            sig._order=order++;
            sigs[inp]=sig;
            const seen=new Set();
            for (const t of sig.tokens) {
                if (!seen.has(t)) { seen.add(t); if(!word_idx.has(t)) word_idx.set(t,[]); word_idx.get(t).push(sig); }
            }
            for (const t of sig.tag_set) { if(!tag_idx.has(t)) tag_idx.set(t,[]); tag_idx.get(t).push(sig); }
        }
        return [sigs,word_idx,tag_idx];
    }
    _build_intent_signatures() {
        [this._precomputed_intents,this._word_idx,this._tag_idx]=this._build_signatures(this._get_merged_match_map());
    }
    update_context(block) {
        if (!block || !("context" in block)) return;
        this.active_context_map={};
        if (Array.isArray(block.context)) {
            for (const cb of block.context) {
                if (cb && typeof cb==='object' && "input" in cb) {
                    for (const inp of cb.input) this.active_context_map[String(inp).toLowerCase().trim()]=cb;
                }
            }
        }
        [this._precomputed_context_intents,this._ctx_word_idx,this._ctx_tag_idx]=this._build_signatures(this.active_context_map);
    }
    _match_exact(key) {
        if (key in this.active_context_map) return [this.active_context_map[key],true];
        if (key in this.exact_match_map) return [this.exact_match_map[key],false];
        return [null,false];
    }
    _get_merged_match_map(){ return {...this.exact_match_map,...this.active_context_map}; }
    _candidates(sigs,word_idx,tag_idx,rarest_word) {
        if (!rarest_word) return Object.values(sigs);
        const seen=new Set(),out=[];
        const tag=this.nlp._synonym_map.get(rarest_word);
        const list=(word_idx.get(rarest_word)||[]).concat(tag?(tag_idx.get(tag)||[]):[]);
        for (const sig of list) if (!seen.has(sig)) { seen.add(sig); out.push(sig); }
        out.sort((a,b)=>a._order-b._order);
        return out;
    }
    
    _fuzzy_best(query_tokens, sigs, word_idx, tag_idx, cutoff, rarest_word) {
        const q = query_tokens.length;
        if (!q) return [null, -1.0];
        const eps = parseFloat(this.config.tie_break_epsilon ?? 0.05);
        const scored = []; let best = -1.0;
        for (const sig of this._candidates(sigs, word_idx, tag_idx, rarest_word)) {
            const t = sig.token_count || 0;
            if (!t) continue;
            const bound = sig.max_weight_sums[Math.min(q, t) - 1] / sig.max_score;
            if (bound < cutoff || bound < best - eps) continue;
            const [score, matched] = this.nlp._score_and_matched(query_tokens, sig, cutoff);
            if (score > best) best = score;
            scored.push([score, matched, sig]);
        }
        if (!scored.length || best < cutoff) return [null, best];
        const floor = Math.max(cutoff, best - eps);
        const pool = scored.filter(x => x[0] >= floor);
        if (!pool.length) return [null, best];
        pool.sort((a, b) => (b[1] - a[1]) || (b[0] - a[0]) || (a[2]._order - b[2]._order));
        return [pool[0][2].block, pool[0][0]];
    }

    process_message(user_prompt) {
        if (this.log_level==="INFO") console.log(`[FlintNPC.js][${this.name}][process_message] Prompt: ${user_prompt}`);
        this.sentiment={}; for (const k of FlintNPC.SENTIMENT_KEYS) this.sentiment[k]=0;   // per-message reset
        const [stripped]=this.nlp.strip_and_sentiment(user_prompt,this.vocabulary,this.sentiment,["expletives","interjections"]);

        const lookup=String(stripped).toLowerCase().trim();
        let [block,is_ctx]=this._match_exact(lookup);
        if (block===null) [block,is_ctx]=this._match_exact(_rstripPunct(lookup).trim());
        if (block!==null) {
            const status=is_ctx?"context match":"exact match";
            this.update_context(block);
            this.nlp.strip_and_sentiment(stripped,this.vocabulary,this.sentiment,FlintNPC.POSITIVE_CATEGORIES);
            return this.generate_response(block,{},1.0,status);
        }

        const [structure,slots]=this.nlp.parse_structure(user_prompt,this.threshold);   // template BEFORE gate
        const matched_template=this.nlp.match_structure(this.templates,structure);
        if (matched_template) {
            if (this.log_level==="INFO") console.log(`[Template Match] ${matched_template.intent||""}`);
            this.update_context(matched_template);
            const cum={...slots};
            if (!("content" in cum) && ("string" in cum)) cum.content=cum.string;
            this.nlp.strip_and_sentiment(user_prompt,this.vocabulary,this.sentiment);
            return this.generate_response(matched_template,cum,1.0,"template match");
        }

        const rarest_word=this.nlp.get_rarest_word(user_prompt);   // gate only guards fuzzy
        if (!rarest_word) return this.generate_response(this.rejection,{},0.0,"rejected");

        const [clean]=this.nlp.strip_and_sentiment(stripped,this.vocabulary,this.sentiment,FlintNPC.POSITIVE_CATEGORIES);
        const query_tokens=String(clean).toLowerCase().split(/\s+/).filter(Boolean);   // RAW tokens

        let [b,score]=this._fuzzy_best(query_tokens,this._precomputed_context_intents,this._ctx_word_idx,this._ctx_tag_idx,this.threshold,null);
        if (score>=this.threshold) { this.update_context(b); return this.generate_response(b,{},score,"probabilistic match"); }
        [b,score]=this._fuzzy_best(query_tokens,this._precomputed_intents,this._word_idx,this._tag_idx,this.threshold,rarest_word);
        if (score>=this.threshold && b) { this.update_context(b); return this.generate_response(b,{},score,"probabilistic match"); }
        const min_rel = 0.25, q = query_tokens.length;
        const max_scored = parseInt(this.config.max_suggestions_scored ?? 200, 10);
        const pool = [];
        for (const sig of this._candidates(this._precomputed_intents, this._word_idx, this._tag_idx, rarest_word)) {
            const t = sig.token_count || 0;
            if (!q || !t) continue;
            const bound = sig.max_weight_sums[Math.min(q, t) - 1] / sig.max_score;
            if (bound < min_rel) continue;
            pool.push([bound, sig]);
        }
        pool.sort((a, b) => b[0] - a[0]);
        const top = [];
        for (let i = 0; i < Math.min(pool.length, max_scored); i++) {
            const sig = pool[i][1];
            const sc = this.nlp.fast_score_calculation(query_tokens, sig, min_rel);
            if (sc >= min_rel) top.push([sc, sig.token_count, sig.block]);
        }
        top.sort((a, b) => b[0] !== a[0] ? b[0] - a[0] : a[1] - b[1]);
        const related=[],seen=new Set();
        const max_sug=parseInt(this.config.suggestions ?? 5,10);
        for (const [sc,t,blk] of top) {
            const inputs=blk.input||[];
            const sig_key=(inputs.length && Array.isArray(inputs))?String(inputs[0]).toLowerCase():String(blk);
            if (!seen.has(sig_key)) { related.push(blk); seen.add(sig_key); }
            if (related.length>=max_sug) break;
        }
        return this.generate_response(this.rejection,{},0.0,"rejected",related);
    }

    process_messages(user_prompt) {
        const parts=String(user_prompt).split(/(<\|\|.*?\|\|>|"[^"\\]*(?:\\.[^"\\]*)*"|'.*?')/g);
        const segments=[]; let buf="";
        for (let i=0;i<parts.length;i++) {
            if (i%2===1) buf+=parts[i];
            else {
                const pieces=parts[i].split(/\n+|\d+\)|[;!?]/g);
                for (let j=0;j<pieces.length;j++) {
                    if (j===0) buf+=pieces[j];
                    else { segments.push(buf); buf=pieces[j]; }
                }
            }
        }
        segments.push(buf);
        const sub_prompts=segments.map(s=>s.trim()).filter(Boolean);
        if (!sub_prompts.length) return this.generate_response(this.rejection,{},0.0,"rejected");

        const responses=[],tools=[],descs=[],statuses=[],perms=[];
        const merged_slots={};
        let lowest=1.0,lastRes={};
        const agg={}; for (const k of FlintNPC.SENTIMENT_KEYS) agg[k]=0;
        for (const sp of sub_prompts) {
            const res=this.process_message(sp);
            const conf=res.confidence ?? 0.0;
            if (conf<this.threshold || res.status==="rejected") {
                if (this.log_level==="WARNING"||this.log_level==="INFO") console.warn(`[FlintNPC.js][${this.name}][process_messages] Rejected '${sp}', confidence ${conf.toFixed(4)}`);
                return this.generate_response(this.rejection,{},0.0,"rejected",res.related||[]);
            }
            lowest=Math.min(lowest,conf);
            Object.assign(merged_slots,res.slots||{});
            if ("response" in res) responses.push(res.response);
            if ("tools" in res && Array.isArray(res.tools)) tools.push(res.tools);
            if ("description" in res) descs.push(res.description);
            if ("status" in res) statuses.push(res.status);
            if ("permission" in res) perms.push(res.permission);
            lastRes=res;
            for (const k of Object.keys(agg)) agg[k]+=(this.sentiment[k]||0);
        }
        const status=(statuses.length && statuses.every(s=>s===statuses[0]))?statuses[0]:statuses.join(", ");
        let permission="";
        for (const p of perms) {
            const pl=String(p).toLowerCase().trim();
            if (pl==="ask") permission="ask";
            else if ((pl==="yolo"||pl==="auto") && permission!=="ask") permission=pl;
        }
        permission=permission||"ask";
        const out=Object.assign({},lastRes);
        out.description=descs.join(" "); out.tools=tools; out.response=responses.join(" ");
        out.confidence=lowest; out.status=status; out.permission=permission;
        out.sentiment=agg; out.slots=merged_slots;
        if (this.log_level==="INFO") console.log(`[FlintNPC.js][${this.name}][process_messages] Output: '${out.response}'`);
        return out;
    }

    generate_response(block, slots, confidence, status, related = []) {
        if (!block) return { "status":status,"confidence":confidence,"response":"Intent not understood.","slots":slots,"sentiment":this.sentiment };
        const _choice=(item)=>Array.isArray(item)?(item.length===0?"":item[Math.floor(Math.random()*item.length)]):item;
        const render_tags=(text)=>{
            if (!text) return "";
            text=String(text);
            const current_tags=text.match(/<\|\|(.*?)\|\|>/g);
            if (!current_tags) return text;
            const previous_text=text;
            for (const rawTag of current_tags) {
                const tag=rawTag.replace(/<\|\||\|\|>/g,"");
                for (const type of ["completion","unknown","related"]) {
                    if (tag===type && !(type in slots) && this.metadata[type]) slots[type]=_choice(this.metadata[type]);
                }
                if (tag in slots) text=text.split(rawTag).join(String(slots[tag]));
                else if (tag in this.metadata) { const val=this.metadata[tag]; text=text.split(rawTag).join(String(Array.isArray(val)?_choice(val):val)); }
                else text=text.split(rawTag).join("");
            }
            if (text===previous_text) return text;
            return text.match(/<\|\|(.*?)\|\|>/)?render_tags(text):text;
        };
        const render_all_tags=(data)=>{
            if (data && typeof data==='object' && !Array.isArray(data)) { const o={}; for (const [k,v] of Object.entries(data)) o[k]=render_all_tags(v); return o; }
            else if (Array.isArray(data)) return data.map(render_all_tags);
            else if (typeof data==='string') return render_tags(data);
            return data;
        };
        let raw_output=_choice(block.output!==undefined?block.output:"");
        if (related && related.length>0 && status==="rejected") raw_output="<||related||>";
        const final_output=render_tags(raw_output);
        let thinking=_choice(block.thinking);
        if (thinking) thinking=render_tags(thinking);
        const payload={
            "npc":this.config.name||"NPC","confidence":confidence,"response":final_output,
            "related":related,"permission":block.permission||"ask",
            "sentiment":Object.assign({},this.sentiment),"emoji":this.nlp.sentiment_emoji(this.sentiment),
            "slots":slots,"status":status,"thinking":thinking||undefined
        };
        if ("description" in block) payload.description=render_tags(block.description);
        if ("tools" in block && Array.isArray(block.tools)) {
            const tools_copy=JSON.parse(JSON.stringify(block.tools));
            payload.tools=render_all_tags(tools_copy);
            const commands_config=this.config.commands||{};
            for (const tool of payload.tools) {
                if (tool && typeof tool==='object' && "arguments" in tool) {
                    const args=tool.arguments;
                    if ("command" in args && "language" in args) {
                        const lang=String(args.language).toLowerCase();
                        if (lang in commands_config) { const w=commands_config[lang]; args.command=`${w.head||""}${args.command}${w.tail||""}`; }
                    }
                }
            }
        }
        if (this.log_level==="INFO") console.log(`[FlintNPC.js][${this.name}][generate_response] Payload: ${JSON.stringify(payload)}`);
        return payload;
    }

    async addRemoteDataset(datasetInfo) {
        if (this.log_level==="INFO") console.log(`[FlintNPC.js][${this.name}] Fetching remote dataset: ${datasetInfo.id} from ${datasetInfo.url}`);
        if (this.loaded_datasets.has(datasetInfo.id)) return { success:false, message:"Dataset already loaded" };
        try {
            const response=await fetch(datasetInfo.url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status} ${response.statusText}`);
            const contentType=response.headers.get("content-type")||"";
            const text=await response.text();
            if (text.trim().startsWith("<")) throw new Error("Received HTML instead of JSON/JSONL. The URL may be incorrect, private, or rate-limited.");
            let newEntries=[];
            if (contentType.includes("application/json")||text.trim().startsWith("[")) {
                try { const parsed=JSON.parse(text); newEntries=Array.isArray(parsed)?parsed:(parsed&&typeof parsed==='object'?[parsed]:[]); }
                catch(e){ console.warn(`[FlintNPC] Standard JSON parse failed, falling back to JSONL. Error:`,e.message); }
            }
            if (newEntries.length===0) {
                const lines=text.split('\n');
                for (let i=0;i<lines.length;i++) {
                    const line=lines[i].trim();
                    if (line.length>0) { try { const entry=JSON.parse(line); if (entry&&typeof entry==='object') newEntries.push(entry); }
                        catch(err){ if (newEntries.length===0&&i<5) console.warn(`[FlintNPC] Failed to parse JSONL line ${i+1}:`,line.substring(0,100)); } }
                }
            }
            if (newEntries.length===0) throw new Error("Parsed dataset is empty. The file may be empty, completely malformed, or an HTML error page.");
            this.loaded_datasets.set(datasetInfo.id,newEntries);
            this.config.active_datasets=this.config.active_datasets||[];
            if (!this.config.active_datasets.includes(datasetInfo.id)) this.config.active_datasets.push(datasetInfo.id);
            this._rebuild_engine();
            return { success:true, message:`Successfully loaded ${newEntries.length} entries from ${datasetInfo.id}`, count:newEntries.length };
        } catch(error) { console.error(`[FlintNPC.js][${this.name}] ❌ Failed to load dataset:`,error); return { success:false, message:error.message }; }
    }
    removeRemoteDataset(datasetId) {
        if (this.loaded_datasets.has(datasetId)) {
            this.loaded_datasets.delete(datasetId);
            if (this.config.active_datasets) this.config.active_datasets=this.config.active_datasets.filter(id=>id!==datasetId);
            this._rebuild_engine();
            return { success:true, message:`Removed ${datasetId}` };
        }
        return { success:false, message:"Dataset not found" };
    }
    _build_nlp() {
        const intents=[...this.dataset,...this.personality].filter(b=>b&&typeof b==='object'&&("input" in b));
        this.nlp=new FlintParser(this.name,this.vocabulary,this.templates,this.templates_vocabulary,this.variable_types,this.log_level,intents);
        this._build_intent_signatures();
    }
    _rebuild_engine() {
        let combined=[...this._base_dataset];
        for (const entries of this.loaded_datasets.values()) combined=combined.concat(entries);
        this.dataset=combined;
        this.load_data();
        this._build_nlp();
        if (this.log_level==="INFO") console.log(`[FlintNPC.js][${this.name}] Engine rebuilt with ${this.dataset.length} total dataset entries.`);
    }
}
