import { invoke } from "@tauri-apps/api/core";

export type LLMProvider =
  | "openai"
  | "anthropic"
  | "siliconflow"
  | "deepseek"
  | "dashscope"
  | "custom";

export interface LLMConfig {
  provider: LLMProvider;
  api_key: string;
  model: string;
  base_url?: string | null;
}

/** Persist the full config JSON in the macOS keychain. */
export async function saveLLMConfig(config: LLMConfig): Promise<void> {
  await invoke<void>("save_llm_config", { config: JSON.stringify(config) });
}

/** Load the config from the keychain; returns null when never saved. */
export async function loadLLMConfig(): Promise<LLMConfig | null> {
  const raw = await invoke<string | null>("load_llm_config");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LLMConfig;
  } catch {
    return null;
  }
}

/** Remove the keychain entry. Idempotent: succeeds even if no entry exists. */
export async function deleteLLMConfig(): Promise<void> {
  await invoke<void>("delete_llm_config");
}

/** Base64 encoding of the config for the X-LLM-Config HTTP header. */
export function encodeForHeader(config: LLMConfig): string {
  const json = JSON.stringify(config);
  // btoa requires ASCII; apply TextEncoder for safety with non-ASCII.
  const bytes = new TextEncoder().encode(json);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}
