/**
 * Microphone capture primitives for the voice-mode interview (Phase 4).
 *
 * Capture flow:
 *   requestMicPermission() → MediaStream (after OS permission grant)
 *   createAudioRecorder(stream, onChunk, onFinal) → AudioRecorderHandle
 *   handle.start() → MediaRecorder emits audio/webm;codecs=opus Blob chunks
 *                     at a configurable timeslice (default 100ms)
 *   handle.stop()  → MediaRecorder fires one final ondataavailable and onstop
 *
 * The WebSocket layer converts each Blob → ArrayBuffer and sends it as a
 * binary frame to the backend's ASR pipeline. See P4.5 for the React wiring.
 *
 * Note: this module only surfaces primitives; no React state, no direct WS
 * coupling. Kept dependency-free so it can be unit-tested in isolation once
 * Vitest is wired up (P4.X).
 */

export type MicPermissionError = "not_supported" | "denied" | "unknown";

export type MicPermissionResult =
  | { ok: true; stream: MediaStream }
  | { ok: false; error: MicPermissionError; message: string };

export async function requestMicPermission(): Promise<MicPermissionResult> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return {
      ok: false,
      error: "not_supported",
      message: "当前环境不支持 navigator.mediaDevices.getUserMedia",
    };
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return { ok: true, stream };
  } catch (err) {
    const domError = err as DOMException;
    const name = domError?.name ?? "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      return {
        ok: false,
        error: "denied",
        // Two real scenarios we have to cover with one message:
        //   1) Eatit is already in System Settings > Privacy > Microphone
        //      with the toggle OFF — user needs to flip it on.
        //   2) Eatit is missing from that list entirely (TCC never saw a
        //      request because a prior dev-build run denied under a
        //      different ad-hoc identity, or user force-quit during the
        //      first prompt). Restarting the packaged app usually triggers
        //      a fresh prompt.
        message:
          "无法访问麦克风。请到 系统设置 > 隐私与安全性 > 麦克风 找到 Eatit 并打开开关;如果列表里没有 Eatit,请完全退出再重新打开 Eatit。",
      };
    }
    return {
      ok: false,
      error: "unknown",
      message: domError?.message ?? String(err),
    };
  }
}

export interface AudioRecorderHandle {
  readonly state: RecordingState;
  start(): void;
  stop(): void;
}

export interface CreateAudioRecorderOptions {
  mimeType?: string;
  timesliceMs?: number;
}

export function createAudioRecorder(
  stream: MediaStream,
  onChunk: (chunk: Blob) => void,
  onFinal?: () => void,
  options?: CreateAudioRecorderOptions,
): AudioRecorderHandle {
  const mimeType = options?.mimeType ?? "audio/webm;codecs=opus";
  const timesliceMs = options?.timesliceMs ?? 100;
  const recorder = new MediaRecorder(stream, { mimeType });

  recorder.addEventListener("dataavailable", (event) => {
    if (event.data && event.data.size > 0) {
      onChunk(event.data);
    }
  });

  if (onFinal) {
    recorder.addEventListener("stop", () => {
      onFinal();
    });
  }

  return {
    get state(): RecordingState {
      return recorder.state;
    },
    start(): void {
      if (recorder.state === "inactive") {
        recorder.start(timesliceMs);
      }
    },
    stop(): void {
      if (recorder.state !== "inactive") {
        recorder.stop();
      }
    },
  };
}
