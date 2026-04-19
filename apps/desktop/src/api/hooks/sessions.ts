import { useMutation, useQuery } from "@tanstack/react-query";
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
import {
  createSession,
  endSession,
  generateReport,
  getSession,
  getSessionList,
  getSessionReport,
} from "@/api/sessions";

export const useCreateSession = () =>
  useMutation<CreateSessionResponse, Error, CreateSessionRequest>({
    mutationFn: (request) => createSession(request),
  });

export const useSession = (sessionId: string | null) =>
  useQuery<SessionDetailResponse>({
    queryKey: ["session", sessionId],
    queryFn: () => {
      if (!sessionId) {
        throw new Error("sessionId is required");
      }
      return getSession(sessionId);
    },
    enabled: Boolean(sessionId),
  });

export const useSessionList = (request: SessionListRequest = {}) =>
  useQuery<SessionListResponse>({
    queryKey: ["session-list", request],
    queryFn: () => getSessionList(request),
  });

export const useEndSession = () =>
  useMutation<EndSessionResponse, Error, string>({
    mutationFn: (sessionId) => endSession(sessionId),
  });

export const useGenerateReport = () =>
  useMutation<
    TriggerReportResponse,
    Error,
    { sessionId: string; request?: TriggerReportRequest }
  >({
    mutationFn: ({ sessionId, request }) => generateReport(sessionId, request),
  });

export const useSessionReport = (sessionId: string | null) =>
  useQuery<InterviewReportResponse>({
    queryKey: ["session-report", sessionId],
    queryFn: () => {
      if (!sessionId) {
        throw new Error("sessionId is required");
      }
      return getSessionReport(sessionId);
    },
    enabled: Boolean(sessionId),
  });
