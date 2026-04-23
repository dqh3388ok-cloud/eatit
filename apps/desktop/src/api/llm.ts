import { apiClient } from "@/api/client";
import { encodeForHeader, type LLMConfig } from "@/lib/llm/config";

export interface LLMUsage {
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
}

export interface LLMTestResponse {
  ok: boolean;
  usage?: LLMUsage | null;
  error_code?: string | null;
  error_message?: string | null;
}

/**
 * Ask the backend to round-trip a tiny probe prompt using the supplied
 * LLMConfig. The key leaves this process only inside the `X-LLM-Config`
 * header; it is never logged, cached, or returned in the response body.
 */
export async function testLLMConnection(config: LLMConfig): Promise<LLMTestResponse> {
  const response = await apiClient.post<LLMTestResponse>(
    "/api/v1/llm/test",
    null,
    { headers: { "X-LLM-Config": encodeForHeader(config) } },
  );
  return response.data;
}
