/**
 * Captain — NPC Tools Manager
 *
 * Manages and executes tool functions available to NPC agents.
 * Tools are custom methods that extend NPC capabilities beyond
 * standard chat responses (e.g., translations, text analysis).
 *
 * Tools are registered with their exact function names to match
 * dataset tool definitions. Supports async/sync execution with
 * parameter validation, error handling, and media injection.
 *
 * @author Giovanni Blu Mitolo
 * @version 2026
 * @license See LICENSE for licensing details
 *
 * @example
 * const captain = new Captain();
 * captain.setVideoRepository({tutorial: ['dQw4w9WgXcQ']});
 * const result = await captain.tools.TextTranslation({
 *   word: 'hello', lang1: 'english', lang2: 'spanish'
 * });
 */
class Captain {
    /**
     * Initialize Captain tools manager and register built-in tools.
     * Wraps method context to preserve 'this' when called from registry.
     */
    constructor() {
        this.videoRepository = {};
        // Wrap InjectImage and InjectYoutubeEmbed to preserve 'this' context
        this.tools.InjectImage = async (args) => {
            const keyword = (args[0] && args[0].keyword) || 'nature';
            const alt = args[0] && args[0].alt;
            return this.injectImage(keyword, alt);
        };
        this.tools.InjectYoutubeEmbed = async (args) => {
            const keyword = (args[0] && args[0].keyword) || '';
            const t = (args[0] && args[0].t) || '';
            return this.injectYoutubeEmbed(keyword, t);
        };
    }

    /**
     * Tool registry — each tool is an async-compatible function.
     * Tools receive parameters as a single object argument.
     */
    tools = {
        /**
         * CountLettersInWord — Count occurrences of a letter in a word.
         * @param {Object} params - { word, letter }
         * @returns {Object} { type: "text", content: count }
         */
        CountLettersInWord:
            function CountLettersInWord(args) {
                const count = args[0].word.split(args[0].letter).length - 1;
                return {
                    type: "text",
                    content: String(count)
                };
            },

        /**
         * TextTranslation — Translate text between languages.
         * Leverages MyMemory API for real-time translations.
         *
         * @param {Object} params - { word, lang1, lang2 }
         * @returns {Promise<Object>} { type: "text", content: translation }
         */
        TextTranslation:
            async function TextTranslation(args) {
                const params = args[0];

                // Language code mapping (MyMemory API expects ISO 639-1 codes)
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
                    const response = await fetch(url, {
                        headers: { 'User-Agent': 'Mozilla/5.0' }
                    });
                    const data = await response.json();
                    const translation = data.responseData.translatedText;

                    return {
                        type: "text",
                        content: `🌐 Translating from ${params.lang1} to ${params.lang2}...\n\nThe translation is ${translation}`
                    };
                } catch (error) {
                    return {
                        type: "text",
                        content: `⛔ Error executing translation: ${error.message}`
                    };
                }
            }
    };

    /**
     * InjectImage — Fetch an image from Wikipedia by keyword
     * Searches Wikipedia for the keyword and retrieves the page image
     * Handles multi-word queries and case-insensitive search with fuzzy matching
     * Uses captain-img CSS class for styling with attribution
     *
     * @param {String} keyword - The search keyword (supports multi-word queries)
     * @param {String} [alt] - Optional alt/caption text override (falls back to the Wikipedia page title)
     * @returns {Promise<Object>} { type: "html", content: HTML with image and attribution }
     */
    injectImage = (keyword, alt) => {
        const searchKeyword = keyword || 'nature';
        console.log("[InjectImage] Fetching image for keyword:", searchKeyword);

        // First, search for the article to find the correct title (handles case-insensitivity and multi-word queries)
        const encodedKeyword = encodeURIComponent(searchKeyword);
        const searchUrl = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodedKeyword}&format=json&origin=*`;

        console.log("[InjectImage] Search URL:", searchUrl);

        return fetch(searchUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        })
            .then(response => {
                console.log("[Wikipedia Search] Response status:", response.status);
                if (!response.ok) {
                    throw new Error(`Wikipedia API error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("[Wikipedia Search] Data received:", data);
                const searchResults = data.query?.search || [];

                if (searchResults.length === 0) {
                    return {
                        type: "text",
                        content: `⛔ No Wikipedia article found for "${searchKeyword}"`
                    };
                }

                // Get the title of the first (most relevant) search result
                const correctTitle = searchResults[0].title;
                console.log("[InjectImage] Found article title:", correctTitle);

                // Now fetch the image for this article
                const imageFetchUrl = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(correctTitle)}&prop=pageimages&piprop=original&format=json&origin=*`;

                return fetch(imageFetchUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                })
                    .then(response => {
                        console.log("[Wikipedia Image API] Response status:", response.status);
                        if (!response.ok) {
                            throw new Error(`Wikipedia API error: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(imageData => {
                        console.log("[Wikipedia Image API] Data received:", imageData);
                        const pages = imageData.query?.pages || {};
                        const page = Object.values(pages)[0];
                        const imageUrl = page?.original?.source;
                        const title = page?.title || correctTitle;
                        const altText = alt || title;

                        console.log("[InjectImage] Title:", title, "| Image URL:", imageUrl);

                        if (!imageUrl) {
                            return {
                                type: "text",
                                content: `⚠️ Article found "${title}" but no image available`
                            };
                        }

                        const wikiLink = `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`;
                        const html = `
                            <div class="captain-img-container" style="position: relative; display: inline-block;">
                                <img class="captain-img" src="${imageUrl}" alt="${altText}" style="max-width: 100%; height: auto; display: block;">
                                <div class="captain-img-subtext">
                                    <a href="${wikiLink}" target="_blank">
                                        ${title} source Wikipedia
                                    </a>
                                </div>
                            </div>
                        `;

                        console.log("[InjectImage] HTML generated successfully");
                        return {
                            type: "html",
                            content: html
                        };
                    });
            })
            .catch(error => {
                console.error("[InjectImage] Fetch error:", error.message);
                return {
                    type: "text",
                    content: `⛔ Error fetching image: ${error.message}`
                };
            });
    };

    /**
     * InjectYoutubeEmbed — Inject a YouTube video embed with autoplay
     * Selects a random video from the keyword's video ID array
     * Uses captain-video CSS class for styling
     *
     * @param {String} keyword - The video keyword/category
     * @returns {Object} { type: "html", content: iframe HTML }
     */
    injectYoutubeEmbed = (selectedVideoId, t) => {
        console.log("[InjectYoutubeEmbed] Embedding video id:", selectedVideoId);
        if (t) t = "&start=" + t;
        if (!selectedVideoId) {
            return {
                type: "text",
                content: `⛔ Video not found!`
            };
        }
        let html = `<iframe class="captain-video" src="https://www.youtube.com/embed/${selectedVideoId}?autoplay=1${t}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" style="height: 33vh" allowfullscreen></iframe>`;
        html += `
            <div class="captain-video-subtext">
                <a href="https://www.youtube.com/${selectedVideoId}" target="_blank">
                    source Youtube
                </a>
            </div>
        `;

        return {
            type: "html",
            content: html
        };
    };

    /**
     * Set video repository for keyword-based video embedding.
     * Maps keywords to YouTube video ID arrays for random selection.
     *
     * @param {Object<String, Array<String>>} videoRepo - {keyword: [videoIds]}
     */
    setVideoRepository(videoRepo) {
        this.videoRepository = videoRepo || {};
    }

    /**
     * Merge additional tools into the existing tool registry.
     * Allows runtime registration of custom tool functions.
     *
     * @param {Object<String, Function>} additionalTools - New tools to register
     * @example
     * captain.addTools({
     *   CustomTool: async (args) => ({ type: 'text', content: 'Result' })
     * });
     */
    addTools(additionalTools) {
        this.tools = { ...this.tools, ...additionalTools };
    }
}
