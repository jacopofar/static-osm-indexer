/**
 * @jest-environment jsdom
 */
import { describe, expect, test } from "@jest/globals";
import { AddressTextualIndex } from "./text_search";

import fetchMock from "jest-fetch-mock";
fetchMock.enableMocks();

describe("textual index", () => {
  beforeEach(() => {
    fetchMock.resetMocks();
  });
  test("when instantiated, fetches the metadata", async () => {
    fetchMock.mockOnce(JSON.stringify({ token_length: 30 }));
    const ati = new AddressTextualIndex("address");
    expect(fetchMock.mock.calls.length).toEqual(1);
    expect(fetchMock.mock.calls[0][0]).toEqual("address/index_metadata.json");
    await ati.initializer;
    expect(ati.minLength).toBe(30);
  });
});
