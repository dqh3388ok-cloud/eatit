type PlaceholderProps = {
  eyebrow: string;
  title: string;
  description: string;
};

/**
 * Transitional placeholder body rendered inside AppShell for pages that are
 * scaffolded but not yet implemented. To be replaced by the real page body
 * in Phase 3.10b / 3.10c.
 */
export function PagePlaceholder({ eyebrow, title, description }: PlaceholderProps): JSX.Element {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <div className="eyebrow">{eyebrow}</div>
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
          {title}
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "var(--ink-500)",
            maxWidth: 620,
            lineHeight: 1.6,
          }}
        >
          {description}
        </p>
      </div>

      <div
        className="ds-card"
        style={{
          padding: "22px 24px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span className="ds-tag ds-tag-green">待建设</span>
        <span style={{ fontSize: 13, color: "var(--ink-500)" }}>
          这一页将在 Phase 3 的后续节次中接入真实业务。
        </span>
      </div>
    </div>
  );
}
