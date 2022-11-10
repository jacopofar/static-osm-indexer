type AddressEntry = {
    name: string;
    lat: number;
    lon: number;
}
export class AddressTextualIndex {
    baseURL: string;
    fetcher: typeof fetch;

    stopWords: Set<string> = new Set();
    minLength: number = 3;
    tokenRegex: RegExp = /[^\p{L}]+/u;


    // the current file token, stored to avoid reloading
    currentFileToken: string | null = null;
    currentFileContent: AddressEntry[] = [];

    constructor(baseURL: string, fetcher = fetch) {
        this.baseURL = baseURL;
        // binding is necessary for fetch to run in the browser...
        this.fetcher = fetcher.bind(window);
        this.init();
    }
    async init() {
        this.fetcher(`${this.baseURL}/index_metadata.json`)
            .then((response) => response.json())
            .then((data) => {
                this.stopWords = new Set(data.stopwords);
                this.minLength = data.token_length;
            })
    }

    private async fileSearch(queryTokens: string[]) {
        let results: AddressEntry[] = [];
        for (let candidate of this.currentFileContent) {
            if (queryTokens.every(qt => {
                return candidate.name.toLowerCase().split(this.tokenRegex).some(
                    candidateToken =>
                        candidateToken.startsWith(qt))
            })) {

                results.push(candidate);
            }
        }
        return results;
    }

    async search(query: string) {
        const queryTokens = query.toLowerCase().split(this.tokenRegex);
        for (let p of queryTokens) {
            if (p.length < this.minLength || this.stopWords.has(p)) {
                continue;
            }
            const fileToken = p.substring(0, this.minLength)
            if (this.currentFileToken === fileToken) {
                return this.fileSearch(queryTokens);
            }
            else {
                const response = await this.fetcher(`${this.baseURL}/${fileToken}.json`);
                let data: AddressEntry[] = [];

                if (response.ok) {
                    data = await response.json();
                }
                else {
                    // assume an empty file means no results
                    data = [];
                }
                this.currentFileToken = fileToken;
                this.currentFileContent = data;
                return this.fileSearch(queryTokens);

            }
        }
        throw new Error('Query string insufficient for the search');
    }
}