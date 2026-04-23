import { Upload } from "lucide-react";

interface Props {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function StepUpload({ onNext, onBack, onSkip }: Props): JSX.Element {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      <div>
        <div className="eyebrow">03 · 上传资料</div>
        <h1
          className="h-serif"
          style={{
            fontSize: 36,
            lineHeight: 1.1,
            fontWeight: 400,
            margin: "12px 0 8px",
            color: "var(--ink-900)",
          }}
        >
          上传第一份简历与 JD(可跳过)
        </h1>
        <p style={{ fontSize: 14, color: "var(--ink-500)", maxWidth: 560, margin: 0 }}>
          这一步只是让你先体验一下 AI
          解析。跳过也完全 OK,之后在「上传与解析」里再补。
        </p>
      </div>

      <div
        style={{
          border: "1.5px dashed var(--line-strong)",
          borderRadius: "var(--r-lg)",
          padding: "36px 24px",
          background: "var(--bg-warm)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: "var(--r-pill)",
            background: "var(--bg-elev)",
            border: "1px solid var(--line)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--ink-500)",
          }}
        >
          <Upload size={20} />
        </div>
        <div style={{ fontSize: 13.5, color: "var(--ink-700)" }}>
          拖拽文件到这里,或点「下一步 / 跳过」稍后上传
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-400)" }}>
          支持 pdf / doc / docx / txt · 完整上传逻辑建设中
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
        <button
          type="button"
          onClick={onBack}
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
          返回
        </button>
        <button
          type="button"
          onClick={onSkip}
          style={{
            padding: "10px 18px",
            borderRadius: "var(--r-md)",
            border: "1px solid var(--line)",
            background: "transparent",
            color: "var(--ink-700)",
            fontSize: 13.5,
            cursor: "pointer",
          }}
        >
          跳过
        </button>
        <button
          type="button"
          onClick={onNext}
          style={{
            padding: "10px 20px",
            borderRadius: "var(--r-md)",
            border: "none",
            background: "var(--brand)",
            color: "white",
            fontSize: 13.5,
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          下一步
        </button>
      </div>
    </div>
  );
}
