import type { LLMProvider } from "@/lib/llm/config";

export interface ProviderPreset {
  id: LLMProvider;
  label: string;
  registerUrl: string;
  baseUrl: string;
  models: readonly string[];
  hint?: string;
}

/**
 * Static metadata for the six supported providers plus a "custom" escape hatch.
 *
 * baseUrl / models are used to pre-fill the Settings form; registerUrl is shown
 * as a help link when the user has not yet created a key. None of these URLs
 * are ever used for client-side `fetch` — the backend is the only LLM client
 * (see phase3-constraints.md §A1). They exist purely as provider metadata.
 */
export const PROVIDERS: readonly ProviderPreset[] = [
  {
    id: "siliconflow",
    label: "硅基流动 SiliconFlow",
    registerUrl: "https://cloud.siliconflow.cn/",
    baseUrl: "https://api.siliconflow.cn/v1",
    models: [
      "Qwen/Qwen2.5-7B-Instruct",
      "Qwen/Qwen2.5-32B-Instruct",
      "deepseek-ai/DeepSeek-V2.5",
    ],
    hint: "国内直连,兼容 OpenAI 协议。",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    registerUrl: "https://platform.deepseek.com/",
    baseUrl: "https://api.deepseek.com/v1",
    models: ["deepseek-chat", "deepseek-reasoner"],
    hint: "性价比高,官方 OpenAI 兼容端点。",
  },
  {
    id: "dashscope",
    label: "阿里云百炼 DashScope",
    registerUrl: "https://bailian.console.aliyun.com/",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    models: ["qwen-plus", "qwen-max", "qwen-turbo"],
    hint: "阿里云百炼平台,需开通 OpenAI 兼容模式。",
  },
  {
    id: "openai",
    label: "OpenAI",
    registerUrl: "https://platform.openai.com/api-keys",
    baseUrl: "https://api.openai.com/v1",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
    hint: "境外访问,注意网络环境。",
  },
  {
    id: "anthropic",
    label: "Anthropic",
    registerUrl: "https://console.anthropic.com/",
    baseUrl: "https://api.anthropic.com/v1",
    models: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    hint: "境外访问,注意网络环境。",
  },
  {
    id: "custom",
    label: "自定义 (OpenAI 兼容)",
    registerUrl: "",
    baseUrl: "",
    models: [],
    hint: "任意 OpenAI 兼容端点,自行填写 Base URL 与模型名。",
  },
] as const;

export function getProvider(id: LLMProvider): ProviderPreset {
  return PROVIDERS.find((p) => p.id === id) ?? PROVIDERS[PROVIDERS.length - 1];
}
