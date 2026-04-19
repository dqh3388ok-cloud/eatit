import type {
  AssetUploadRequest,
  AssetUploadResponse,
  ParseRequestResponse,
  ParseResultResponse,
} from "@eatit/shared-types";
import { apiClient } from "@/api/client";

export const uploadResume = async (
  file: File,
  request: AssetUploadRequest = {},
): Promise<AssetUploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  if (request.asset_bundle_id) {
    formData.append("asset_bundle_id", request.asset_bundle_id);
  }

  const response = await apiClient.post<AssetUploadResponse>("/api/v1/assets/resume", formData);
  return response.data;
};

export const uploadJd = async (
  file: File,
  request: AssetUploadRequest = {},
): Promise<AssetUploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  if (request.asset_bundle_id) {
    formData.append("asset_bundle_id", request.asset_bundle_id);
  }

  const response = await apiClient.post<AssetUploadResponse>("/api/v1/assets/jd", formData);
  return response.data;
};

export const triggerParse = async (assetBundleId: string): Promise<ParseRequestResponse> => {
  const response = await apiClient.post<ParseRequestResponse>(`/api/v1/assets/${assetBundleId}/parse`);
  return response.data;
};

export const getParseResult = async (assetBundleId: string): Promise<ParseResultResponse> => {
  const response = await apiClient.get<ParseResultResponse>(`/api/v1/assets/${assetBundleId}/parse`);
  return response.data;
};
