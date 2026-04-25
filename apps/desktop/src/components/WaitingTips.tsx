import { useEffect, useState } from "react";
import { Lightbulb } from "lucide-react";

/**
 * Rotating-tip overlay for long-running operations (resume parse, report
 * generation). Shown alongside whatever skeleton/spinner the page already
 * has, gives the user something useful to read instead of staring at a
 * shimmer for 20s.
 *
 * Tips are intentionally short and actionable — a one-liner delivered
 * every few seconds beats a wall of best-practice text. Tips don't loop
 * randomly; they cycle in order so a user who waits long enough sees
 * each tip exactly once before repeating.
 */

const ROTATION_INTERVAL_MS = 4000;

const TIPS: readonly string[] = [
  "STAR 法则:Situation 背景 → Task 任务 → Action 行动 → Result 结果。",
  "回答项目题先一句话总览,再分层展开,避免一上来就堆细节。",
  "面试官追问意味着对你的方向感兴趣,把「为什么这样做」讲清楚。",
  "数字是答案的「锚」:延迟从 200ms 降到 50ms 比「明显变快」更可信。",
  "技术决策题别只说选了什么,把放弃的方案 + 取舍说出来。",
  "遇到不熟的题不要假装,先复述题意,再说思路边界。",
  "面试官沉默 ≠ 答得不好,通常是在打字记录,不要急着补救。",
  "设计题先问约束:QPS、数据量、一致性要求、SLA,再画方案。",
  "回答时间控制在 1–3 分钟,长答先画结构,再展开 1–2 个重点。",
  "失败经历题重点不是 bug 本身,而是你怎么定位 + 怎么避免下次。",
  "用「我」而不是「我们」,清晰说明你个人的贡献占比。",
  "结尾留一个钩子:「如果展开聊 X,我可以从…」,方便面试官继续问。",
];

type Props = {
  // Optional title override (e.g. "正在解析简历..." / "正在生成报告...")
  // Page passes its own primary loading copy; tips are the secondary line.
  title: string;
  // Optional subtitle below the title (e.g. "通常约 20 秒"). Falls below
  // the title and above the rotating tip.
  subtitle?: string;
};

export function WaitingTips({ title, subtitle }: Props): JSX.Element {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const handle = window.setInterval(() => {
      setIndex((prev) => (prev + 1) % TIPS.length);
    }, ROTATION_INTERVAL_MS);
    return () => {
      window.clearInterval(handle);
    };
  }, []);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
        padding: "20px 22px",
        borderRadius: "var(--r-md)",
        background: "var(--bg-warm)",
        border: "1px solid var(--line)",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-900)" }}>
          {title}
        </div>
        {subtitle ? (
          <div style={{ fontSize: 12, color: "var(--ink-500)" }}>{subtitle}</div>
        ) : null}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 10,
          padding: "12px 14px",
          borderRadius: "var(--r-sm)",
          background: "var(--brand-softer)",
          border: "1px solid var(--brand-soft)",
        }}
      >
        <Lightbulb size={14} style={{ color: "var(--brand-ink)", marginTop: 2, flexShrink: 0 }} />
        <div
          // Re-mount on index change so CSS transition can replay; the
          // `key` swap is what actually triggers the fade-in animation.
          key={index}
          style={{
            fontSize: 13,
            lineHeight: 1.7,
            color: "var(--ink-700)",
            animation: "eatit-tip-fade 360ms ease-out",
          }}
        >
          <span style={{ color: "var(--brand-ink)", fontWeight: 500 }}>面试 Tip · </span>
          {TIPS[index]}
        </div>
      </div>

      <style>{`
        @keyframes eatit-tip-fade {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
