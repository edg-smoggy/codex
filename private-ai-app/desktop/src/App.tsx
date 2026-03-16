import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useShallow } from "zustand/react/shallow";

import { AdminPage } from "./pages/AdminPage";
import { AuthPage } from "./pages/AuthPage";
import { ChatPage } from "./pages/ChatPage";
import { useAuthStore } from "./stores/authStore";

function RequireAuth({ children }: { children: JSX.Element }) {
  const bundle = useAuthStore((state) => state.bundle);
  if (!bundle) return <Navigate to="/auth" replace />;
  return children;
}

function RequireAdmin({ children }: { children: JSX.Element }) {
  const bundle = useAuthStore((state) => state.bundle);
  if (!bundle) return <Navigate to="/auth" replace />;
  if (bundle.user.role !== "admin") return <Navigate to="/chat" replace />;
  return children;
}

export default function App() {
  const { hydrated, bundle, init } = useAuthStore(
    useShallow((state) => ({
      hydrated: state.hydrated,
      bundle: state.bundle,
      init: state.init,
    })),
  );

  useEffect(() => {
    init();
  }, [init]);

  if (!hydrated) {
    return <div className="app-loading">加载中...</div>;
  }

  return (
    <Routes>
      <Route path="/auth" element={bundle ? <Navigate to="/chat" replace /> : <AuthPage />} />
      <Route
        path="/chat"
        element={
          <RequireAuth>
            <ChatPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAdmin>
            <AdminPage />
          </RequireAdmin>
        }
      />
      <Route path="*" element={<Navigate to={bundle ? "/chat" : "/auth"} replace />} />
    </Routes>
  );
}
