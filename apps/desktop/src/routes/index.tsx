import { Navigate, Route, Routes } from "react-router-dom";
import { ConfigPage } from "@/pages/ConfigPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { HomePage } from "@/pages/HomePage";
import { InterviewPage } from "@/pages/InterviewPage";
import { ReportPage } from "@/pages/ReportPage";
import { UploadPage } from "@/pages/UploadPage";

export function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/config" element={<ConfigPage />} />
      <Route path="/interview/:sessionId" element={<InterviewPage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/report/:sessionId" element={<ReportPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
