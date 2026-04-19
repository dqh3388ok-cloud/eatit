import { useParams } from "react-router-dom";
import { PageShell } from "@/pages/page-shell";

export function InterviewPage(): JSX.Element {
  const { sessionId = "unknown" } = useParams<{ sessionId: string }>();

  return (
    <PageShell
      title="Realtime Interview"
      description={`Placeholder route for active session ${sessionId}.`}
      routePath={`/interview/${sessionId}`}
    />
  );
}
