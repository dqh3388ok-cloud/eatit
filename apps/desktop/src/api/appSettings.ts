import axios from "axios";
import { apiClient } from "@/api/client";

export interface AppSettingValue<T = unknown> {
  value: T;
}

/**
 * GET /api/v1/app-settings/{key}
 * Returns null when the backend reports 404 "not set".
 * Any other error is re-thrown so the caller can surface it.
 */
export async function getAppSetting<T = unknown>(key: string): Promise<T | null> {
  try {
    const response = await apiClient.get<AppSettingValue<T>>(
      `/api/v1/app-settings/${encodeURIComponent(key)}`,
    );
    return response.data.value;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}

/** PUT /api/v1/app-settings/{key} — persist a JSON-serializable value. */
export async function putAppSetting<T>(key: string, value: T): Promise<T> {
  const response = await apiClient.put<AppSettingValue<T>>(
    `/api/v1/app-settings/${encodeURIComponent(key)}`,
    { value },
  );
  return response.data.value;
}
