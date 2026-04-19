import { useMutation, useQuery } from "@tanstack/react-query";
import type {
  AssetUploadRequest,
  ParseRequestResponse,
  ParseResultResponse,
} from "@eatit/shared-types";
import { getParseResult, triggerParse, uploadJd, uploadResume } from "@/api/assets";

export const useUploadResume = () =>
  useMutation({
    mutationFn: ({ file, request }: { file: File; request?: AssetUploadRequest }) =>
      uploadResume(file, request),
  });

export const useUploadJd = () =>
  useMutation({
    mutationFn: ({ file, request }: { file: File; request?: AssetUploadRequest }) =>
      uploadJd(file, request),
  });

export const useTriggerParse = () =>
  useMutation<ParseRequestResponse, Error, string>({
    mutationFn: (assetBundleId) => triggerParse(assetBundleId),
  });

export const useParseResult = (assetBundleId: string | null) =>
  useQuery<ParseResultResponse>({
    queryKey: ["parse-result", assetBundleId],
    queryFn: () => {
      if (!assetBundleId) {
        throw new Error("assetBundleId is required");
      }
      return getParseResult(assetBundleId);
    },
    enabled: Boolean(assetBundleId),
  });
