interface Props {
  value: number;
}

/**
 * SVG circle showing the 0..100 pass_probability. Uses stroke-dashoffset
 * to fill proportionally; color tiers track the scoring baseline in the
 * Report prompt (80+ strong, 60+ solid, 40+ borderline, below weak).
 */
export function PassProbabilityRing({ value }: Props): JSX.Element {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  let color = "var(--ink-500)";
  let label = "边界";
  if (clamped >= 80) {
    color = "var(--brand)";
    label = "强匹配";
  } else if (clamped >= 60) {
    color = "var(--brand-ink)";
    label = "胜任";
  } else if (clamped >= 40) {
    color = "var(--warn)";
    label = "需复盘";
  } else {
    color = "var(--warn)";
    label = "不匹配";
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}
    >
      <svg width="110" height="110" viewBox="0 0 110 110">
        <circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke="var(--line)"
          strokeWidth="8"
        />
        <circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 55 55)"
        />
        <text
          x="55"
          y="58"
          textAnchor="middle"
          fontFamily="var(--f-serif)"
          fontSize="28"
          fill="var(--ink-900)"
        >
          {clamped}
        </text>
        <text
          x="55"
          y="78"
          textAnchor="middle"
          fontFamily="var(--f-mono)"
          fontSize="10"
          fill="var(--ink-500)"
        >
          / 100
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div className="eyebrow">通过概率</div>
        <div
          style={{
            fontSize: 16,
            fontWeight: 600,
            color,
          }}
        >
          {label}
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-500)", maxWidth: 220 }}>
          基于本轮问答与证据绑定的复盘得出的估计,仅供参考。
        </div>
      </div>
    </div>
  );
}
