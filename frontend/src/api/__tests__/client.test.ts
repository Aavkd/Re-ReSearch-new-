import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { apiClient } from "../client";

const BASE = "http://localhost:8000";

// Override the instance base URL so axios points at the test mock server
apiClient.defaults.baseURL = BASE;

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("apiClient interceptor", () => {
  it("normalises 404 detail from FastAPI error response", async () => {
    server.use(
      http.get(`${BASE}/test-404`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 })
      )
    );

    await expect(apiClient.get("/test-404")).rejects.toThrow("Not found");
  });

  it("normalises network error to Error with message", async () => {
    server.use(
      http.get(`${BASE}/test-network`, () => HttpResponse.error())
    );

    await expect(apiClient.get("/test-network")).rejects.toThrow(Error);
  });

  it("passes through successful responses unchanged", async () => {
    server.use(
      http.get(`${BASE}/test-ok`, () =>
        HttpResponse.json({ ok: true }, { status: 200 })
      )
    );

    const res = await apiClient.get<{ ok: boolean }>("/test-ok");
    expect(res.data.ok).toBe(true);
  });
});
