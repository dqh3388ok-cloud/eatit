import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { maskApiKey } from "@/lib/llm/masking";

interface Props {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  height: 40,
  padding: "0 44px 0 12px",
  borderRadius: "var(--r-md)",
  border: "1px solid var(--line)",
  background: "var(--bg-elev)",
  color: "var(--ink-900)",
  fontSize: 13.5,
  fontFamily: "var(--f-mono)",
};

export function KeyInput({ value, onChange, placeholder }: Props): JSX.Element {
  const [visible, setVisible] = useState(false);
  const masked = maskApiKey(value);

  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink-700)" }}>
        API Key
      </span>
      <div style={{ position: "relative" }}>
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder ?? "sk-..."}
          autoComplete="off"
          spellCheck={false}
          style={inputStyle}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "隐藏密钥" : "显示密钥"}
          style={{
            position: "absolute",
            right: 8,
            top: "50%",
            transform: "translateY(-50%)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            border: "none",
            background: "transparent",
            color: "var(--ink-500)",
            cursor: "pointer",
          }}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {value ? (
        <span
          className="mono"
          style={{ fontSize: 11.5, color: "var(--ink-400)" }}
        >
          已保存(预览): {masked}
        </span>
      ) : null}
    </label>
  );
}
