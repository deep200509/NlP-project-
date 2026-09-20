import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import ComingSoon from "./pages/ComingSoon.jsx";
import Dashboard from "./pages/Dashboard.jsx";

// Pages inside <Protected> can only be opened after logging in.
function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="splash">Loading…</p>;
  return user ? children : <Navigate to="/login" replace />;
}

function GuestOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="splash">Loading…</p>;
  return user ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><AuthPage mode="login" /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><AuthPage mode="register" /></GuestOnly>} />

      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/new-api" element={<ComingSoon title="New API" />} />
        <Route path="/chat/:conversationId" element={<ComingSoon title="Chat" />} />
        <Route path="/projects" element={<ComingSoon title="My projects" />} />
        <Route path="/projects/:projectId" element={<ComingSoon title="Project" />} />
        <Route path="/history" element={<ComingSoon title="Chat history" />} />
        <Route path="/settings" element={<ComingSoon title="Settings" />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}