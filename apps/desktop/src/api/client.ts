import axios from "axios";
import { encodeForHeader, loadLLMConfig } from "@/lib/llm/config";

export const API_BASE_URL = "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
});

/**
 * Every outbound request that doesn't already pin an X-LLM-Config header
 * gets one from the keychain. This covers the `/parse`, `POST /sessions`,
 * `POST /report` routes without each call site having to remember to
 * attach the header itself. Routes that don't need the header (health,
 * app-settings) don't break — the backend middleware only validates the
 * header when it's present.
 *
 * The `/llm/test` endpoint in api/llm.ts sets the header explicitly so it
 * can test an *unsaved* config; the `if already set` guard below leaves
 * that untouched.
 */
apiClient.interceptors.request.use(async (config) => {
  const existing = config.headers?.get?.("X-LLM-Config");
  if (existing) return config;

  try {
    const llm = await loadLLMConfig();
    if (llm && llm.api_key) {
      config.headers.set("X-LLM-Config", encodeForHeader(llm));
    }
  } catch {
    /* keychain unavailable in non-Tauri shell; request will proceed without */
  }
  return config;
});
