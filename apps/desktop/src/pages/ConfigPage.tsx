import { useState } from "react";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import type {
  InterviewDirection,
  InterviewStyle,
} from "@eatit/shared-types";
import { createSession } from "@/api/sessions";
import { useAppStore } from "@/stores/app-store";

type TileOption<T extends string> = {
  value: T;
  label: string;
  hint: string;
};

const STYLE_OPTIONS: TileOption<InterviewStyle>[] = [
  {
    value: "friendly_guided",
    label: "友好引导",
    hint: "轻松破冰,给提示,适合第一次模拟",
  },
  {
    value: "standard_professional",
    label: "标准专业",
    hint: "正式但克制,不给额外提示",
  },
  {
    value: "high_pressure_followup",
    label: "高强度追问",
    hint: "连续追问,挑战表达与抗压",
  },
];

const DIRECTION_OPTIONS: TileOption<InterviewDirection>[] = [
  {
    value: "role_match",
    label: "岗位匹配",
    hint: "聚焦候选人与岗位的契合度",
  },
  {
    value: "project_deep_dive",
    label: "项目深挖",
    hint: "围绕 1~2 个重点项目纵向追问",
  },
  {
    value: "behavioral_comprehensive",
    label: "行为综合",
    hint: "覆盖协作/复盘/抗压等维度",
  },
];

const DURATION_OPTIONS: TileOption<string>[] = [
  { value: "15", label: "15 分钟", hint: "短练,聚焦一个主题" },
  { value: "20", label: "20 分钟", hint: "默认,覆盖 3 个轮次" },
  { value: "30", label: "30 分钟", hint: "完整体验,含反问" },
];

function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail ?? err.message;
  }
  return err instanceof Error ? err.message : "请求失败";
}

export function ConfigPage(): JSX.Element {
  const navigate = useNavigate();
  const upload = useAppStore((s) => s.upload);
  const config = useAppStore((s) => s.config);
  const patchConfig = useAppStore((s) => s.patchConfig);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    if (!upload.assetBundleId) {
      setError("请先在「上传与解析」里完成简历与 JD 的上传。");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const response = await createSession({
        asset_bundle_id: upload.assetBundleId,
        config: {
          style: config.style,
          direction: config.direction,
          duration_minutes: config.durationMinutes,
        },
      });
      navigate(`/interview/${response.session_id}`);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const ready = Boolean(upload.assetBundleId) && upload.parseStatus === "succeeded";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <div className="eyebrow">03 · 面试配置</div>
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
          选一套和今天状态匹配的面试方式
        </h1>
        <p style={{ fontSize: 14, color: "var(--ink-500)", maxWidth: 620, lineHeight: 1.6 }}>
          AI 会根据你选择的风格、方向和时长生成专属的面试框架,开始后无法中途修改。
        </p>
      </div>

      {!ready ? (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "var(--r-md)",
            background: "var(--warn-softer)",
            color: "var(--warn)",
            border: "1px solid var(--warn)",
            fontSize: 13,
          }}
        >
          请先在「上传与解析」完成 AI 解析,然后再来配置面试。
        </div>
      ) : null}

      <TileGroup
        title="面试风格"
        description="影响 AI 面试官的语气与追问强度。"
        options={STYLE_OPTIONS}
        value={config.style}
        onChange={(value) => patchConfig({ style: value })}
      />

      <TileGroup
        title="面试方向"
        description="决定 AI 把重心放在哪里。"
        options={DIRECTION_OPTIONS}
        value={config.direction}
        onChange={(value) => patchConfig({ direction: value })}
      />

      <TileGroup
        title="期望时长"
        description="会按比例切分各环节(暖场/深挖/反问)。"
        options={DURATION_OPTIONS}
        value={String(config.durationMinutes)}
        onChange={(value) => patchConfig({ durationMinutes: Number(value) })}
      />

      {error ? (
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
          {error}
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 12 }}>
        <button
          type="button"
          onClick={() => navigate("/upload")}
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
          返回上传
        </button>
        <button
          type="button"
          onClick={handleStart}
          disabled={!ready || submitting}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "11px 22px",
            borderRadius: "var(--r-md)",
            border: "none",
            background: ready && !submitting ? "var(--brand)" : "var(--ink-200)",
            color: "white",
            fontSize: 14,
            fontWeight: 500,
            cursor: ready && !submitting ? "pointer" : "not-allowed",
          }}
        >
          {submitting ? <Loader2 size={14} className="spin" /> : null}
          {submitting ? "生成面试框架..." : "开始面试"}
        </button>
      </div>
    </div>
  );
}

interface TileGroupProps<T extends string> {
  title: string;
  description: string;
  options: TileOption<T>[];
  value: T;
  onChange: (next: T) => void;
}

function TileGroup<T extends string>({
  title,
  description,
  options,
  value,
  onChange,
}: TileGroupProps<T>): JSX.Element {
  return (
    <section
      className="ds-card"
      style={{
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <header style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <h2
          style={{
            margin: 0,
            fontSize: 15,
            fontWeight: 600,
            color: "var(--ink-900)",
          }}
        >
          {title}
        </h2>
        <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-500)" }}>
          {description}
        </p>
      </header>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 10,
        }}
      >
        {options.map((option) => {
          const selected = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              style={{
                textAlign: "left",
                padding: "14px 16px",
                borderRadius: "var(--r-md)",
                border: `1.5px solid ${selected ? "var(--brand)" : "var(--line)"}`,
                background: selected ? "var(--brand-softer)" : "var(--bg-elev)",
                color: "var(--ink-900)",
                cursor: "pointer",
                transition: "border-color 120ms ease, background 120ms ease",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <span
                style={{
                  fontSize: 13.5,
                  fontWeight: 600,
                  color: selected ? "var(--brand-ink)" : "var(--ink-900)",
                }}
              >
                {option.label}
              </span>
              <span style={{ fontSize: 12, color: "var(--ink-500)", lineHeight: 1.5 }}>
                {option.hint}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
