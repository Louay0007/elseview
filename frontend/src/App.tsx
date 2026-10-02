import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import AuthFlow from "./pages/auth/AuthFlow";
import CompleteProfile from "./pages/auth/CompleteProfile";
import TesterOnboarding from "./pages/auth/TesterOnboarding";
import Account from "./pages/workspace/Account";
import Notifications from "./pages/workspace/Notifications";
import Refer from "./pages/workspace/Refer";
import Dashboard from "./pages/workspace/Dashboard";
import Analytics from "./pages/workspace/Analytics";
import History from "./pages/workspace/History";
import Billing from "./pages/workspace/Billing";
import BuyCredits from "./pages/workspace/BuyCredits";
import Credits from "./pages/workspace/Credits";
import Settings from "./pages/workspace/Settings";
import StudyEditor from "./pages/workspace/StudyEditor";
import Recruit from "./pages/workspace/Recruit";
import Publish from "./pages/workspace/Publish";
import Reviews from "./pages/workspace/Reviews";
import ReportDetail from "./pages/workspace/ReportDetail";
import RunnerPreview from "./pages/workspace/RunnerPreview";
import TesterDashboard from "./pages/tester/Dashboard";
import TesterStudies from "./pages/tester/Studies";
import TesterRunner from "./pages/tester/Runner";
import TesterSessions from "./pages/tester/Sessions";
import TesterTestHistory from "./pages/tester/TestHistory";
import TesterNotifications from "./pages/tester/Notifications";
import TesterEarnings from "./pages/tester/Earnings";
import TesterProfile from "./pages/tester/Profile";
import { AuthLocaleProvider } from "./components/auth/AuthLocale";
import { WorkspaceProvider } from "./components/workspace/WorkspaceContext";
import LegalNotice, { legalPages } from "./pages/legal/LegalNotice";
import { routes } from "@/lib/routes";

const App = () => (
  <TooltipProvider>
    <Toaster />
    <Sonner />
    <BrowserRouter>
      <AuthLocaleProvider>
        <WorkspaceProvider>
          <Routes>
            <Route path={routes.landing} element={<Index />} />

            {/* Authentication. Each mode mounts AuthFlow with its own key so a
                refresh or a shared link always lands on the right step. */}
            <Route path={routes.login} element={<AuthFlow key="login" mode="login" />} />
            <Route path={routes.signup} element={<AuthFlow key="signup" mode="signup" />} />
            <Route path={routes.verifyEmail} element={<AuthFlow key="verify" mode="verify" />} />
            <Route path={routes.recover} element={<AuthFlow key="recover" mode="recover" />} />
            <Route path={routes.resetPassword} element={<AuthFlow key="reset" mode="reset" />} />
            <Route path={routes.invitation} element={<AuthFlow key="invitation" mode="invitation" />} />
            <Route path={routes.completeProfile} element={<CompleteProfile />} />

            {/* Legal copy. Both shells link to these, so the destinations exist
                rather than falling through to the not-found page. */}
            <Route path={routes.terms} element={<LegalNotice slug="terms" {...legalPages.terms} />} />
            <Route path={routes.privacy} element={<LegalNotice slug="privacy" {...legalPages.privacy} />} />

            {/* Researcher workspace. */}
            <Route path={routes.dashboard} element={<Dashboard />} />
            <Route path={routes.newStudy} element={<StudyEditor />} />
            <Route path="/studies/:studyId/edit" element={<StudyEditor />} />
            <Route path={routes.recruit} element={<Recruit />} />
            <Route path={routes.publish} element={<Publish />} />
            <Route path={routes.reviews} element={<Reviews />} />
            <Route path="/reports/:reportId" element={<ReportDetail />} />
            <Route path={routes.preview} element={<RunnerPreview />} />
            <Route path={routes.analytics} element={<Analytics />} />
            <Route path={routes.history} element={<History />} />
            <Route path={routes.account} element={<Account />} />
            <Route path={routes.accountNotifications} element={<Notifications />} />
            <Route path={routes.accountRefer} element={<Refer />} />
            <Route path={routes.settings} element={<Settings />} />
            <Route path={routes.billing} element={<Billing />} />
            <Route path={routes.credits} element={<Credits />} />
            <Route path={routes.buyCredits} element={<BuyCredits />} />

            {/* Tester space. A tester must never reach a researcher page that
                manages studies, credits, reports or billing. */}
            <Route path={routes.testerOnboarding} element={<TesterOnboarding />} />
            <Route path={routes.tester} element={<TesterDashboard />} />
            <Route path={routes.testerStudies} element={<TesterStudies />} />
            <Route path={routes.testerRunner} element={<TesterRunner />} />
            <Route path={routes.testerSessions} element={<TesterSessions />} />
            <Route path={routes.testerHistory} element={<TesterTestHistory />} />
            <Route path={routes.testerNotifications} element={<TesterNotifications />} />
            <Route path={routes.testerEarnings} element={<TesterEarnings />} />
            <Route path={routes.testerProfile} element={<TesterProfile />} />

            {/* Legacy aliases, so an old bookmark or shared link still lands
                somewhere sensible instead of the not-found page. */}
            <Route path="/login" element={<Navigate to={routes.login} replace />} />
            <Route path="/signup" element={<Navigate to={routes.signup} replace />} />
            <Route path="/mfa" element={<Navigate to={routes.login} replace />} />
            <Route path="/auth/mfa" element={<Navigate to={routes.login} replace />} />
            <Route path="/auth/enroll-mfa" element={<Navigate to={routes.login} replace />} />
            <Route path="/studies/create" element={<Navigate to={routes.newStudy} replace />} />
            <Route path="/study-preview" element={<Navigate to={routes.preview} replace />} />
            <Route path="/terms" element={<Navigate to={routes.terms} replace />} />
            <Route path="/privacy" element={<Navigate to={routes.privacy} replace />} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </WorkspaceProvider>
      </AuthLocaleProvider>
    </BrowserRouter>
  </TooltipProvider>
);

export default App;
