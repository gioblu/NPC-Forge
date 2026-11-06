/**
 * Captain — NPC Tools Manager
 * Giovanni Blu Mitolo 2026
 */
class Captain {
    constructor() {
        this.tools.InjectImage = async (args) => {
            const keyword = (args[0] && args[0].keyword) || 'nature';
            const alt = args[0] && args[0].alt;
            return this.injectImage(keyword, alt);
        };
        
        this.tools.InjectYoutubeEmbed = async (args) => {
            const videoId = (args[0] && args[0].videoId) || '';
            const t = (args[0] && args[0].t) || '';    
            return this.injectYoutubeEmbed(videoId, t);
        };

        this.tools.SearchWikipedia = async (args) => {
            const params = args[0] || {};
            const query = params.query || params.keyword || "";
            
            if (!query) {
                return { type: "text", content: "⛔ Please provide a search query." };
            }

            const encodedQuery = encodeURIComponent(query);
            const url = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodedQuery}&prop=extracts&exintro=true&explaintext=true&format=json&origin=*&redirects=1`;

            try {
                const response = await fetch(url, { 
                    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } 
                });
                
                const data = await response.json();
                const pages = data.query?.pages || {};
                const pageId = Object.keys(pages)[0];
                
                if (pageId === "-1") {
                    return { type: "text", content: `⛔ No Wikipedia article found for "${query}".` };
                }

                const page = pages[pageId];
                const title = page.title;
                const extract = page.extract.split(". ").slice(0, 4).join().replace(/\.$/, '') + ".";
                const wikiLink = `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`;

                if (!extract || extract.trim() === "") {
                    return { type: "text", content: `⚠️ Article "${title}" found, but no content is available.` };
                }

                const html = `
                    <div class="wiki-summary">
                        <div>${extract}</div>
                        <div class="captain-img-subtext">
                            ${title}. Source: <a href="${wikiLink}" target="_blank">Wikipedia</a>
                        </div>
                    </div>
                `;

                return { type: "html", content: html };
            } catch (error) {
                console.error("[SearchWikipedia] Fetch error:", error.message);
                return { type: "text", content: `⛔ Error fetching Wikipedia data: ${error.message}` };
            }
        };

        // Map the dataset's "run_in_terminal" tool to our web-friendly "write_file" logic
        this.tools.run_in_terminal = this.tools.write_file;
    }

    tools = {
        CountLettersInWord: function CountLettersInWord(args) {
            const count = args[0].word.split(args[0].letter).length - 1;
            return { type: "text", content: String(count) };
        },

        TextTranslation: async function TextTranslation(args) {
            const params = args[0];
            const langMap = {
                'english': 'en', 'italian': 'it', 'spanish': 'es',
                'french': 'fr', 'german': 'de', 'portuguese': 'pt',
                'russian': 'ru', 'japanese': 'ja', 'chinese': 'zh-cn'
            };

            const cleanLang1 = params.lang1.toLowerCase().trim();
            const cleanLang2 = params.lang2.toLowerCase().trim();
            const from_code = langMap[cleanLang1] || cleanLang1;
            const to_code = langMap[cleanLang2] || cleanLang2;
            const encodedText = encodeURIComponent(params.word);
            const url = `https://api.mymemory.translated.net/get?q=${encodedText}&langpair=${from_code}|${to_code}`;

            try {
                const response = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
                const data = await response.json();
                const translation = data.responseData.translatedText;
                return {
                    type: "text",
                    content: `🌐 Translating from ${params.lang1} to ${params.lang2}...\n\nThe translation is ${translation}`
                };
            } catch (error) {
                return { type: "text", content: `⛔ Error executing translation: ${error.message}` };
            }
        },

        write_file: async function write_file(args) {
            const params = args[0] || {};
            // Support both 'file_content' and 'command' for maximum dataset compatibility
            const codeContent = params.file_content || params.command || "";
            const filePath = params.file_path || params.path || "";
            const providedLanguage = (params.language || "text").toLowerCase();
            const explanation = params.explanation || "";
            const goal = params.goal || "Generated Script";

            let hlLang = "text";
            let ext = ".txt";
            let filename = `npc_${goal.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`;

            // 1. Try to determine language/extension from file_path first
            if (filePath) {
                // Extract extension from the end of the path (e.g., "script.py" -> "py")
                const pathExtMatch = filePath.match(/\.([a-zA-Z0-9]+)$/);
                if (pathExtMatch) {
                    const pathExt = pathExtMatch[1].toLowerCase();
                    
                    // Map common extensions to standard language names for highlighting
                    const pathLangMap = {
                        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                        'sh': 'bash', 'bash': 'bash', 'zsh': 'bash',
                        'html': 'html', 'htm': 'html', 'css': 'css', 
                        'json': 'json', 'txt': 'text', 'md': 'markdown',
                        'sql': 'sql', 'xml': 'xml', 'yaml': 'yaml', 'yml': 'yaml'
                    };
                    
                    hlLang = pathLangMap[pathExt] || pathExt;
                    ext = `.${pathExt}`;
                    
                    // Extract the actual filename from the path for the download attribute
                    const pathParts = filePath.split(/[\\/]/);
                    filename = pathParts[pathParts.length - 1];
                    
                    // Safety: if the extracted filename somehow lacks an extension, add it
                    if (!filename.includes('.')) {
                        filename += ext;
                    }
                }
            }

            // 2. Fallback to provided language if file_path didn't yield a clear result
            if (hlLang === "text" && providedLanguage !== "text") {
                const langMap = { 
                    'py': 'python', 'python': 'python', 
                    'js': 'javascript', 'javascript': 'javascript', 
                    'bash': 'bash', 'sh': 'bash', 'shell': 'bash' 
                };
                hlLang = langMap[providedLanguage] || providedLanguage;
                
                const extensions = { 
                    'python': '.py', 'javascript': '.js', 'bash': '.sh', 
                    'html': '.html', 'css': '.css', 'json': '.json', 'text': '.txt' 
                };
                ext = extensions[hlLang] || `.${providedLanguage}`;
                filename = `npc_${goal.replace(/[^a-z0-9]/gi, '_').toLowerCase()}${ext}`;
            }

            // Basic HTML escaping for safety
            const safeCode = codeContent
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");

            // Create a blob URL for the download link
            const blob = new Blob([codeContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);

            const html = `
                <div class="npc-tool-output" style="margin-top: 12px; border: 1px solid var(--border-strong); border-radius: var(--radius); overflow: hidden; background: var(--panel);">
                    <div style="place-items: flex-end; padding: 0.6rem 0.8rem; background: var(--button-background); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-strong);">
                        <span style="font-weight: 650; font-size: 0.85rem; color: var(--heading);">
                            💻 ${goal} 
                            <span style="font-weight: 400; color: var(--text-dim); font-size: 0.75rem; display: inline-block">(${hlLang})</span>
                        </span>
                        <a href="${url}" download="${filename}" class="theme-toggle">Download</a>
                    </div>
                    ${explanation ? `<div style="padding: .5em .5em .25em 0; font-size: 0.85rem; color: var(--text-dim); background: var(--npc-background); border-bottom: 1px solid var(--border);"><em>${explanation}</em></div>` : ''}
                    <pre style="margin: 0; padding: 0.8rem; background: var(--field); color: var(--text); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; line-height: 1.6; overflow-x: auto; white-space: pre-wrap;"><code>${safeCode}</code></pre>
                </div>
            `;

            return { type: "html", content: html };
        }
    };

    injectImage = (keyword, alt) => {
        const searchKeyword = keyword || 'nature';
        const encodedKeyword = encodeURIComponent(searchKeyword);
        const searchUrl = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodedKeyword}&format=json&origin=*`;

        return fetch(searchUrl, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } })
            .then(response => {
                if (!response.ok) throw new Error(`Wikipedia API error: ${response.status}`);
                return response.json();
            })
            .then(data => {
                const searchResults = data.query?.search || [];
                if (searchResults.length === 0) {
                    return { type: "text", content: `⛔ No Wikipedia article found for "${searchKeyword}"` };
                }

                const correctTitle = searchResults[0].title;
                const imageFetchUrl = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(correctTitle)}&prop=pageimages&piprop=original&format=json&origin=*`;

                return fetch(imageFetchUrl, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } })
                    .then(response => {
                        if (!response.ok) throw new Error(`Wikipedia API error: ${response.status}`);
                        return response.json();
                    })
                    .then(imageData => {
                        const pages = imageData.query?.pages || {};
                        const page = Object.values(pages)[0];
                        const imageUrl = page?.original?.source;
                        const title = page?.title || correctTitle;
                        const altText = alt || title;

                        if (!imageUrl) {
                            return { type: "text", content: `⚠️ Article found "${title}" but no image available` };
                        }

                        const wikiLink = `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`;
                        return {
                            type: "html",
                            content: `
                                <div class="captain-img-container" style="position: relative; display: inline-block;">
                                    <img onload="scrollChatToBottom()" class="captain-img" src="${imageUrl}" alt="${altText}" style="max-width: 100%; height: auto; display: block;">
                                    <div class="captain-img-subtext">
                                        ${title}. Source: <a href="${wikiLink}" target="_blank">Wikipedia</a>
                                    </div>
                                </div>
                            `
                        };
                    });
            })
            .catch(error => {
                console.error("[InjectImage] Fetch error:", error.message);
                return { type: "text", content: `⛔ Error fetching image: ${error.message}` };
            });
    };

    injectYoutubeEmbed = (selectedVideoId, t) => {
        console.log("[InjectYoutubeEmbed] Embedding video id:", selectedVideoId);
        const timeParam = t ? `&start=${t}` : '';
        
        if (!selectedVideoId) {
            return { type: "text", content: `⛔ Video not found!` };
        }
        
        let html = `<iframe class="captain-video" src="https://www.youtube.com/embed/${selectedVideoId}?autoplay=1${timeParam}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" style="height: 33vh" allowfullscreen></iframe>`;
        html += `
            <div class="captain-video-subtext">
                <a href="https://www.youtube.com/watch?v=${selectedVideoId}" target="_blank">source Youtube</a>
            </div>
        `;

        return { type: "html", content: html };
    };

    addTools(additionalTools) {
        this.tools = { ...this.tools, ...additionalTools };
    }
}