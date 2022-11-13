// text_search.ts
var AddressTextualIndex = class {
  constructor(baseURL, fetcher = fetch) {
    this.stopWords = /* @__PURE__ */ new Set();
    this.minLength = 3;
    this.tokenRegex = /[^\p{L}]+/u;
    this.currentFileToken = null;
    this.currentFileContent = [];
    this.baseURL = baseURL;
    this.fetcher = fetcher.bind(window);
    this.initializer = this.init();
  }
  async init() {
    const data = await (await this.fetcher(`${this.baseURL}/index_metadata.json`)).json();
    this.stopWords = new Set(data.stopwords);
    this.minLength = data.token_length;
  }
  async fileSearch(queryTokens) {
    let results = [];
    for (let candidate of this.currentFileContent) {
      if (queryTokens.every((qt) => {
        return candidate.name.toLowerCase().split(this.tokenRegex).some((candidateToken) => candidateToken.startsWith(qt));
      })) {
        results.push(candidate);
      }
    }
    return results;
  }
  async search(query) {
    await this.initializer;
    const queryTokens = query.toLowerCase().split(this.tokenRegex);
    for (let p of queryTokens) {
      if (p.length < this.minLength || this.stopWords.has(p)) {
        continue;
      }
      const fileToken = p.substring(0, this.minLength);
      if (this.currentFileToken === fileToken) {
        return this.fileSearch(queryTokens);
      } else {
        const response = await this.fetcher(
          `${this.baseURL}/${fileToken}.json`
        );
        let data = [];
        if (response.ok) {
          data = await response.json();
        } else {
          data = [];
        }
        this.currentFileToken = fileToken;
        this.currentFileContent = data;
        return this.fileSearch(queryTokens);
      }
    }
    throw new Error("Query string insufficient for the search");
  }
};
export {
  AddressTextualIndex
};
