import { create } from "zustand";

export type ConnectivityState = "online" | "reconnecting" | "offline";

interface ConnectivityStore {
  state: ConnectivityState;
  detail: string | null;
  set(state: ConnectivityState, detail?: string | null): void;
}

/**
 * Cross-component connectivity indicator. InterviewPage flips it to
 * "reconnecting" / "offline" during WS outages; Topbar renders a
 * green / amber / red dot sourced from this store.
 */
export const useConnectivityStore = create<ConnectivityStore>((set) => ({
  state: "online",
  detail: null,
  set(state, detail = null) {
    set({ state, detail });
  },
}));
