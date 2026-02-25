import { apiClient } from "./client";
import type { AppNode, IngestResponse, SearchMode } from "../types";

/** Scrape a URL and ingest it into the knowledge base. */
export async function ingestUrl(url: string): Promise<IngestResponse> {
  const res = await apiClient.post<IngestResponse>("/ingest/url", { url });
  return res.data;
}

/** Upload a PDF file and ingest it into the knowledge base. */
export async function ingestPdf(file: File): Promise<IngestResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post<IngestResponse>("/ingest/pdf", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

/** Search the knowledge base. Defaults to fuzzy mode with top_k=10. */
export async function search(
  query: string,
  mode: SearchMode = "fuzzy",
  topK = 10
): Promise<AppNode[]> {
  const res = await apiClient.get<AppNode[]>("/search", {
    params: { q: query, mode, top_k: topK },
  });
  return res.data;
}
