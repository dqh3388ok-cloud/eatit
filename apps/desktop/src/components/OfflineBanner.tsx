import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";
import { apiClient } from "@/api/client";

const HEARTBEAT_INTERVAL_MS = 20_000;
const HEARTBEAT_TIMEOUT_MS = 4_000;

/**
 * Tracks connectivity via two signals:
 *   - navigator.onLine / "online"+"offline" events (cheap, immediate).
 *   - A 20s heartbeat GET /health against the local backend (covers the
 *     case where the machine is online but the FastAPI server crashed).
 *
 * When either signal reports down, render a sticky banner above page
 * content. The banner self-heals as soon as connectivity returns.
 */
export function OfflineBanner(): JSX.Element | null {
  const [browserOnline, setBrowserOnline] = useState<boolean>(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  const [backendReachable, setBackendReachable] = useState<boolean>(true);

  useEffect(() => {
    const onOnline = () => setBrowserOnline(true);
    const onOffline = () => setBrowserOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function ping() {
      try {
        await apiClient.get("/health", { timeout: HEARTBEAT_TIMEOUT_MS });
        if (!cancelled) setBackendReachable(true);
      } catch {
        if (!cancelled) setBackendReachable(false);
      }
    }
    void ping();
    const handle = window.setInterval(ping, HEARTBEAT_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  const online = browserOnline && backendReachable;
  if (online) return null;

  return (
    <div
      role="alert"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        background: "var(--warn-softer)",
        borderBottom: "1px solid var(--warn)",
        color: "var(--warn)",
        padding: "8px 16px",
        fontSize: 12.5,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <WifiOff size={14} />
      {browserOnline
        ? "无法连接本地后端服务,请尝试重新启动 Eatit。"
        : "设备当前离线,后台请求将暂停。"}
    </div>
  );
}
