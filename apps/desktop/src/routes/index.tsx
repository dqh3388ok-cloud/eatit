import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { OnboardingGate } from "@/components/OnboardingGate";
import { ConfigPage } from "@/pages/ConfigPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { HomePage } from "@/pages/HomePage";
import { InterviewPage } from "@/pages/InterviewPage";
import { MetaReportListPage } from "@/pages/MetaReportListPage";
import { MetaReportPage } from "@/pages/MetaReportPage";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { ReportPage } from "@/pages/ReportPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { UploadPage } from "@/pages/UploadPage";

export function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route element={<OnboardingGate />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/interview" element={<InterviewPage />} />
          <Route path="/interview/:sessionId" element={<InterviewPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/report/:sessionId" element={<ReportPage />} />
          <Route path="/meta-reports" element={<MetaReportListPage />} />
          <Route path="/meta-report/:id" element={<MetaReportPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
