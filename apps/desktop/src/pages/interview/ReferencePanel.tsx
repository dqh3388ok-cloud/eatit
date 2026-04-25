import { useEffect, useState } from "react";
import { Lightbulb, ChevronDown, ChevronRight } from "lucide-react";
import type { ReferenceAnswerHint } from "@/statecharts/interview-machine";

type Props = {
  reference: ReferenceAnswerHint | null;
  // Reset the "revealed" state when this changes — used so a new turn
  // forces the user to opt in again instead of leaking the previous
  // turn's hint.
  resetKey: number;
};

/**
 * AI-generated reference answer hint, shown under the answer area.
 *
 * Always rendered (so the user knows the feature exists) but the actual
 * content is hidden behind a "查看 AI 参考答案" reveal so the user gets
 * a chance to answer first. Each new turn resets the reveal state via
 * `resetKey` so the previous turn's hint doesn't bleed through.
 *
 * Three loading states:
 *   - reference === null: backend hasn't pushed `server.reference.ready`
 *     yet. We show a thin "AI 正在准备参考答案..." note.
 *   - reference !== null & not revealed: button to expand.
 *   - reference !== null & revealed: full content.
 */
export function ReferencePanel({ reference, resetKey }: Props): JSX.Element {
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    setRevealed(false);
  }, [resetKey]);

  if (!reference) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 12px",
          borderRadius: "var(--r-md)",
          border: "1px dashed var(--line)",
          background: "var(--bg-warm)",
          color: "var(--ink-500)",
          fontSize: 12,
        }}
      >
        <Lightbulb size={14} />
        <span>AI 正在准备本轮参考答案,稍候可参考。</span>
      </div>
    );
  }

  if (!revealed) {
    return (
      <button
        type="button"
        onClick={() => setRevealed(true)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 14px",
          borderRadius: "var(--r-md)",
          border: "1px solid var(--brand)",
          background: "var(--brand-softer)",
          color: "var(--brand-ink)",
          fontSize: 13,
          fontWeight: 500,
          cursor: "pointer",
          alignSelf: "flex-start",
        }}
      >
        <Lightbulb size={14} />
        查看 AI 参考答案
        <ChevronRight size={14} />
      </button>
    );
  }

  return (
    <section
      className="ds-card"
      style={{
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        background: "var(--brand-softer)",
        border: "1px solid var(--brand-soft)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            fontWeight: 600,
            color: "var(--brand-ink)",
          }}
        >
          <Lightbulb size={14} />
          AI 参考答案
        </div>
        <button
          type="button"
          onClick={() => setRevealed(false)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            padding: "2px 8px",
            borderRadius: "var(--r-sm)",
            border: "1px solid transparent",
            background: "transparent",
            color: "var(--ink-500)",
            fontSize: 11,
            cursor: "pointer",
          }}
        >
          收起 <ChevronDown size={12} />
        </button>
      </header>

      {reference.answer_outline.length > 0 ? (
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            回答提纲
          </div>
          <ol
            style={{
              margin: 0,
              paddingLeft: 18,
              fontSize: 12.5,
              lineHeight: 1.7,
              color: "var(--ink-700)",
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {reference.answer_outline.map((item, idx) => (
              <li key={`outline-${idx}`}>{item}</li>
            ))}
          </ol>
        </div>
      ) : null}

      {reference.ideal_answer ? (
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            完整示例
          </div>
          <div
            style={{
              fontSize: 12.5,
              lineHeight: 1.7,
              color: "var(--ink-900)",
              whiteSpace: "pre-wrap",
            }}
          >
            {reference.ideal_answer}
          </div>
        </div>
      ) : null}

      {reference.key_evaluation_points.length > 0 ? (
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            评分关键点
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              fontSize: 12.5,
              lineHeight: 1.7,
              color: "var(--ink-700)",
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {reference.key_evaluation_points.map((item, idx) => (
              <li key={`kp-${idx}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {reference.common_pitfalls.length > 0 ? (
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            常见误区
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              fontSize: 12.5,
              lineHeight: 1.7,
              color: "var(--warn)",
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {reference.common_pitfalls.map((item, idx) => (
              <li key={`pf-${idx}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
