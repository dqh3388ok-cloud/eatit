import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

export function AppShell(): JSX.Element {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "240px 1fr",
        minHeight: "100vh",
      }}
    >
      <Sidebar />
      <main style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar />
        <div
          style={{
            padding: "32px 40px 80px",
            maxWidth: 1280,
            width: "100%",
            margin: "0 auto",
          }}
        >
          <Outlet />
        </div>
      </main>
    </div>
  );
}
