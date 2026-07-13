import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AuthProvider } from "../auth/auth-store";
import { AppLayout } from "../components/layouts/AppLayout";
import { AuthLayout } from "../components/layouts/AuthLayout";
import { GuestOnlyRoute } from "../components/routing/GuestOnlyRoute";
import { ProtectedRoute } from "../components/routing/ProtectedRoute";
import { ThemeProvider } from "../components/ui/ThemeProvider";
import { ToastProvider } from "../components/ui/ToastProvider";
import { AdminDashboardPage } from "../pages/app/AdminDashboardPage";
import { AdminEscalationContactsPage } from "../pages/app/AdminEscalationContactsPage";
import { AdminEscalationsPage } from "../pages/app/AdminEscalationsPage";
import { AdminProviderHealthPage, AdminSystemHealthPage } from "../pages/app/AdminHealthPages";
import { AdminIntelligenceSourcesPage } from "../pages/app/AdminIntelligenceSourcesPage";
import { AdminKnowledgePage } from "../pages/app/AdminKnowledgePage";
import { AdminUsersPage } from "../pages/app/AdminUsersPage";
import { FarmCreatePage } from "../pages/app/FarmCreatePage";
import { ChatPage } from "../pages/app/ChatPage";
import { EscalationsPage } from "../pages/app/EscalationsPage";
import { FarmDetailPage } from "../pages/app/FarmDetailPage";
import { FarmDiagnosisPage } from "../pages/app/FarmDiagnosisPage";
import { FarmEditPage } from "../pages/app/FarmEditPage";
import { FarmIntelligenceSectionPage } from "../pages/app/FarmIntelligenceSectionPage";
import { FarmListPage } from "../pages/app/FarmListPage";
import { FarmRecommendationsPage } from "../pages/app/FarmRecommendationsPage";
import { FarmStagePage } from "../pages/app/FarmStagePage";
import { FarmTimelinePage } from "../pages/app/FarmTimelinePage";
import { FarmWeatherPage } from "../pages/app/FarmWeatherPage";
import { DiagnosisResultPage } from "../pages/app/DiagnosisResultPage";
import { KnowledgeSearchPage } from "../pages/app/KnowledgeSearchPage";
import { NotificationsPage } from "../pages/app/NotificationsPage";
import { ProfilePage } from "../pages/app/ProfilePage";
import { SettingsPage } from "../pages/app/SettingsPage";
import { WorkspacePage } from "../pages/app/WorkspacePage";
import { LoginPage } from "../pages/auth/LoginPage";
import { SignupPage } from "../pages/auth/SignupPage";
import { NotFoundPage } from "../pages/system/NotFoundPage";
import { RootRedirect } from "../pages/system/RootRedirect";

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<RootRedirect />} />

              <Route element={<GuestOnlyRoute />}>
                <Route element={<AuthLayout />}>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/signup" element={<SignupPage />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/app" element={<WorkspacePage />} />
                  <Route path="/app/admin" element={<AdminDashboardPage />} />
                  <Route path="/app/admin/users" element={<AdminUsersPage />} />
                  <Route path="/app/admin/knowledge" element={<AdminKnowledgePage />} />
                  <Route
                    path="/app/admin/intelligence-sources"
                    element={<AdminIntelligenceSourcesPage />}
                  />
                  <Route
                    path="/app/admin/escalation-contacts"
                    element={<AdminEscalationContactsPage />}
                  />
                  <Route path="/app/admin/escalations" element={<AdminEscalationsPage />} />
                  <Route
                    path="/app/admin/provider-health"
                    element={<AdminProviderHealthPage />}
                  />
                  <Route path="/app/admin/system-health" element={<AdminSystemHealthPage />} />
                  <Route path="/app/chat" element={<ChatPage />} />
                  <Route path="/app/notifications" element={<NotificationsPage />} />
                  <Route path="/app/profile" element={<ProfilePage />} />
                  <Route path="/app/settings" element={<SettingsPage />} />
                  <Route path="/app/knowledge" element={<KnowledgeSearchPage />} />
                  <Route path="/app/escalations" element={<EscalationsPage />} />
                  <Route path="/app/contact-expert" element={<EscalationsPage />} />
                  <Route path="/app/farms" element={<FarmListPage />} />
                  <Route path="/app/farms/new" element={<FarmCreatePage />} />
                  <Route path="/app/farms/:farmId" element={<FarmDetailPage />} />
                  <Route path="/app/farms/:farmId/weather" element={<FarmWeatherPage />} />
                  <Route
                    path="/app/farms/:farmId/advisories"
                    element={<FarmIntelligenceSectionPage kind="advisories" />}
                  />
                  <Route
                    path="/app/farms/:farmId/news"
                    element={<FarmIntelligenceSectionPage kind="news" />}
                  />
                  <Route
                    path="/app/farms/:farmId/market"
                    element={<FarmIntelligenceSectionPage kind="market" />}
                  />
                  <Route
                    path="/app/farms/:farmId/soil"
                    element={<FarmIntelligenceSectionPage kind="soil" />}
                  />
                  <Route
                    path="/app/farms/:farmId/stage-advisory"
                    element={<FarmStagePage />}
                  />
                  <Route
                    path="/app/farms/:farmId/recommendations"
                    element={<FarmRecommendationsPage />}
                  />
                  <Route path="/app/farms/:farmId/timeline" element={<FarmTimelinePage />} />
                  <Route path="/app/farms/:farmId/diagnosis" element={<FarmDiagnosisPage />} />
                  <Route
                    path="/app/farms/:farmId/diagnoses/:diagnosisId"
                    element={<DiagnosisResultPage />}
                  />
                  <Route path="/app/farms/:farmId/edit" element={<FarmEditPage />} />
                </Route>
              </Route>

              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
