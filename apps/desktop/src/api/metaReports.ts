import type {
  MetaReportDetailResponse,
  MetaReportListResponse,
  TriggerMetaReportRequest,
  TriggerMetaReportResponse,
} from "@eatit/shared-types";
import { apiClient } from "@/api/client";

export const triggerMetaReport = async (
  request: TriggerMetaReportRequest = {},
): Promise<TriggerMetaReportResponse> => {
  const response = await apiClient.post<TriggerMetaReportResponse>(
    "/api/v1/meta-reports",
    request,
  );
  return response.data;
};

export const getMetaReport = async (
  metaReportId: string,
): Promise<MetaReportDetailResponse> => {
  const response = await apiClient.get<MetaReportDetailResponse>(
    `/api/v1/meta-reports/${metaReportId}`,
  );
  return response.data;
};

export const getMetaReportList = async (
  params: { page?: number; page_size?: number } = {},
): Promise<MetaReportListResponse> => {
  const response = await apiClient.get<MetaReportListResponse>(
    "/api/v1/meta-reports",
    { params },
  );
  return response.data;
};
