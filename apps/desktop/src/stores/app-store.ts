import { create } from "zustand";
import type {
  InterviewDirection,
  InterviewStyle,
  ParseResultPayload,
} from "@eatit/shared-types";

type UploadStatus = "idle" | "uploading" | "uploaded" | "failed";
type ParseStatus = "idle" | "running" | "succeeded" | "failed";

export type CurrentUpload = {
  assetBundleId: string | null;
  resumeFileName: string | null;
  jdFileName: string | null;
  resumeStatus: UploadStatus;
  jdStatus: UploadStatus;
  parseStatus: ParseStatus;
  parsePayload: ParseResultPayload | null;
  error: string | null;
};

export type CurrentConfig = {
  style: InterviewStyle;
  direction: InterviewDirection;
  durationMinutes: number;
};

type AppStore = {
  upload: CurrentUpload;
  patchUpload: (patch: Partial<CurrentUpload>) => void;
  resetUpload: () => void;

  config: CurrentConfig;
  patchConfig: (patch: Partial<CurrentConfig>) => void;
};

const DEFAULT_UPLOAD: CurrentUpload = {
  assetBundleId: null,
  resumeFileName: null,
  jdFileName: null,
  resumeStatus: "idle",
  jdStatus: "idle",
  parseStatus: "idle",
  parsePayload: null,
  error: null,
};

const DEFAULT_CONFIG: CurrentConfig = {
  style: "standard_professional",
  direction: "project_deep_dive",
  durationMinutes: 20,
};

export const useAppStore = create<AppStore>((set) => ({
  upload: { ...DEFAULT_UPLOAD },
  patchUpload: (patch) =>
    set((state) => ({ upload: { ...state.upload, ...patch } })),
  resetUpload: () => set({ upload: { ...DEFAULT_UPLOAD } }),

  config: { ...DEFAULT_CONFIG },
  patchConfig: (patch) =>
    set((state) => ({ config: { ...state.config, ...patch } })),
}));
