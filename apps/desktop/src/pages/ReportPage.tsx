import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import type { InterviewReportResponse } from "@eatit/shared-types";
import { generateReport, getSessionReport } from "@/api/sessions";
import { PassProbabilityRing } from "@/pages/report/PassProbabilityRing";
import { ReasonRow } from "@/pages/report/ReasonRow";

type ReportState =
  | { kind: "loading" }
  | { kind: "generating" }
  | { kind: "ready"; data: InterviewReportResponse }
  | { kind: "error"; message: string };

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 120_000;

function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail ?? err.message;
  }
  return err instanceof Error ? err.message : "请求失败";
}

export function ReportPage(): JSX.Element {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<ReportState>({ kind: "loading" });

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    const started = Date.now();

    async function ensureAndPoll() {
      setState({ kind: "loading" });
      // First attempt: fetch existing; if 409 (still generating) or 404 (not
      // yet requested), trigger + poll. This makes the page idempotent: the
      // same URL works whether the report was previously requested or not.
      try {
        const existing = await getSessionReport(sessionId!);
        if (cancelled) return;
        setState({ kind: "ready", data: existing });
        return;
      } catch (err) {
        const status = axios.isAxiosError(err) ? err.response?.status : null;
        if (status !== 404 && status !== 409) {
          if (!cancelled) setState({ kind: "error", message: extractError(err) });
          return;
        }
      }

      try {
        await generateReport(sessionId!);
      } catch (err) {
        if (!cancelled) setState({ kind: "error", message: extractError(err) });
        return;
      }

      if (cancelled) return;
      setState({ kind: "generating" });

      while (!cancelled) {
        if (Date.now() - started > POLL_TIMEOUT_MS) {
          setState({ kind: "error", message: "报告生成超时,请稍后重试。" });
          return;
        }
        try {
          const response = await getSessionReport(sessionId!);
          if (cancelled) return;
          setState({ kind: "ready", data: response });
          return;
        } catch (err) {
          const status = axios.isAxiosError(err) ? err.response?.status : null;
          if (status === 409) {
            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
            continue;
          }
          if (!cancelled) setState({ kind: "error", message: extractError(err) });
          return;
        }
      }
    }

    void ensureAndPoll();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const header = useMemo(
    () => (
      <header style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            cursor: "pointer",
            fontSize: 12,
            color: "var(--ink-500)",
          }}
          onClick={() => navigate("/history")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter") navigate("/history");
          }}
        >
          <ArrowLeft size={14} /> 返回面试记录
        </div>
        <div className="eyebrow">06 · 评估报告</div>
        <h1
          className="h-serif"
          style={{
            fontSize: 42,
            lineHeight: 1.1,
            fontWeight: 400,
            margin: "10px 0 0",
            color: "var(--ink-900)",
          }}
        >
          本场面试的复盘
        </h1>
      </header>
    ),
    [navigate],
  );

  if (!sessionId) {
    return (
      <div style={{ color: "var(--ink-500)" }}>缺少 session_id。</div>
    );
  }

  if (state.kind === "loading" || state.kind === "generating") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {header}
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div className="shimmer" style={{ width: 110, height: 110, borderRadius: "50%" }} />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
            <div className="shimmer" style={{ height: 14, width: "50%" }} />
            <div className="shimmer" style={{ height: 12, width: "70%" }} />
            <div className="shimmer" style={{ height: 12, width: "40%" }} />
          </div>
        </div>
        <div className="ds-card" style={{ padding: 22, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="shimmer" style={{ height: 14, width: "30%" }} />
          <div className="shimmer" style={{ height: 10, width: "80%" }} />
          <div className="shimmer" style={{ height: 10, width: "75%" }} />
          <div className="shimmer" style={{ height: 10, width: "82%" }} />
        </div>
        <div style={{ fontSize: 12.5, color: "var(--ink-500)" }}>通常约 20 秒</div>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {header}
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--r-md)",
            background: "var(--warn-soft)",
            color: "var(--warn)",
            border: "1px solid var(--warn)",
            fontSize: 13.5,
          }}
        >
          {state.message}
        </div>
      </div>
    );
  }

  const payload = state.data.payload;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      {header}

      <section
        className="ds-card"
        style={{
          padding: 22,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <PassProbabilityRing value={payload.pass_probability} />
        <div
          style={{
            fontSize: 14,
            lineHeight: 1.7,
            color: "var(--ink-900)",
          }}
        >
          {payload.overall_summary}
        </div>
      </section>

      {payload.reasons.length > 0 ? (
        <section>
          <div
            className="eyebrow"
            style={{ marginBottom: 10 }}
          >
            证据绑定的维度评价
          </div>
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: 0,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            {payload.reasons.map((reason, idx) => (
              <ReasonRow
                key={`${reason.aspect}-${idx}`}
                reason={reason}
              />
            ))}
          </ul>
        </section>
      ) : null}

      {payload.next_actions.length > 0 ? (
        <section
          className="ds-card"
          style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}
        >
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--ink-900)" }}>
            下一场面试前可以做的事
          </h2>
          <ol
            style={{
              margin: 0,
              paddingLeft: 20,
              display: "flex",
              flexDirection: "column",
              gap: 6,
              color: "var(--ink-700)",
              fontSize: 13.5,
              lineHeight: 1.6,
            }}
          >
            {payload.next_actions.map((action, idx) => (
              <li key={`${action}-${idx}`}>{action}</li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}
