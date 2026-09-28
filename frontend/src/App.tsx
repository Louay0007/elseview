import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import AuthFlow from "./pages/auth/AuthFlow";
import CompleteProfile from "./pages/auth/CompleteProfile";
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
import TesterEarnings from "./pages/tester/Earnings";
import TesterProfile from "./pages/tester/Profile";
import { AuthLocaleProvider } from "./components/auth/AuthLocale";
import { WorkspaceProvider } from "./components/workspace/WorkspaceContext";

const App = () => (
  <TooltipProvider>
    <Toaster />
    <Sonner />
    <BrowserRouter>
      <AuthLocaleProvider>
        <WorkspaceProvider>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/login" element={<Navigate to="/auth/login" replace />} />
            <Route path="/signup" element={<Navigate to="/auth/signup" replace />} />
            <Route path="/mfa" element={<Navigate to="/auth/login" replace />} />
            <Route path="/auth/login" element={<AuthFlow key="login" mode="login" />} />
            <Route path="/auth/signup" element={<AuthFlow key="signup" mode="signup" />} />
            <Route path="/auth/verify-email" element={<AuthFlow key="verify" mode="verify" />} />
            <Route path="/auth/complete-profile" element={<CompleteProfile />} />
            <Route path="/account" element={<Account />} />
            <Route path="/account/notifications" element={<Notifications />} />
            <Route path="/account/refer" element={<Refer />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/studies/create" element={<StudyEditor />} />
            <Route path="/studies/:studyId/edit" element={<StudyEditor />} />
            <Route path="/recruit" element={<Recruit />} />
            <Route path="/publish" element={<Publish />} />
            <Route path="/reviews" element={<Reviews />} />
            <Route path="/reports/:reportId" element={<ReportDetail />} />
            <Route path="/study-preview" element={<RunnerPreview />} />
            <Route path="/tester" element={<TesterDashboard />} />
            <Route path="/tester/studies" element={<TesterStudies />} />
            <Route path="/tester/runner" element={<TesterRunner />} />
            <Route path="/tester/sessions" element={<TesterSessions />} />
            <Route path="/tester/earnings" element={<TesterEarnings />} />
            <Route path="/tester/profile" element={<TesterProfile />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/history" element={<History />} />
            <Route path="/workspace/billing" element={<Billing />} />
            <Route path="/workspace/credits" element={<Credits />} />
            <Route path="/workspace/credits/buy" element={<BuyCredits />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/auth/recover" element={<AuthFlow key="recover" mode="recover" />} />
            <Route path="/auth/reset-password" element={<AuthFlow key="reset" mode="reset" />} />
            <Route path="/auth/invitation" element={<AuthFlow key="invitation" mode="invitation" />} />
            <Route path="/auth/mfa" element={<Navigate to="/auth/login" replace />} />
            <Route path="/auth/enroll-mfa" element={<Navigate to="/auth/login" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </WorkspaceProvider>
      </AuthLocaleProvider>
    </BrowserRouter>
  </TooltipProvider>
);

export default App;
