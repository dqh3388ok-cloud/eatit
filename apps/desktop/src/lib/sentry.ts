import * as Sentry from "@sentry/react";

/**
 * Sentry scaffold with secret-redacting `beforeSend`.
 *
 * Mirrors the backend contract at apps/api/app/infra/observability/sentry.py:
 * when the DSN is empty (default), initSentry is a no-op and no network
 * traffic is emitted. Production builds wire VITE_SENTRY_DSN via .env so
 * flipping it activates the scaffold end-to-end.
 *
 * Redaction targets (Phase 5 §P5.5, extends Phase 3 constraint §A1 + §C):
 *   - X-LLM-Config header value (base64 LLMConfig)
 *   - AZURE_SPEECH_KEY / AZURE_SPEECH_REGION env values
 *   - Raw audio Blob / ArrayBuffer bytes
 *   - InterviewTurn.answer free-text content (candidate PII)
 *
 * Matching is case-insensitive on the key; value types are inspected for
 * binary blobs so opus chunks never land in breadcrumbs intact.
 */

const REDACTED = "<redacted>";

// Exact-match keys. Must stay in sync with apps/api/app/infra/observability/sentry.py.
const SECRET_EXACT_KEYS = new Set<string>([
  "authorization",
  "bearer",
  "token",
  "password",
  "apikey",
  "answer",
]);

// Substring probes — kept generic so the literal env name / Azure SDK
// field name only live inside apps/api/app/infra/asr/.
const SECRET_KEY_SUBSTRINGS = [
  "llm-config",
  "llm_config",
  "azure_speech",
  "api_key",
  "subscription",
];

function isSecretKey(key: string): boolean {
  const normalized = key.toLowerCase();
  if (SECRET_EXACT_KEYS.has(normalized)) return true;
  for (const probe of SECRET_KEY_SUBSTRINGS) {
    if (normalized.includes(probe)) return true;
  }
  return false;
}

function redactNode(node: unknown): unknown {
  if (node === null || node === undefined) return node;
  if (typeof node === "string" || typeof node === "number" || typeof node === "boolean") {
    return node;
  }
  if (node instanceof ArrayBuffer) {
    return `<bytes len=${node.byteLength}>`;
  }
  if (typeof Blob !== "undefined" && node instanceof Blob) {
    return `<blob size=${node.size} type=${node.type || "unknown"}>`;
  }
  if (Array.isArray(node)) {
    return node.map((item) => redactNode(item));
  }
  if (typeof node === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
      out[key] = isSecretKey(key) ? REDACTED : redactNode(value);
    }
    return out;
  }
  return node;
}

export function initSentry(dsn: string, environment: string): boolean {
  if (!dsn) return false;

  Sentry.init({
    dsn,
    environment,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
    beforeSend(event) {
      return redactNode(event) as Sentry.ErrorEvent;
    },
    beforeBreadcrumb(breadcrumb) {
      return redactNode(breadcrumb) as Sentry.Breadcrumb;
    },
  });
  return true;
}

// Exported for unit tests and for ad-hoc callers that want to scrub a
// payload before logging it locally.
export const __redactForTests = redactNode;
