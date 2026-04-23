import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAppSetting } from "@/api/appSettings";

const ONBOARDING_KEY = "onboarding_completed_at";

function Shimmer(): JSX.Element {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <div
        style={{
          width: 220,
          height: 12,
          borderRadius: "var(--r-pill)",
          background:
            "linear-gradient(90deg, var(--bg-sunken) 0%, var(--line) 50%, var(--bg-sunken) 100%)",
          backgroundSize: "200% 100%",
          animation: "eatit-shimmer 1.4s ease-in-out infinite",
        }}
      />
    </div>
  );
}

export function OnboardingGate(): JSX.Element {
  const location = useLocation();
  const query = useQuery({
    queryKey: ["app-settings", ONBOARDING_KEY],
    queryFn: () => getAppSetting<string>(ONBOARDING_KEY),
    staleTime: Infinity,
    retry: false,
  });

  if (query.isLoading) return <Shimmer />;

  // If the backend is unreachable, don't trap the user on a shimmer — let them in.
  // The wizard will be available from the sidebar later; first-run redirect only
  // happens when we definitively know the setting is absent.
  if (query.isError) return <Outlet />;

  if (query.data == null) {
    return <Navigate to="/onboarding" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
