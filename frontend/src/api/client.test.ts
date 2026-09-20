import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

function mockFetchOnce(response: Partial<Response> & { text?: () => Promise<string> }) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: response.ok ?? true,
      status: response.status ?? 200,
      statusText: response.statusText ?? "OK",
      text: response.text ?? (async () => ""),
      json: response.json ?? (async () => ({})),
    }),
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client error handling", () => {
  it("extracts the FastAPI 'detail' message from a JSON error body", async () => {
    mockFetchOnce({
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ detail: "This category still has transactions assigned to it" }),
    });

    await expect(api.categories.list()).rejects.toThrow(
      "This category still has transactions assigned to it",
    );
  });

  it("falls back to the raw body when the error isn't JSON", async () => {
    mockFetchOnce({ ok: false, status: 500, text: async () => "Internal Server Error" });

    await expect(api.categories.list()).rejects.toThrow("Internal Server Error");
  });

  it("returns undefined for a 204 No Content response", async () => {
    mockFetchOnce({ ok: true, status: 204 });

    await expect(api.categories.remove(1)).resolves.toBeUndefined();
  });

  it("parses the JSON body on success", async () => {
    mockFetchOnce({ ok: true, status: 200, json: async () => [{ id: 1, name: "Groceries" }] });

    await expect(api.categories.list()).resolves.toEqual([{ id: 1, name: "Groceries" }]);
  });
});
