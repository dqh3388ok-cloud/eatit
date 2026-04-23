import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMachine } from "@xstate/react";
import { useNavigate, useParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import type {
  ClientTextEvent,
  ServerEvent,
} from "@eatit/shared-types";
import { API_BASE_URL } from "@/api/client";
import { getAppSetting } from "@/api/appSettings";
import { loadLLMConfig, type LLMConfig } from "@/lib/llm/config";
import {
  createAudioRecorder,
  requestMicPermission,
  type AudioRecorderHandle,
} from "@/lib/mic";
import { LiveCaption } from "@/pages/interview/LiveCaption";
import { ObserverPanel } from "@/pages/interview/ObserverPanel";
import { VoiceControl } from "@/pages/interview/VoiceControl";
import { interviewMachine } from "@/statecharts/interview-machine";

const OBSERVER_BREAKPOINT_PX = 1100;

type InputMode = "voice" | "text";

function getViewportWidth(): number {
  if (typeof window === "undefined") return OBSERVER_BREAKPOINT_PX;
  return window.innerWidth;
}

function toWs(baseUrl: string): string {
  return baseUrl.startsWith("https://")
    ? baseUrl.replace("https://", "wss://")
    : baseUrl.replace("http://", "ws://");
}

export function InterviewPage(): JSX.Element {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [state, send] = useMachine(interviewMachine);
  const socketRef = useRef<WebSocket | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<AudioRecorderHandle | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [inputMode, setInputMode] = useState<InputMode>("voice");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [observerPanelEnabled, setObserverPanelEnabled] = useState(true);
  const [observerCollapsed, setObserverCollapsed] = useState(
    () => getViewportWidth() < OBSERVER_BREAKPOINT_PX,
  );

  useEffect(() => {
    let mounted = true;
    loadLLMConfig()
      .then((cfg) => {
        if (mounted) setLlmConfig(cfg);
      })
      .catch(() => {
        /* keychain unavailable */
      })
      .finally(() => {
        if (mounted) setConfigLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    getAppSetting<boolean>("observer_panel_enabled")
      .then((value) => {
        if (!mounted) return;
        if (value === null || value === undefined) {
          setObserverPanelEnabled(true);
          return;
        }
        setObserverPanelEnabled(Boolean(value));
      })
      .catch(() => {
        /* backend unavailable — default to on */
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    function onResize() {
      if (getViewportWidth() < OBSERVER_BREAKPOINT_PX) {
        setObserverCollapsed(true);
      }
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (!sessionId || configLoading) return;
    if (!llmConfig) {
      send({ type: "WS_ERROR", message: "尚未配置 LLM,请先前往「设置」。" });
      return;
    }

    send({ type: "CONNECT", sessionId });

    const url = `${toWs(API_BASE_URL)}/ws/sessions/${sessionId}?token=mock`;
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      // First frame must be client.session.init — see phase3-constraints A2.
      const initFrame: ClientTextEvent = {
        event: "client.session.init",
        config: {
          provider: llmConfig.provider,
          api_key: llmConfig.api_key,
          model: llmConfig.model,
          base_url: llmConfig.base_url ?? null,
        },
      };
      socket.send(JSON.stringify(initFrame));
      send({ type: "WS_OPEN" });
    };

    socket.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as ServerEvent;
        if (parsed.event === "server.question.generated") {
          send({ type: "SERVER_QUESTION", payload: parsed.payload });
        } else if (parsed.event === "server.turn.assessed") {
          send({ type: "SERVER_ASSESSED", payload: parsed.payload });
        } else if (parsed.event === "server.coach.observation") {
          send({ type: "SERVER_OBSERVATION", payload: parsed.payload });
        } else if (parsed.event === "server.transcript.partial") {
          send({ type: "TRANSCRIPT_PARTIAL", text: parsed.payload.text });
        } else if (parsed.event === "server.transcript.final") {
          send({ type: "TRANSCRIPT_FINAL", text: parsed.payload.text });
        } else if (parsed.event === "server.error") {
          send({ type: "WS_ERROR", message: `${parsed.code}: ${parsed.message}` });
        }
      } catch (err) {
        send({
          type: "WS_ERROR",
          message: err instanceof Error ? err.message : "无法解析服务器消息",
        });
      }
    };

    socket.onerror = () => {
      send({ type: "WS_ERROR", message: "WebSocket 连接异常" });
    };

    socket.onclose = () => {
      socketRef.current = null;
    };

    return () => {
      try {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ event: "client.session.end" }));
        }
      } catch {
        /* socket already closed */
      }
      socket.close();
      socketRef.current = null;
    };
  }, [sessionId, configLoading, llmConfig, send]);

  useEffect(() => {
    if (state.matches("ended") && sessionId) {
      navigate(`/report/${sessionId}`, { replace: true });
    }
  }, [state, sessionId, navigate]);

  const sendClientFrame = useCallback((frame: ClientTextEvent) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(frame));
    }
  }, []);

  const stopRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder) {
      recorder.stop();
    }
    recorderRef.current = null;
  }, []);

  const handleVoiceStart = useCallback(async () => {
    const question = state.context.currentQuestion;
    if (!question) return;
    if (state.context.isRecording) return;
    setVoiceError(null);

    let stream = micStreamRef.current;
    if (!stream) {
      const result = await requestMicPermission();
      if (!result.ok) {
        setVoiceError(result.message);
        return;
      }
      stream = result.stream;
      micStreamRef.current = stream;
    }

    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setVoiceError("WebSocket 尚未连接,无法开始录音");
      return;
    }

    const turnIndex = question.turn_index;
    const recorder = createAudioRecorder(
      stream,
      (chunk) => {
        chunk
          .arrayBuffer()
          .then((buffer) => {
            const s = socketRef.current;
            if (s && s.readyState === WebSocket.OPEN) {
              s.send(buffer);
            }
          })
          .catch(() => {
            /* chunk arrayBuffer failure is non-fatal for the stream */
          });
      },
      undefined,
      { timesliceMs: 100 },
    );
    recorderRef.current = recorder;

    sendClientFrame({ event: "client.audio.start", turn_index: turnIndex });
    recorder.start();
    send({ type: "AUDIO_START" });
  }, [state, sendClientFrame, send]);

  const handleVoiceStop = useCallback(() => {
    const question = state.context.currentQuestion;
    if (!question) return;
    if (!state.context.isRecording) return;
    stopRecording();
    sendClientFrame({ event: "client.audio.stop", turn_index: question.turn_index });
    send({ type: "AUDIO_STOP" });
  }, [state, sendClientFrame, send, stopRecording]);

  useEffect(() => {
    return () => {
      stopRecording();
      const stream = micStreamRef.current;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
      }
    };
  }, [stopRecording]);

  const handleSubmit = () => {
    const question = state.context.currentQuestion;
    if (!question) return;
    const answer = state.context.draftAnswer.trim();
    if (!answer) return;
    sendClientFrame({
      event: "client.turn.end",
      turn_index: question.turn_index,
      question: question.question,
      answer,
    });
    send({ type: "SUBMIT_ANSWER" });
  };

  const statusLabel = useMemo(() => {
    if (state.matches("idle")) return "待启动";
    if (state.matches("connecting")) return "正在连接...";
    if (state.matches("ready")) return "等待第一道问题";
    if (state.matches("user_answering")) return "轮到你作答";
    if (state.matches("scoring")) return "AI 正在复盘这轮";
    if (state.matches("next_question")) return "生成下一题中...";
    if (state.matches("ended")) return "面试结束";
    return "";
  }, [state]);

  if (!sessionId) {
    return (
      <Center>
        <p style={{ color: "var(--ink-500)" }}>缺少 session_id,请从「面试配置」开始。</p>
      </Center>
    );
  }

  const isUserAnswering = state.matches("user_answering");
  const showObserverPanel = observerPanelEnabled;
  const mainColumn = (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <header style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div className="eyebrow">04 · 实时面试</div>
        <h1
          className="h-serif"
          style={{
            margin: "10px 0 2px",
            fontSize: 36,
            lineHeight: 1.1,
            fontWeight: 400,
            color: "var(--ink-900)",
          }}
        >
          AI 模拟面试官
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: "var(--ink-500)" }}>
          会话 · <span className="mono">{sessionId}</span>
        </p>
      </header>

      <StatusBar label={statusLabel} error={state.context.error} />

      <section
        className="ds-card"
        style={{
          padding: 22,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          minHeight: 260,
        }}
      >
        {state.context.currentQuestion ? (
          <>
            <div style={{ fontSize: 12, color: "var(--ink-500)" }}>
              第 {state.context.currentQuestion.turn_index} 轮 ·{" "}
              {state.context.currentQuestion.expected_depth}
            </div>
            <div
              className="h-serif"
              style={{
                fontSize: 24,
                lineHeight: 1.3,
                color: "var(--ink-900)",
                fontWeight: 400,
              }}
            >
              {state.context.currentQuestion.question}
            </div>
          </>
        ) : (
          <div style={{ color: "var(--ink-500)", fontSize: 14 }}>
            {state.matches("connecting") || state.matches("ready") ? (
              <span>
                <Loader2 size={14} className="spin" style={{ verticalAlign: -2, marginRight: 6 }} />
                面试官正在准备第一个问题...
              </span>
            ) : (
              "等待服务端下发问题"
            )}
          </div>
        )}

        <ModeToggle
          mode={inputMode}
          disabled={!isUserAnswering || state.context.isRecording}
          onChange={(next) => {
            if (next === inputMode) return;
            if (state.context.isRecording) handleVoiceStop();
            setInputMode(next);
          }}
        />

        {inputMode === "voice" ? (
          <>
            <VoiceControl
              isRecording={state.context.isRecording}
              disabled={!isUserAnswering}
              partialTranscript={state.context.partialTranscript}
              onStart={() => {
                void handleVoiceStart();
              }}
              onStop={handleVoiceStop}
            />
            <LiveCaption
              finalTranscript={state.context.finalTranscript}
              partialTranscript={state.context.partialTranscript}
            />
            {voiceError ? (
              <div
                style={{
                  fontSize: 12,
                  color: "var(--warn)",
                  padding: "8px 10px",
                  borderRadius: "var(--r-sm)",
                  background: "var(--warn-softer)",
                  border: "1px solid var(--warn)",
                }}
              >
                {voiceError}
              </div>
            ) : null}
          </>
        ) : (
          <textarea
            value={state.context.draftAnswer}
            onChange={(e) => send({ type: "UPDATE_ANSWER", value: e.target.value })}
            placeholder="在这里输入你的回答..."
            disabled={!isUserAnswering}
            style={{
              width: "100%",
              minHeight: 140,
              padding: 14,
              borderRadius: "var(--r-md)",
              border: "1px solid var(--line)",
              background: isUserAnswering ? "var(--bg-elev)" : "var(--bg-sunken)",
              color: "var(--ink-900)",
              fontFamily: "var(--f-sans)",
              fontSize: 14,
              lineHeight: 1.6,
              resize: "vertical",
            }}
          />
        )}

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={
              !isUserAnswering ||
              state.context.isRecording ||
              state.context.draftAnswer.trim().length === 0
            }
            style={{
              padding: "10px 20px",
              borderRadius: "var(--r-md)",
              border: "none",
              background:
                isUserAnswering &&
                !state.context.isRecording &&
                state.context.draftAnswer.trim().length > 0
                  ? "var(--brand)"
                  : "var(--ink-200)",
              color: "white",
              fontSize: 13.5,
              fontWeight: 500,
              cursor: isUserAnswering && !state.context.isRecording ? "pointer" : "not-allowed",
            }}
          >
            提交回答
          </button>
          <button
            type="button"
            onClick={() => {
              sendClientFrame({ event: "client.session.end" });
              send({ type: "END_SESSION" });
            }}
            disabled={state.matches("ended") || state.matches("idle")}
            style={{
              padding: "10px 18px",
              borderRadius: "var(--r-md)",
              border: "1px solid var(--line)",
              background: "var(--bg-elev)",
              color: "var(--ink-900)",
              fontSize: 13.5,
              cursor: "pointer",
            }}
          >
            提前结束
          </button>
        </div>
      </section>

      {state.context.lastAssessment ? (
        <section
          className="ds-card"
          style={{ padding: 18, display: "flex", flexDirection: "column", gap: 8 }}
        >
          <div style={{ fontSize: 12, color: "var(--ink-500)" }}>
            上一轮复盘 · 第 {state.context.lastAssessment.turn_index} 轮
          </div>
          <div style={{ fontSize: 13.5, color: "var(--ink-900)", lineHeight: 1.6 }}>
            {state.context.lastAssessment.summary}
          </div>
          {state.context.lastAssessment.strengths.length > 0 ||
          state.context.lastAssessment.weaknesses.length > 0 ? (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {state.context.lastAssessment.strengths.map((s) => (
                <span key={`s-${s}`} className="ds-tag ds-tag-green">
                  ✓ {s}
                </span>
              ))}
              {state.context.lastAssessment.weaknesses.map((w) => (
                <span
                  key={`w-${w}`}
                  className="ds-tag"
                  style={{ background: "var(--warn-softer)", color: "var(--warn)" }}
                >
                  △ {w}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );

  if (!showObserverPanel) {
    return mainColumn;
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: observerCollapsed ? "1fr 36px" : "minmax(0, 1fr) 280px",
        gap: 0,
        alignItems: "stretch",
        minHeight: "calc(100vh - 32px)",
      }}
    >
      <div style={{ minWidth: 0, paddingRight: 20 }}>{mainColumn}</div>
      <ObserverPanel
        observations={state.context.observations}
        collapsed={observerCollapsed}
        onToggle={() => setObserverCollapsed((v) => !v)}
      />
    </div>
  );
}

function ModeToggle({
  mode,
  disabled,
  onChange,
}: {
  mode: InputMode;
  disabled: boolean;
  onChange: (next: InputMode) => void;
}): JSX.Element {
  return (
    <div
      role="radiogroup"
      aria-label="回答方式"
      style={{
        display: "inline-flex",
        alignSelf: "flex-start",
        padding: 3,
        gap: 2,
        borderRadius: "var(--r-pill)",
        background: "var(--bg-sunken)",
        border: "1px solid var(--line)",
      }}
    >
      {(["voice", "text"] as const).map((value) => {
        const selected = mode === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled && !selected}
            onClick={() => onChange(value)}
            style={{
              padding: "6px 14px",
              borderRadius: "var(--r-pill)",
              border: "none",
              background: selected ? "var(--bg-elev)" : "transparent",
              color: selected ? "var(--ink-900)" : "var(--ink-500)",
              fontSize: 12.5,
              fontWeight: selected ? 500 : 400,
              cursor: disabled && !selected ? "not-allowed" : "pointer",
              boxShadow: selected ? "var(--shadow-xs)" : "none",
            }}
          >
            {value === "voice" ? "语音" : "文字"}
          </button>
        );
      })}
    </div>
  );
}

function StatusBar({ label, error }: { label: string; error: string | null }): JSX.Element {
  return (
    <div
      style={{
        padding: "10px 14px",
        borderRadius: "var(--r-md)",
        background: error ? "var(--warn-softer)" : "var(--brand-softer)",
        color: error ? "var(--warn)" : "var(--brand-ink)",
        border: `1px solid ${error ? "var(--warn)" : "var(--brand)"}`,
        fontSize: 13,
        display: "flex",
        gap: 10,
      }}
    >
      <span>{label}</span>
      {error ? <span>· {error}</span> : null}
    </div>
  );
}

function Center({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <div
      style={{
        minHeight: 280,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {children}
    </div>
  );
}
