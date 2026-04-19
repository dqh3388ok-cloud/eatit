import type {
  CreateSessionRequest,
  CreateSessionResponse,
  EndSessionResponse,
  InterviewReportResponse,
  SessionDetailResponse,
  SessionListRequest,
  SessionListResponse,
  TriggerReportRequest,
  TriggerReportResponse,
} from "@eatit/shared-types";
import { apiClient } from "@/api/client";

export const createSession = async (
  request: CreateSessionRequest,
): Promise<CreateSessionResponse> => {
  const response = await apiClient.post<CreateSessionResponse>("/api/v1/sessions", request);
  return response.data;
};

export const getSession = async (sessionId: string): Promise<SessionDetailResponse> => {
  const response = await apiClient.get<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`);
  return response.data;
};

export const getSessionList = async (
  request: SessionListRequest = {},
): Promise<SessionListResponse> => {
  const response = await apiClient.get<SessionListResponse>("/api/v1/sessions", {
    params: request,
  });
  return response.data;
};

export const endSession = async (sessionId: string): Promise<EndSessionResponse> => {
  const response = await apiClient.post<EndSessionResponse>(`/api/v1/sessions/${sessionId}/end`);
  return response.data;
};

export const generateReport = async (
  sessionId: string,
  request: TriggerReportRequest = {},
): Promise<TriggerReportResponse> => {
  const response = await apiClient.post<TriggerReportResponse>(
    `/api/v1/sessions/${sessionId}/report`,
    request,
  );
  return response.data;
};

export const getSessionReport = async (
  sessionId: string,
): Promise<InterviewReportResponse> => {
  const response = await apiClient.get<InterviewReportResponse>(
    `/api/v1/sessions/${sessionId}/report`,
  );
  return response.data;
};
