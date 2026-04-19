import { create } from "zustand";

type AppStore = {
  apiBaseUrl: string;
  setApiBaseUrl: (value: string) => void;
};

export const useAppStore = create<AppStore>((set) => ({
  apiBaseUrl: "http://localhost:8000",
  setApiBaseUrl: (value) => set({ apiBaseUrl: value }),
}));
