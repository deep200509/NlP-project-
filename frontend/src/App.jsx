import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import Chat from "./pages/Chat.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import History from "./pages/History.jsx";
import ProjectDetail from "./pages/ProjectDetail.jsx";
import Projects from "./pages/Projects.jsx";
import Settings from "./pages/Settings.jsx";

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
        <Route path="/new-api" element={<Chat />} />
        <Route path="/chat/:conversationId" element={<Chat />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:projectId" element={<ProjectDetail />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}