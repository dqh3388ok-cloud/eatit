import { useState } from "react";
import { StepWelcome } from "@/pages/onboarding/StepWelcome";
import { StepLLM } from "@/pages/onboarding/StepLLM";
import { StepUpload } from "@/pages/onboarding/StepUpload";
import { StepDone } from "@/pages/onboarding/StepDone";

const STEPS = ["欢迎", "LLM 配置", "上传资料", "完成"] as const;

export function OnboardingPage(): JSX.Element {
  const [step, setStep] = useState(0);

  const goTo = (next: number) => setStep(Math.max(0, Math.min(STEPS.length - 1, next)));

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg)",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 720,
          padding: "56px 32px 80px",
          display: "flex",
          flexDirection: "column",
          gap: 28,
        }}
      >
        <ProgressHeader current={step} />

        <main style={{ display: "flex", flexDirection: "column" }}>
          {step === 0 ? <StepWelcome onNext={() => goTo(1)} /> : null}
          {step === 1 ? (
            <StepLLM onNext={() => goTo(2)} onBack={() => goTo(0)} />
          ) : null}
          {step === 2 ? (
            <StepUpload
              onNext={() => goTo(3)}
              onBack={() => goTo(1)}
              onSkip={() => goTo(3)}
            />
          ) : null}
          {step === 3 ? <StepDone onBack={() => goTo(2)} /> : null}
        </main>
      </div>
    </div>
  );
}

function ProgressHeader({ current }: { current: number }): JSX.Element {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div
        className="mono"
        style={{
          fontSize: 11,
          color: "var(--ink-500)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Eatit · Onboarding
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {STEPS.map((label, index) => {
          const done = index < current;
          const active = index === current;
          return (
            <div
              key={label}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <div
                style={{
                  height: 3,
                  borderRadius: 2,
                  background: done || active ? "var(--brand)" : "var(--line)",
                  transition: "background 180ms ease",
                }}
              />
              <div
                style={{
                  fontSize: 11.5,
                  color: active
                    ? "var(--ink-900)"
                    : done
                      ? "var(--brand-ink)"
                      : "var(--ink-400)",
                  fontWeight: active ? 600 : 400,
                }}
              >
                {String(index + 1).padStart(2, "0")} · {label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
