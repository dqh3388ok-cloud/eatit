import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Loader2 } from "lucide-react";
import type { SessionListResponse } from "@eatit/shared-types";
import { getSessionList } from "@/api/sessions";

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

export function HistoryPage(): JSX.Element {
  const navigate = useNavigate();
  const query = useQuery<SessionListResponse>({
    queryKey: ["sessions", "list"],
    queryFn: () => getSessionList({ page: 1, page_size: 50 }),
  });

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
    </div>
  );
}
