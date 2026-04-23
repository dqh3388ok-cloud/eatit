import { apiClient } from "@/api/client";

export interface ASRHealth {
  available: boolean;
  provider: string;
}

/**
 * GET /api/v1/asr/health — returns whether the server has Azure Speech
 * credentials wired up. The desktop SettingsPage uses this to disable the
 * "面试语音模式" switch (and InterviewPage uses it at mount time to decide
 * whether to render VoiceControl at all).
 */
export async function fetchASRHealth(): Promise<ASRHealth> {
  const response = await apiClient.get<ASRHealth>("/api/v1/asr/health");
  return response.data;
}
