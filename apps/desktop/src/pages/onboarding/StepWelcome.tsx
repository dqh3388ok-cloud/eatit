interface Props {
  onNext: () => void;
}

export function StepWelcome({ onNext }: Props): JSX.Element {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <div className="eyebrow">01 · 欢迎</div>
        <h1
          className="h-serif"
          style={{
            fontSize: 48,
            lineHeight: 1.05,
            fontWeight: 400,
            margin: "14px 0 10px",
            color: "var(--ink-900)",
          }}
        >
          开始你的第一次模拟面试
        </h1>
        <p
          style={{
            fontSize: 15,
            lineHeight: 1.7,
            color: "var(--ink-500)",
            maxWidth: 560,
            margin: 0,
          }}
        >
          Eatit 在本机跑完整条流水线:上传简历与 JD → AI
          面试官出题并评估回答 → 生成可反复回看的评估报告。所有数据保留在你本机的
          SQLite 数据库里,不上传,不同步。
        </p>
      </div>

      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          fontSize: 13.5,
          color: "var(--ink-700)",
          maxWidth: 560,
        }}
      >
        <li>• 使用你自己的 LLM API Key(BYOK),不需要额外付费给我们</li>
        <li>• API Key 保存在 macOS 钥匙串,不落盘到日志</li>
        <li>• 全程离线可用,除了你配置的 LLM 调用</li>
      </ul>

      <button
        type="button"
        onClick={onNext}
        style={{
          alignSelf: "flex-start",
          padding: "11px 22px",
          borderRadius: "var(--r-md)",
          border: "none",
          background: "var(--brand)",
          color: "white",
          fontSize: 14,
          fontWeight: 500,
          cursor: "pointer",
        }}
      >
        开始配置
      </button>
    </div>
  );
}
