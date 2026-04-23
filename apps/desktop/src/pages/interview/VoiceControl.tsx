import { Mic, MicOff } from "lucide-react";

/**
 * Hold-to-talk button for voice-mode interviews.
 *
 * Press-and-hold semantics: mousedown / touchstart fires `onStart`;
 * mouseup / touchend / mouseleave / blur fires `onStop`. The lifecycle
 * events are driven from the outside so the InterviewPage can link them
 * to MediaRecorder + WS frames without this component knowing about the
 * socket.
 *
 * Visual states:
 *   - idle:      dark button with mic icon, "按住说话"
 *   - disabled:  gray button (e.g. voice not permitted yet)
 *   - recording: red button, pulsing dot, "正在聆听..." + live partial
 */
export function VoiceControl({
  isRecording,
  disabled,
  partialTranscript,
  onStart,
  onStop,
}: {
  isRecording: boolean;
  disabled?: boolean;
  partialTranscript: string;
  onStart: () => void;
  onStop: () => void;
}): JSX.Element {
  const handleStart = (event: { preventDefault: () => void }) => {
    if (disabled) return;
    event.preventDefault();
    onStart();
  };

  const handleStop = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    if (isRecording) onStop();
  };

  const background = disabled
    ? "var(--ink-200)"
    : isRecording
      ? "var(--warn)"
      : "var(--brand)";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "10px 14px",
        borderRadius: "var(--r-md)",
        border: "1px solid var(--line)",
        background: "var(--bg-elev)",
      }}
    >
      <button
        type="button"
        disabled={disabled}
        onMouseDown={handleStart}
        onMouseUp={handleStop}
        onMouseLeave={handleStop}
        onTouchStart={handleStart}
        onTouchEnd={handleStop}
        onBlur={handleStop}
        aria-pressed={isRecording}
        aria-label={isRecording ? "松开结束录音" : "按住说话"}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 18px",
          borderRadius: "var(--r-pill)",
          border: "none",
          background,
          color: "white",
          fontSize: 13.5,
          fontWeight: 500,
          cursor: disabled ? "not-allowed" : "pointer",
          minWidth: 160,
          justifyContent: "center",
          userSelect: "none",
        }}
      >
        {isRecording ? (
          <>
            <span
              className="pulse-dot"
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: "white",
                display: "inline-block",
              }}
            />
            正在聆听...
          </>
        ) : disabled ? (
          <>
            <MicOff size={15} />
            语音模式不可用
          </>
        ) : (
          <>
            <Mic size={15} />
            按住说话
          </>
        )}
      </button>
      {isRecording && partialTranscript ? (
        <span
          style={{
            fontSize: 13,
            color: "var(--ink-500)",
            fontStyle: "italic",
            flex: 1,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {partialTranscript}
        </span>
      ) : null}
    </div>
  );
}
