import axios, { AxiosError } from "axios";
import { encodeForHeader, loadLLMConfig } from "@/lib/llm/config";
import { pushToast } from "@/stores/toast-store";

/**
 * Base URL of the local backend. Starts as the dev fallback `:8000`
 * (matches `uv run uvicorn` defaults) and gets rewritten by
 * `initBackendUrl()` at app boot once the Tauri host reports the
 * actual port chosen by the bundled backend subprocess. `let` gives us
 * ES-module live bindings so importers of `API_BASE_URL` see the
 * updated value automatically after init completes.
 */
export let API_BASE_URL = "http://127.0.0.1:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
});

/**
 * Ask the Tauri host for the backend port and rewrite API_BASE_URL +
 * apiClient's defaults. Called from main.tsx before React renders so
 * every subsequent request uses the right URL.
 *
 * Timing wrinkle: the Rust side launches the bundled backend in a
 * worker thread and stores the port only once the child prints
 * `EATIT_BACKEND_READY port=<N>` to stdout. The webview hits this
 * function almost immediately, often before the backend has finished
 * booting. `get_backend_port` returns Err("backend not ready") during
 * that window, which we used to swallow — and the webview then raced
 * to the fallback `:8000`, showed the offline banner, and fired a
 * toast for every subsequent heartbeat.
 *
 * Poll instead: retry every 500 ms up to 30 s (matches the Rust
 * side's BACKEND_READY_TIMEOUT_SECS). In dev without Tauri the first
 * `import("@tauri-apps/api/core")` rejects and we fall through to
 * the `:8000` fallback on the first iteration.
 */
const BACKEND_POLL_INTERVAL_MS = 500;
const BACKEND_POLL_MAX_MS = 30_000;

export async function initBackendUrl(): Promise<void> {
  let invoke: (<T>(cmd: string) => Promise<T>) | null = null;
  try {
    const mod = await import("@tauri-apps/api/core");
    invoke = mod.invoke as typeof invoke;
  } catch {
    // Not running under Tauri (plain vite dev in a browser tab).
    // Keep the :8000 fallback; assume dev uvicorn is up.
    return;
  }
  if (!invoke) return;

  const deadline = Date.now() + BACKEND_POLL_MAX_MS;
  while (Date.now() < deadline) {
    try {
      const port = await invoke<number>("get_backend_port");
      if (typeof port === "number" && port > 0 && port < 65536) {
        API_BASE_URL = `http://127.0.0.1:${port}`;
        apiClient.defaults.baseURL = API_BASE_URL;
        return;
      }
    } catch {
      /* backend still booting — retry */
    }
    await new Promise((resolve) => setTimeout(resolve, BACKEND_POLL_INTERVAL_MS));
  }
  // 30 s elapsed and the backend never announced itself. Keep the
  // :8000 fallback so the offline banner surfaces for a genuine
  // "backend won't start" failure rather than a transient startup.
}

/**
 * Per-request opt-out flag. Call sites that want to render their own
 * error UI pass `{ skipErrorToast: true }` in the request config. The
 * response interceptor below reads this flag off the request config
 * before showing a generic toast.
 */
declare module "axios" {
  export interface AxiosRequestConfig {
    skipErrorToast?: boolean;
  }
}

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

// Intentionally NO response / error interceptor that forwards the axios
// `config` (which carries `X-LLM-Config` on every call) to Sentry or
// logs. Our Sentry `beforeSend` also redacts the header, but belt-and-
// braces: we never hand the raw request metadata to breadcrumb tooling
// in the first place. See src/lib/sentry.ts for the redaction contract.
//
// The response interceptor below ONLY reads the parsed JSON body (safe —
// backend exception_handlers.py already strips secrets) and dispatches
// a user-facing toast. We never stringify `error.config` or
// `error.request` into the toast / store.
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; request_id?: string; code?: string }>) => {
    if (error.config?.skipErrorToast) {
      return Promise.reject(error);
    }
    const status = error.response?.status;
    const body = error.response?.data;
    const detail = body?.detail ?? error.message ?? "请求失败";
    const requestId = body?.request_id;
    const code = body?.code;

    // 409 is almost always "state conflict, retry later" — every real caller
    // (report polling, async task status) handles it with a bespoke retry or
    // progress indicator. A generic "数据冲突" toast on every poll tick is
    // noise. Callers that WANT a toast can always re-throw / pushToast
    // themselves. (Observed 2026-04-24: report page polling while
    // ReportAgent was still generating surfaced a toast every 1.5s.)
    if (status === 409) {
      return Promise.reject(error);
    }

    let title = "请求失败";
    let tone: "error" | "warn" = "error";
    if (!error.response) {
      title = "网络异常";
      tone = "warn";
    } else if (status && status >= 500) {
      title = status === 502 ? "LLM 调用失败" : status === 503 ? "语音服务不可用" : "服务端错误";
    } else if (status === 400) {
      title = "请求参数有误";
      tone = "warn";
    } else if (status === 403 || status === 401) {
      title = "无权限或鉴权失败";
    }

    pushToast({
      tone,
      title,
      message: detail,
      requestId,
    });
    // Re-throw so the caller's existing error handling still runs; the
    // toast is purely additive UX.
    void code;
    return Promise.reject(error);
  },
);
