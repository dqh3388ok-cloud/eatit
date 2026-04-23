import { useEffect, useRef } from "react";

/**
 * Two-layer caption rendering for voice-mode interviews.
 *
 *   finalTranscript    — committed, ink-900 (reads as the final answer text)
 *   partialTranscript  — in-progress, ink-400 italic (Azure's `recognizing`)
 *
 * Autoscrolls to the bottom as text grows so long answers stay in view.
 */
export function LiveCaption({
  finalTranscript,
  partialTranscript,
}: {
  finalTranscript: string;
  partialTranscript: string;
}): JSX.Element | null {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [finalTranscript, partialTranscript]);

  if (!finalTranscript && !partialTranscript) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      style={{
        padding: "12px 14px",
        borderRadius: "var(--r-md)",
        border: "1px solid var(--line)",
        background: "var(--bg-sunken)",
        maxHeight: 120,
        overflowY: "auto",
        fontSize: 14,
        lineHeight: 1.6,
        whiteSpace: "pre-wrap",
      }}
    >
      {finalTranscript ? (
        <span style={{ color: "var(--ink-900)" }}>{finalTranscript}</span>
      ) : null}
      {finalTranscript && partialTranscript ? <span> </span> : null}
      {partialTranscript ? (
        <span style={{ color: "var(--ink-400)", fontStyle: "italic" }}>
          {partialTranscript}
        </span>
      ) : null}
    </div>
  );
}
