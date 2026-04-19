import { useParams } from "react-router-dom";
import { PageShell } from "@/pages/page-shell";

export function ReportPage(): JSX.Element {
  const { sessionId = "unknown" } = useParams<{ sessionId: string }>();

  return (
    <PageShell
      title="Interview Report"
      description={`Placeholder route for report view ${sessionId}.`}
      routePath={`/report/${sessionId}`}
    />
  );
}
