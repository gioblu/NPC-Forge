
/**
 * FlintParser - NLU engine (aligned to final Python FlintParser.py)
 * Giovanni Blu Mitolo 2026 — NDF 0.0
 */
class FlintParser {
    constructor(name, vocabulary, templates, templates_vocabulary, variable_types, log_level="INFO", intents=null) {
        this.log_level=log_level;
        // JS-only convenience defaults (kept); Python relies on types.json being present.
        this.variable_types={ "<||string||>":".*", "<||number||>":"[0-9]+", ...(variable_types||{}) };
        this.vocabulary=vocabulary;
        this.templates=templates;
        this.templates_vocabulary=templates_vocabulary||{};
        this.log_info=`[${name}][nlp.js]`;
        this._tokenize_cache=new Map();
        this._regex_cache=new Map();
        this._cand_cache=new Map();
        this._word_sim_cache=new Map();
        this.weights=this.calculate_auto_weights(intents||[]);
        this._compiled_paths=this._compile_templates(templates);
        this._synonym_map=new Map();
        if (this.templates_vocabulary) {
            for (const [tag,synonyms] of Object.entries(this.templates_vocabulary)) {
                const nt=String(tag).toLowerCase().trim();
                this._synonym_map.set(nt,nt);
                for (const syn of synonyms) this._synonym_map.set(String(syn).toLowerCase().trim(),nt);
            }
        }
    }

    _tokenize(text) {
        if (typeof text!=='string') text=String(text??"");
        if (this._tokenize_cache.has(text)) return this._tokenize_cache.get(text);
        const tokens=text.toLowerCase().trim().split(/\s+/).filter(Boolean);
        if (this._tokenize_cache.size>10000) this._tokenize_cache.clear();
        this._tokenize_cache.set(text,tokens);
        return tokens;
    }

    // batch eviction instead of clear() — stops cache thrashing
    _word_sim(a, b, th) {
        const key = a + "\u0000" + b + "\u0000" + th;
        const c = this._word_sim_cache;
        const hit = c.get(key);
        if (hit !== undefined) return hit;
        const v = this.levenshtein_similarity(a, b, th);
        if (c.size >= 100000) { let n = 10000; for (const k of c.keys()) { c.delete(k); if (--n <= 0) break; } }
        c.set(key, v);
        return v;
    }

    _get_word_pattern(words_list) {
        const key=words_list.join("\u0000");
        if (this._regex_cache.has(key)) return this._regex_cache.get(key);
        const uniq=[...new Set(words_list)].filter(w=>w).sort((a,b)=>b.length-a.length);
        let pattern=null;
        if (uniq.length) {
            const parts=uniq.map(w=>{
                const esc=w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
                const pre=/[A-Za-z0-9_]/.test(w[0])?"\\b":"";
                const post=/[A-Za-z0-9_]/.test(w[w.length-1])?"\\b":"";
                return pre+esc+post;
            });
            pattern=new RegExp("\\s*(?:"+parts.join("|")+")\\s*","gi");
        }
        if (this._regex_cache.size>1000) this._regex_cache.clear();
        this._regex_cache.set(key,pattern);
        return pattern;
    }
    _compile_templates(templates) {
        const compiled=[];
        if (!templates) return compiled;
        for (const b of templates) {
            if (!b||!b.structure) continue;
            for (const path of b.structure) {
                const required_count=path.reduce((c,n)=>c+(n.required!==false?1:0),0);
                compiled.push({template:b,path,required_count,total_length:path.length});
            }
        }
        compiled.sort((a,b)=> b.total_length!==a.total_length ? b.total_length-a.total_length : b.required_count-a.required_count);
        return compiled;
    }
    tag_matches(value,tag){ return Array.isArray(tag)?tag.includes(value):value===tag; }

    calculate_auto_weights(intents) {
        if (!intents.length) return {};
        const wordIntentCounts={};
        for (const entry of intents) {
            const uniq=new Set();
            const inputs=entry.input||[];
            const arr=Array.isArray(inputs)?inputs:[inputs];
            for (const sentence of arr) {
                if (typeof sentence!=='string') continue;
                for (const w of this._tokenize(sentence)) uniq.add(w);
            }
            for (const w of uniq) wordIntentCounts[w]=(wordIntentCounts[w]||0)+1;
        }
        const counts=Object.values(wordIntentCounts);
        const maxCount=counts.length?counts.reduce((m,c)=>c>m?c:m,1):1;
        const weights={};
        for (const [w,c] of Object.entries(wordIntentCounts)) weights[w]=Math.max(0.05,1.0-(c/maxCount));
        return weights;
    }
    get_rarest_word(prompt) {
        if (!prompt || !this.weights || Object.keys(this.weights).length===0) return null;
        const tokens=this._tokenize(prompt);
        if (!tokens.length) return null;
        let rarest=tokens[0], maxWeight=this.weights[rarest]!==undefined?this.weights[rarest]:0.0;
        for (let i=1;i<tokens.length;i++) {
            const w=this.weights[tokens[i]]!==undefined?this.weights[tokens[i]]:0.0;
            if (w>maxWeight) { maxWeight=w; rarest=tokens[i]; }
        }
        return maxWeight>0.0?rarest:null;
    }

    strip_and_count(text, words_list) {
        if (!words_list||!words_list.length) return [String(text).trim(),0];
        const pattern=this._get_word_pattern(words_list);
        if (!pattern) return [String(text).trim(),0];
        const tokens=String(text).split(/(<\|\|.*?\|\|>|".*?"|'.*?')/g);
        let total=0;
        for (let idx=0;idx<tokens.length;idx++) {
            let t=tokens[idx];
            if (!t) { tokens[idx]=""; continue; }
            if ((t.startsWith("<||")&&t.endsWith("||>"))||(t.startsWith('"')&&t.endsWith('"'))||(t.startsWith("'")&&t.endsWith("'"))) continue;
            while (true) {
                const m=t.match(pattern);
                if (!m) break;
                total+=m.length;
                t=t.replace(pattern," ");
            }
            tokens[idx]=t;
        }
        return [tokens.join("").trim().replace(/\s+/g,' '),total];
    }
    strip_and_sentiment(user_prompt, sentiment_json, current_sentiment, target_categories=null) {
        const category_mapping={ "expletives":"expletives","interjections":"interjection","thanking_words":"thanking_words","encouraging_words":"encouraging_words","discouraging_words":"discouraging_words" };
        if (target_categories===null) target_categories=Object.keys(category_mapping);
        let current_prompt=user_prompt;
        for (const [key,json_key] of Object.entries(category_mapping)) {
            if (target_categories.includes(key)) {
                const word_list=sentiment_json[json_key]||[];
                const [cleaned,count]=this.strip_and_count(current_prompt,word_list);
                current_prompt=cleaned; current_sentiment[key]=count;
            }
        }
        const punct=/^[!"#$%&'()*+,\-./:;<=>?@[\]^_`{|}~]/;
        while (current_prompt && punct.test(current_prompt)) current_prompt=current_prompt.substring(1);
        return [current_prompt.replace(/\s+([,.!?;])/g,'$1'),current_sentiment];
    }
    sentiment_emoji(sentiment) {
        if (!sentiment||typeof sentiment!=='object') return "😑";
        const enc=sentiment.encouraging_words||0,thx=sentiment.thanking_words||0,dis=sentiment.discouraging_words||0,exp=sentiment.expletives||0,inj=sentiment.interjections||0,total_pos=enc+thx;
        if (!dis&&!thx){ if(exp===1)return"😒"; if(exp===2)return"😔"; if(exp===3)return"😞"; if(exp===4)return"😨"; if(exp>=5)return"😱"; }
        if (!thx){ if(dis===1)return"😠"; if(dis===2)return"😤"; if(dis===3)return"😪"; if(dis===4)return"😭"; if(dis>=5)return"😵"; }
        if (exp>0&&dis>0)return"😡"; if(exp>0&&total_pos>0)return"🤨";
        if (thx===1||enc===1)return"😁"; if(thx===2||enc===2)return"😃"; if(thx===3||enc===3)return"😆"; if(thx===4||enc===4)return"😜"; if(thx>=5||enc>=5)return"😘";
        if (inj===1)return"😏"; if(inj===2)return"😒"; if(inj===3)return"🧐"; if(inj===4)return"😲"; if(inj>=5)return"😵";
        return "😑";
    }

    levenshtein_similarity(s1, s2, threshold=0.0) {
        s1=String(s1).toLowerCase().trim(); s2=String(s2).toLowerCase().trim();
        if (s1.length<s2.length){ const tmp=s1; s1=s2; s2=tmp; }
        const len1=s1.length,len2=s2.length,max_len=len1;
        if (max_len===0) return 1.0;
        if (s1===s2) return 1.0;
        if (1.0-(len1-len2)/max_len<threshold) return 0.0;
        const max_dist=Math.floor((1.0-threshold)*max_len+1e-9);
        let p=0; while(p<len2&&s1[p]===s2[p])p++;
        s1=s1.slice(p); s2=s2.slice(p);
        let q=0; while(q<s2.length&&s1[s1.length-1-q]===s2[s2.length-1-q])q++;
        if(q){ s1=s1.slice(0,s1.length-q); s2=s2.slice(0,s2.length-q); }
        const n1=s1.length,n2=s2.length;
        if(n2===0) return n1<=max_len? (n1<=max_dist?1.0-n1/max_len:0.0) : 0.0;
        const row=new Array(n2+1); for(let k=0;k<=n2;k++)row[k]=k;
        for(let i=1;i<=n1;i++){
            let prev=i; const c1=s1[i-1]; let mr=i;
            for(let j=1;j<=n2;j++){
                const cur=Math.min(row[j]+1,prev+1,row[j-1]+(c1!==s2[j-1]?1:0));
                row[j-1]=prev; prev=cur; if(cur<mr)mr=cur;
            }
            row[n2]=prev;
            if(mr>max_dist)return 0.0;
        }
        return 1.0-(row[n2]/max_len);
    }

    precompute_intent_signature(target_input, block, synonym_weight=0.0) {
        const tokens=this._tokenize(target_input).slice();
        const weights_list=[]; let max_score=0.0; let tags=null;
        for (const t of tokens) {
            const w=this.weights[t]!==undefined?this.weights[t]:1.0;
            weights_list.push(w); max_score+=w;
            const tag=this._synonym_map.get(t);
            if (tag){ if(tags===null)tags=new Set(); tags.add(tag); }
        }
        weights_list.sort((a,b)=>b-a);
        const bounds=new Float64Array(tokens.length); let s=0.0;
        for (let i=0;i<weights_list.length;i++){ s+=weights_list[i]; bounds[i]=s; }
        return { block, tokens, tag_set: tags?Array.from(tags):[], max_score, synonym_weight, token_count:tokens.length, max_weight_sums:bounds };
    }

        _score_and_matched(query_tokens, data, threshold) {
        let total_score = 0.0;
        const matched = new Array(query_tokens.length).fill(false);
        let eff_max = data.max_score;
        const syn_w = data.synonym_weight !== undefined ? data.synonym_weight : 0.0;
        const smap = this._synonym_map, weights = this.weights;
        const q_info = query_tokens.map(t => [t, smap.get(t), t.length]);
        for (const t_anchor of data.tokens) {
            const a_w = weights[t_anchor] !== undefined ? weights[t_anchor] : 1.0;
            const a_len = t_anchor.length;
            let best_sim = 0.0, best_idx = -1;
            const max_diff = Math.floor(Math.max(a_len, 10) * (1.0 - threshold)) + 2;
            const a_tag = smap.get(t_anchor);
            for (let idx = 0; idx < q_info.length; idx++) {
                if (matched[idx]) continue;
                const [t_q, q_tag, q_len] = q_info[idx];
                if (t_anchor === t_q) { best_sim = 1.0; best_idx = idx; break; }
                if (a_tag && q_tag && a_tag === q_tag) { best_sim = syn_w; best_idx = idx; break; }
                if (Math.abs(a_len - q_len) > max_diff) continue;
                const sim = this._word_sim(t_anchor, t_q, threshold);
                if (sim > best_sim) { best_sim = sim; best_idx = idx; }
            }
            if (best_sim >= threshold) { total_score += best_sim * a_w; if (best_idx !== -1) matched[best_idx] = true; }
        }
        for (let idx = 0; idx < q_info.length; idx++) {
            const [t_q, q_tag] = q_info[idx];
            if (!matched[idx] && !(t_q in weights) && q_tag === undefined) eff_max += 0.5;
        }
        const score = eff_max ? total_score / eff_max : 0.0;
        return [score, matched.reduce((n, m) => n + (m ? 1 : 0), 0)];
    }

    fast_score_calculation(query_tokens, data, threshold) {
        return this._score_and_matched(query_tokens, data, threshold)[0];
    }

    find_candidates(structure, candidates) {
        const key=JSON.stringify(structure);
        let cached=this._cand_cache.get(key);
        if (cached===undefined) {
            cached=[];
            const u_len=structure.length;
            for (const template of this.templates) {
                if (!template||!template.structure) continue;
                for (const path of template.structure) {
                    let p=0,u=0;
                    while (p<path.length&&u<u_len) {
                        if (this.tag_matches(structure[u],path[p].tag)){u++;p++;}
                        else if (path[p].required===false){p++;}
                        else break;
                    }
                    if (u!==u_len||p>=path.length) continue;
                    const node=path[p]; const nodes=[node];
                    if (node.required===false&&p+1<path.length) nodes.push(path[p+1]);
                    for (const n of nodes) {
                        const k=[n.type,n.tag];
                        if (!cached.some(([ct,cg])=>ct===k[0]&&JSON.stringify(cg)===JSON.stringify(k[1]))) cached.push(k);
                    }
                }
            }
            if (this._cand_cache.size>5000) this._cand_cache.clear();
            this._cand_cache.set(key,cached);
        }
        candidates.push(...cached);
    }
    find_template(token, threshold) {
        const low=token.toLowerCase();
        const exact=this._synonym_map.get(low);
        if (exact) return exact;
        let match=null,similarity=0.0;
        if (low.length>4) {
            for (const [syn,tag] of this._synonym_map) {
                if (syn.length>=4) {
                    const sim=this._word_sim(low,syn,threshold);
                    if (sim>=threshold&&sim>similarity){ similarity=sim; match=tag; if(sim===1.0)break; }
                }
            }
        }
        if (match&&similarity<1.0&&this.log_level==="INFO") console.log(`${this.log_info}[find_template] Typo: '${token}' matched to '${match}' (Confidence: ${similarity.toFixed(2)})`);
        return match;
    }

    parse_structure(sub_prompt, threshold) {
        const token_pattern=/"[^"\\]*(?:\\.[^"\\]*)*"|\S+/g;
        const raw_words=(String(sub_prompt).match(token_pattern)||[]).map(w=>w.trim()).filter(Boolean);
        const stop_words=this.vocabulary?.stop_words||[];
        const expletives=this.expletives_list||[];
        const interjections=this.interjection_list||[];
        const working_tokens=raw_words.filter(w=>!stop_words.includes(w)&&!expletives.includes(w)&&!interjections.includes(w));
        const structure=[],slots={};
        let i=0;
        while (i<working_tokens.length) {
            let token=working_tokens[i];
            const candidates=[]; this.find_candidates(structure,candidates);
            const expects_variable=candidates.some(([type,tag])=>typeof tag==='string'&&tag in this.variable_types);
            const remainder=working_tokens.slice(i).join(" ");
            let match=null;
            if (!token.includes(" ")) {
                if (candidates.some(([type])=>type==="vocab")) {
                    const pm=this.find_template(token,threshold);
                    if (pm) {
                        const etv=candidates.some(([type,tag])=>type==="vocab"&&this.tag_matches(pm,tag));
                        if (structure.length>0&&expects_variable&&!etv) match=null; else match=pm;
                    }
                }
            }
            if (match){ structure.push(match); i++; continue; }
            let matched_variable=false;
            for (const [type,tag] of candidates) {
                if (type==="vocab") continue;
                const rgxp=`<||${type}||>`;
                if (rgxp in this.variable_types) {
                    const regex_pattern=new RegExp(this.variable_types[rgxp],'i');
                    const slot_name=String(tag).replace(/<\|\||\|\|>/g,"");
                    if (type==="string"&&!token.startsWith('"')) {
                        if (regex_pattern.test(remainder)) {
                            structure.push(tag);
                            slots[slot_name]=remainder.replace(/'/g,"'\\''");
                            i=working_tokens.length; matched_variable=true; break;
                        }
                    }
                    if (regex_pattern.test(token)) {
                        structure.push(tag);
                        slots[slot_name]=token.replace(/^"+|"+$/g,'').replace(/'/g,"'\\''");
                        i++; matched_variable=true; break;
                    }
                }
            }
            if (matched_variable) continue;
            i++;
        }
        if (this.log_level==="INFO") console.log(`${this.log_info}[abstract_input] Slots: ${JSON.stringify(slots)}.`);
        return [structure,slots];
    }
    match_structure(templates, structure) {
        const struct_len=structure.length;
        const compiledPaths=(templates===this.templates&&this._compiled_paths)?this._compiled_paths:this._compile_templates(templates);
        for (const item of compiledPaths) {
            if (item.required_count>struct_len) continue;
            let prompt_i=0,template_i=0,template_match=true;
            while (template_i<item.path.length) {
                const node=item.path[template_i];
                const is_required=node.required!==false;
                if (prompt_i<struct_len&&this.tag_matches(structure[prompt_i],node.tag)){prompt_i++;template_i++;continue;}
                if (!is_required){template_i++;} else {template_match=false;break;}
            }
            if (template_match&&prompt_i===struct_len) return item.template;
        }
        return null;
    }
}