import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { ChevronRight, Loader2, Sparkles } from "lucide-react";
import type { SessionListResponse, SessionSummary } from "@eatit/shared-types";
import { getSessionList } from "@/api/sessions";
import { triggerMetaReport } from "@/api/metaReports";

const STATUS_LABEL: Record<string, string> = {
  created: "已创建",
  session_started: "进行中",
  turn_recording: "作答中",
  turn_transcribing: "转写中",
  turn_evaluating: "评估中",
  turn_compressing: "压缩中",
  next_question_ready: "出题完成",
  paused: "暂停",
  ended: "已结束",
  exited_early: "提前结束",
  report_generating: "报告生成中",
  report_ready: "报告就绪",
  failed: "失败",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function isReady(session: SessionSummary): boolean {
  return session.status === "report_ready";
}

export function HistoryPage(): JSX.Element {
  const navigate = useNavigate();
  const query = useQuery<SessionListResponse>({
    queryKey: ["sessions", "list"],
    queryFn: () => getSessionList({ page: 1, page_size: 50 }),
  });

  const readySessions = useMemo(
    () => (query.data?.items ?? []).filter(isReady),
    [query.data],
  );

  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <div className="eyebrow">05 · 面试记录</div>
        <h1
          className="h-serif"
          style={{
            fontSize: 42,
            lineHeight: 1.1,
            fontWeight: 400,
            margin: "10px 0 6px",
            color: "var(--ink-900)",
          }}
        >
          我的面试记录
        </h1>
        <p style={{ fontSize: 14, color: "var(--ink-500)", maxWidth: 620, lineHeight: 1.6 }}>
          每一次完整或中断的面试都会在这里保留,点击任意一条可查看当时生成的评估报告。
        </p>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          disabled={readySessions.length === 0}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 14px",
            borderRadius: "var(--r-sm)",
            background:
              readySessions.length === 0 ? "var(--bg-sunken)" : "var(--brand)",
            color: readySessions.length === 0 ? "var(--ink-400)" : "white",
            border: "none",
            fontSize: 13,
            fontWeight: 500,
            cursor: readySessions.length === 0 ? "not-allowed" : "pointer",
          }}
        >
          <Sparkles size={14} />
          生成综合分析 ({readySessions.length} 场)
        </button>
        {readySessions.length === 0 ? (
          <div style={{ fontSize: 12, color: "var(--ink-500)" }}>
            需要至少 1 场已完成并生成报告的面试
          </div>
        ) : null}
      </div>

      {query.isLoading ? (
        <div
          className="ds-card"
          style={{
            padding: 22,
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "var(--ink-500)",
            fontSize: 13.5,
          }}
        >
          <Loader2 size={14} className="spin" />
          加载中...
        </div>
      ) : null}

      {query.isError ? (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "var(--r-md)",
            background: "var(--warn-soft)",
            color: "var(--warn)",
            border: "1px solid var(--warn)",
            fontSize: 13,
          }}
        >
          加载失败:{query.error instanceof Error ? query.error.message : "请检查后端连接"}
        </div>
      ) : null}

      {query.data && query.data.items.length === 0 ? (
        <div
          className="ds-card"
          style={{
            padding: 22,
            textAlign: "center",
            color: "var(--ink-500)",
            fontSize: 13.5,
          }}
        >
          还没有面试记录。去「上传与解析」开始一场吧。
        </div>
      ) : null}

      {query.data && query.data.items.length > 0 ? (
        <ul
          className="ds-card"
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {query.data.items.map((item, index) => (
            <li
              key={item.id}
              onClick={() => navigate(`/report/${item.id}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`/report/${item.id}`);
                }
              }}
              style={{
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                gap: 16,
                cursor: "pointer",
                borderTop: index === 0 ? "none" : "1px solid var(--line)",
                transition: "background 120ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--bg-sunken)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink-900)" }}>
                  {formatDate(item.created_at)}
                </div>
                <div style={{ fontSize: 12, color: "var(--ink-500)", marginTop: 4 }}>
                  <span className="mono">{item.id}</span>
                  <span style={{ margin: "0 6px", color: "var(--ink-300)" }}>·</span>
                  {item.turn_count} 轮
                </div>
              </div>
              <span className="ds-tag">
                {STATUS_LABEL[item.status] ?? item.status}
              </span>
              <ChevronRight size={16} color="var(--ink-400)" />
            </li>
          ))}
        </ul>
      ) : null}

      {modalOpen ? (
        <MetaReportModal
          readySessions={readySessions}
          onClose={() => setModalOpen(false)}
        />
      ) : null}
    </div>
  );
}

function MetaReportModal({
  readySessions,
  onClose,
}: {
  readySessions: SessionSummary[];
  onClose: () => void;
}): JSX.Element {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(readySessions.map((s) => s.id)),
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const trigger = useMutation({
    mutationFn: (sessionIds: string[]) =>
      triggerMetaReport({ session_ids: sessionIds }),
    onSuccess: (response) => {
      navigate(`/meta-report/${response.id}`);
    },
    onError: (err) => {
      if (axios.isAxiosError(err)) {
        setErrorMessage(err.response?.data?.detail ?? err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("请求失败");
      }
    },
  });

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleConfirm = () => {
    setErrorMessage(null);
    const ids = Array.from(selected);
    if (ids.length === 0) {
      setErrorMessage("至少选择 1 场");
      return;
    }
    trigger.mutate(ids);
  };

  const singleSession = selected.size === 1;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="生成综合分析"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(17, 24, 20, 0.35)",
        display: "grid",
        placeItems: "center",
        zIndex: 50,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="ds-card"
        style={{
          width: 520,
          maxWidth: "90vw",
          maxHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          gap: 14,
          padding: 20,
        }}
      >
        <div>
          <h2
            className="h-serif"
            style={{
              margin: 0,
              fontSize: 22,
              fontWeight: 400,
              color: "var(--ink-900)",
            }}
          >
            生成综合分析
          </h2>
          <p
            style={{
              fontSize: 13,
              color: "var(--ink-500)",
              marginTop: 6,
              lineHeight: 1.6,
            }}
          >
            选择希望纳入分析的面试。只选 1 场时生成单场复盘,不会凭空凑出趋势。
          </p>
        </div>

        <ul
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            overflowY: "auto",
            border: "1px solid var(--line)",
            borderRadius: "var(--r-sm)",
            maxHeight: 280,
          }}
        >
          {readySessions.map((session) => {
            const checked = selected.has(session.id);
            return (
              <li key={session.id}>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "10px 14px",
                    cursor: "pointer",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(session.id)}
                    style={{ cursor: "pointer" }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: "var(--ink-900)",
                      }}
                    >
                      {formatDate(session.created_at)}
                    </div>
                    <div
                      style={{
                        fontSize: 11.5,
                        color: "var(--ink-500)",
                        marginTop: 2,
                      }}
                    >
                      <span className="mono">{session.id.slice(0, 8)}</span>
                      <span style={{ margin: "0 6px", color: "var(--ink-300)" }}>
                        ·
                      </span>
                      {session.turn_count} 轮
                    </div>
                  </div>
                </label>
              </li>
            );
          })}
        </ul>

        {singleSession ? (
          <div
            style={{
              fontSize: 12,
              color: "var(--info)",
              background: "var(--info-soft)",
              padding: "8px 12px",
              borderRadius: "var(--r-sm)",
            }}
          >
            只选 1 场时生成单场复盘
          </div>
        ) : null}

        {errorMessage ? (
          <div
            style={{
              fontSize: 12,
              color: "var(--warn)",
              background: "var(--warn-soft)",
              padding: "8px 12px",
              borderRadius: "var(--r-sm)",
            }}
          >
            {errorMessage}
          </div>
        ) : null}

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
            marginTop: 4,
          }}
        >
          <button
            type="button"
            onClick={onClose}
            disabled={trigger.isPending}
            style={{
              padding: "8px 14px",
              borderRadius: "var(--r-sm)",
              background: "transparent",
              border: "1px solid var(--line)",
              fontSize: 13,
              color: "var(--ink-700)",
              cursor: trigger.isPending ? "not-allowed" : "pointer",
            }}
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={trigger.isPending || selected.size === 0}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 14px",
              borderRadius: "var(--r-sm)",
              background: "var(--brand)",
              color: "white",
              border: "none",
              fontSize: 13,
              fontWeight: 500,
              cursor:
                trigger.isPending || selected.size === 0
                  ? "not-allowed"
                  : "pointer",
              opacity: trigger.isPending || selected.size === 0 ? 0.7 : 1,
            }}
          >
            {trigger.isPending ? <Loader2 size={14} className="spin" /> : null}
            生成 ({selected.size} 场)
          </button>
        </div>
      </div>
    </div>
  );
}
