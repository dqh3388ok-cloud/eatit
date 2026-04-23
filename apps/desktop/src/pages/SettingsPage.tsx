import { useEffect, useMemo, useState } from "react";
import { getAppSetting, putAppSetting } from "@/api/appSettings";
import { fetchASRHealth } from "@/api/asr";
import { ProviderSelect } from "@/pages/settings/ProviderSelect";
import { KeyInput } from "@/pages/settings/KeyInput";
import { TestConnectionButton } from "@/pages/settings/TestConnectionButton";
import { DataManagement } from "@/pages/settings/DataManagement";
import { loadLLMConfig, type LLMConfig, type LLMProvider } from "@/lib/llm/config";
import { getProvider, PROVIDERS } from "@/lib/llm/providers";

type InterviewInputMode = "voice" | "text";

const DEFAULT_PROVIDER: LLMProvider = "siliconflow";

function initialConfig(): LLMConfig {
  const preset = getProvider(DEFAULT_PROVIDER);
  return {
    provider: preset.id,
    api_key: "",
    model: preset.models[0] ?? "",
    base_url: preset.baseUrl || null,
  };
}

const fieldStyle: React.CSSProperties = {
  width: "100%",
  height: 40,
  padding: "0 12px",
  borderRadius: "var(--r-md)",
  border: "1px solid var(--line)",
  background: "var(--bg-elev)",
  color: "var(--ink-900)",
  fontSize: 13.5,
  fontFamily: "var(--f-sans)",
};

export function SettingsPage(): JSX.Element {
  const [config, setConfig] = useState<LLMConfig>(() => initialConfig());
  const [hydrated, setHydrated] = useState(false);
  const preset = useMemo(() => getProvider(config.provider), [config.provider]);

  useEffect(() => {
    let mounted = true;
    loadLLMConfig()
      .then((existing) => {
        if (!mounted) return;
        if (existing) setConfig(existing);
      })
      .catch(() => {
        /* keychain unavailable in dev shell — keep defaults */
      })
      .finally(() => {
        if (mounted) setHydrated(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleProviderChange = (next: typeof preset) => {
    setConfig((prev) => ({
      provider: next.id,
      api_key: prev.api_key,
      model: next.models[0] ?? prev.model,
      base_url: next.baseUrl || null,
    }));
  };

  const suggestedModels = PROVIDERS.find((p) => p.id === config.provider)?.models ?? [];
  const showCustomModel =
    config.provider === "custom" || !suggestedModels.includes(config.model);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <div>
        <div className="eyebrow">07 · 设置</div>
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
          LLM 配置 · 数据管理
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "var(--ink-500)",
            maxWidth: 620,
            lineHeight: 1.6,
          }}
        >
          所有调用都通过本地后端中转,你的 API Key 只会保存在 macOS
          钥匙串中,不会写入日志或同步到任何服务器。
        </p>
      </div>

      <section
        className="ds-card"
        style={{ padding: 24, display: "flex", flexDirection: "column", gap: 18 }}
      >
        <header style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <h2
            style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--ink-900)" }}
          >
            BYOK · 模型提供方
          </h2>
          <p style={{ margin: 0, fontSize: 13, color: "var(--ink-500)" }}>
            自带 API Key(Bring Your Own Key)。选择 Provider 并测试连接后即可开始使用。
          </p>
        </header>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 16,
          }}
        >
          <ProviderSelect value={config.provider} onChange={handleProviderChange} />

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink-700)" }}>
              Base URL {config.provider === "custom" ? "(必填)" : "(可选覆盖)"}
            </span>
            <input
              type="text"
              value={config.base_url ?? ""}
              onChange={(e) =>
                setConfig((c) => ({ ...c, base_url: e.target.value || null }))
              }
              placeholder={preset.baseUrl || "https://api.example.com/v1"}
              style={fieldStyle}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink-700)" }}>
              模型名称
            </span>
            {showCustomModel ? (
              <input
                type="text"
                value={config.model}
                onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))}
                placeholder="例如 gpt-4o-mini"
                style={fieldStyle}
              />
            ) : (
              <select
                value={config.model}
                onChange={(e) => setConfig((c) => ({ ...c, model: e.target.value }))}
                style={fieldStyle}
              >
                {suggestedModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            )}
          </label>
        </div>

        <KeyInput
          value={config.api_key}
          onChange={(next) => setConfig((c) => ({ ...c, api_key: next }))}
        />

        {preset.registerUrl ? (
          <div style={{ fontSize: 12.5, color: "var(--ink-500)" }}>
            没有密钥?前往{" "}
            <a
              href={preset.registerUrl}
              target="_blank"
              rel="noreferrer"
              style={{ color: "var(--brand)", textDecoration: "underline" }}
            >
              {preset.label}
            </a>{" "}
            注册。{preset.hint}
          </div>
        ) : preset.hint ? (
          <div style={{ fontSize: 12.5, color: "var(--ink-500)" }}>{preset.hint}</div>
        ) : null}

        <TestConnectionButton
          config={config}
          disabled={!hydrated}
        />
      </section>

      <InterviewExperienceSection />

      <DataManagement />
    </div>
  );
}

function InterviewExperienceSection(): JSX.Element {
  const [observerEnabled, setObserverEnabled] = useState<boolean>(true);
  const [observerHydrated, setObserverHydrated] = useState(false);
  const [observerSaving, setObserverSaving] = useState(false);
  const [observerError, setObserverError] = useState<string | null>(null);

  const [inputMode, setInputMode] = useState<InterviewInputMode>("voice");
  const [modeHydrated, setModeHydrated] = useState(false);
  const [modeSaving, setModeSaving] = useState(false);
  const [modeError, setModeError] = useState<string | null>(null);
  const [asrAvailable, setAsrAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    getAppSetting<boolean>("observer_panel_enabled")
      .then((value) => {
        if (!mounted) return;
        setObserverEnabled(value === null || value === undefined ? true : Boolean(value));
      })
      .catch(() => {
        /* backend unavailable — default to on */
      })
      .finally(() => {
        if (mounted) setObserverHydrated(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    getAppSetting<InterviewInputMode>("interview_input_mode")
      .then((value) => {
        if (!mounted) return;
        setInputMode(value === "text" ? "text" : "voice");
      })
      .catch(() => {
        /* backend unavailable — default to voice */
      })
      .finally(() => {
        if (mounted) setModeHydrated(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    fetchASRHealth()
      .then((health) => {
        if (mounted) setAsrAvailable(Boolean(health.available));
      })
      .catch(() => {
        if (mounted) setAsrAvailable(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleObserverToggle = async () => {
    const next = !observerEnabled;
    setObserverEnabled(next);
    setObserverError(null);
    setObserverSaving(true);
    try {
      await putAppSetting<boolean>("observer_panel_enabled", next);
    } catch (err) {
      setObserverEnabled(!next);
      setObserverError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setObserverSaving(false);
    }
  };

  const handleModeChange = async (next: InterviewInputMode) => {
    if (next === inputMode) return;
    const prev = inputMode;
    setInputMode(next);
    setModeError(null);
    setModeSaving(true);
    try {
      await putAppSetting<InterviewInputMode>("interview_input_mode", next);
    } catch (err) {
      setInputMode(prev);
      setModeError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setModeSaving(false);
    }
  };

  const voiceDisabledByBackend = asrAvailable === false;

  return (
    <section
      className="ds-card"
      style={{ padding: 24, display: "flex", flexDirection: "column", gap: 18 }}
    >
      <header style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <h2
          style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--ink-900)" }}
        >
          面试体验
        </h2>
        <p style={{ margin: 0, fontSize: 13, color: "var(--ink-500)" }}>
          控制实时面试页的附加提示。这些开关只影响 UI,不改变面试评估本身。
        </p>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontSize: 13.5, fontWeight: 500, color: "var(--ink-900)" }}>
            面试语音模式
          </span>
          <span style={{ fontSize: 12, color: "var(--ink-500)", lineHeight: 1.6 }}>
            语音模式下,按住「按住说话」即可录音,AI 会实时显示字幕并自动生成答案。
            文字模式则沿用文本框输入。
          </span>
        </div>
        <div
          role="radiogroup"
          aria-label="面试语音模式"
          style={{
            display: "inline-flex",
            alignSelf: "flex-start",
            padding: 3,
            gap: 2,
            borderRadius: "var(--r-pill)",
            background: "var(--bg-sunken)",
            border: "1px solid var(--line)",
            opacity: modeHydrated && !modeSaving ? 1 : 0.7,
          }}
        >
          {(["voice", "text"] as const).map((value) => {
            const selected = inputMode === value;
            const optionDisabled =
              value === "voice" ? voiceDisabledByBackend : false;
            const effectiveDisabled =
              !modeHydrated || modeSaving || (optionDisabled && !selected);
            return (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={selected}
                disabled={effectiveDisabled}
                onClick={() => {
                  void handleModeChange(value);
                }}
                style={{
                  padding: "6px 14px",
                  borderRadius: "var(--r-pill)",
                  border: "none",
                  background: selected ? "var(--bg-elev)" : "transparent",
                  color: selected ? "var(--ink-900)" : "var(--ink-500)",
                  fontSize: 12.5,
                  fontWeight: selected ? 500 : 400,
                  cursor: effectiveDisabled ? "not-allowed" : "pointer",
                  boxShadow: selected ? "var(--shadow-xs)" : "none",
                }}
              >
                {value === "voice" ? "语音" : "文字"}
              </button>
            );
          })}
        </div>

        {voiceDisabledByBackend ? (
          <div
            style={{
              fontSize: 12,
              color: "var(--warn)",
              background: "var(--warn-softer)",
              border: "1px solid var(--warn)",
              padding: "8px 12px",
              borderRadius: "var(--r-sm)",
              lineHeight: 1.6,
            }}
          >
            ⚠️ 服务端未配置 Azure Speech,语音模式不可用。请参考 README 在
            <span className="mono"> .env </span>中补上
            <span className="mono"> AZURE_SPEECH_KEY </span>
            和
            <span className="mono"> AZURE_SPEECH_REGION </span>
            后重启后端。
          </div>
        ) : null}

        {modeError ? (
          <div
            style={{
              fontSize: 12,
              color: "var(--warn)",
              background: "var(--warn-soft)",
              padding: "8px 12px",
              borderRadius: "var(--r-sm)",
            }}
          >
            {modeError}
          </div>
        ) : null}
      </div>

      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "10px 0",
          cursor: observerHydrated && !observerSaving ? "pointer" : "not-allowed",
        }}
      >
        <input
          type="checkbox"
          role="switch"
          checked={observerEnabled}
          disabled={!observerHydrated || observerSaving}
          onChange={handleObserverToggle}
          style={{ width: 18, height: 18, cursor: "inherit" }}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontSize: 13.5, fontWeight: 500, color: "var(--ink-900)" }}>
            AI 观察侧栏
          </span>
          <span style={{ fontSize: 12, color: "var(--ink-500)", lineHeight: 1.6 }}>
            每轮作答完,AI 会在右侧给一句 ≤ 60 字的轻量反馈。关掉则不显示侧栏。
          </span>
        </div>
      </label>

      {observerError ? (
        <div
          style={{
            fontSize: 12,
            color: "var(--warn)",
            background: "var(--warn-soft)",
            padding: "8px 12px",
            borderRadius: "var(--r-sm)",
          }}
        >
          {observerError}
        </div>
      ) : null}
    </section>
  );
}
