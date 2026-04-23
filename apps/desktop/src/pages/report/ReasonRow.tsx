import type { ReportReason } from "@eatit/shared-types";

interface Props {
  reason: ReportReason;
}

const VERDICT_LABEL: Record<ReportReason["verdict"], string> = {
  strong: "强项",
  solid: "达标",
  mixed: "两面",
  weak: "薄弱",
};

function verdictTagStyle(verdict: ReportReason["verdict"]): React.CSSProperties {
  switch (verdict) {
    case "strong":
      return { background: "var(--brand)", color: "#fff", borderColor: "var(--brand)" };
    case "solid":
      return {
        background: "var(--brand-soft)",
        color: "var(--brand-ink)",
        borderColor: "var(--brand)",
      };
    case "mixed":
      return {
        background: "var(--bg-sunken)",
        color: "var(--ink-700)",
        borderColor: "var(--line-strong)",
      };
    case "weak":
      return {
        background: "var(--warn-softer)",
        color: "var(--warn)",
        borderColor: "var(--warn)",
      };
  }
}

export function ReasonRow({ reason }: Props): JSX.Element {
  return (
    <li
      className="ds-card"
      style={{
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "var(--ink-900)",
          }}
        >
          {reason.aspect}
        </span>
        <span
          className="ds-tag"
          style={{
            ...verdictTagStyle(reason.verdict),
            border: "1px solid",
            fontSize: 11.5,
          }}
        >
          {VERDICT_LABEL[reason.verdict]}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 11.5,
            color: "var(--ink-500)",
            marginLeft: "auto",
          }}
          title={`第 ${reason.evidence_turn_index} 轮证据`}
        >
          #turn-{reason.evidence_turn_index}
        </span>
      </header>
      <blockquote
        style={{
          margin: 0,
          padding: "10px 14px",
          borderLeft: "3px solid var(--line-strong)",
          background: "var(--bg-sunken)",
          borderRadius: "var(--r-sm)",
          fontSize: 13,
          lineHeight: 1.6,
          color: "var(--ink-700)",
        }}
      >
        “{reason.quote}”
      </blockquote>
    </li>
  );
}
