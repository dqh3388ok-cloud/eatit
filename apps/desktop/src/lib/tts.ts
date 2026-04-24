/**
 * Interviewer text-to-speech via the WebKit-bundled Web Speech API.
 *
 * We use SpeechSynthesis rather than OpenAI's /v1/audio/speech route because
 * - zero network latency on cold-start (macOS ships zh voices out of the box)
 * - zero marginal cost to the BYOK user
 * - zero new backend deps; keeps the bundled DMG lean
 *
 * Tradeoff: macOS's stock Mandarin voices sound robotic. If later we want
 * higher fidelity we can gate behind a "HD voice" toggle that calls the
 * provider's TTS endpoint and streams an <audio> tag.
 */

const ZH_LOCALES = /^zh(-|_|$)/i;

function pickZhVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;
  // Prefer premium / neural voices if the OS reports them.
  const zhVoices = voices.filter((v) => ZH_LOCALES.test(v.lang));
  if (zhVoices.length === 0) return null;
  const premium = zhVoices.find((v) => /premium|enhanced|neural/i.test(v.name));
  return premium ?? zhVoices[0];
}

/**
 * Speak `text` as the interviewer. Cancels any previous utterance so two
 * adjacent calls (e.g. rapid question switches) don't queue up and overlap.
 */
export function speakInterviewerLine(text: string): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  const trimmed = text.trim();
  if (!trimmed) return;

  const synth = window.speechSynthesis;
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(trimmed);
  const voice = pickZhVoice();
  if (voice) {
    utterance.voice = voice;
    utterance.lang = voice.lang;
  } else {
    utterance.lang = "zh-CN";
  }
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  // Safari/WKWebView populates voices asynchronously on cold start; if the
  // list was empty on the first call it'll be populated by the time the
  // `voiceschanged` event fires. Re-pick on the next tick to avoid silent
  // fallback to the system default English voice.
  if (!voice) {
    const onVoicesReady = () => {
      synth.removeEventListener("voiceschanged", onVoicesReady);
      const late = pickZhVoice();
      if (late) {
        synth.cancel();
        const retry = new SpeechSynthesisUtterance(trimmed);
        retry.voice = late;
        retry.lang = late.lang;
        synth.speak(retry);
      }
    };
    synth.addEventListener("voiceschanged", onVoicesReady);
  }

  synth.speak(utterance);
}

/** Abort any ongoing or queued utterance. Safe to call when nothing is speaking. */
export function stopInterviewerLine(): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
}
