/**
 * MSW Node server — used by Vitest to intercept HTTP requests in tests.
 *
 * Import this in individual test files that need HTTP mocking, or in a
 * global test-setup file:
 *
 *   import { server } from "../../mocks/server";
 *   beforeAll(() => server.listen());
 *   afterEach(() => server.resetHandlers());
 *   afterAll(() => server.close());
 */
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
