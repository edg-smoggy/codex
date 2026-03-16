import { FormEvent, useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";

import { useAuthStore } from "../../stores/authStore";

type AuthMode = "admin_login" | "member_login" | "register";

export function AuthPanel() {
  const [mode, setMode] = useState<AuthMode>("admin_login");
  const [inviteCode, setInviteCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const auth = useAuthStore(
    useShallow((state) => ({
      loading: state.loading,
      error: state.error,
      loginWithPassword: state.loginWithPassword,
      registerWithInvite: state.registerWithInvite,
    })),
  );

  const submitLabel = useMemo(() => {
    if (auth.loading) return "处理中...";
    return mode === "register" ? "注册并登录" : "登录";
  }, [auth.loading, mode]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (mode === "register") {
      await auth.registerWithInvite(inviteCode, username, password);
      return;
    }

    await auth.loginWithPassword(username, password, mode === "admin_login" ? "admin" : "member");
  };

  return (
    <div className="auth-screen">
      <div className="auth-card-pro">
        <div className="auth-logo-row">
          <div className="logo-icon">H</div>
          <span className="logo-text">AI Hub</span>
        </div>

        <h1 className="auth-title">多模型智能助手</h1>
        <p className="auth-subtitle">管理员使用管理员登录，成员首次使用请通过邀请码注册。</p>

        <div className="auth-tabs" role="tablist" aria-label="auth mode">
          <button
            type="button"
            className={mode === "admin_login" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("admin_login")}
          >
            管理员登录
          </button>
          <button
            type="button"
            className={mode === "member_login" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("member_login")}
          >
            成员登录
          </button>
          <button
            type="button"
            className={mode === "register" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("register")}
          >
            成员注册
          </button>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          {mode === "register" ? (
            <label>
              邀请码
              <input
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                placeholder="AIHUB-2025-INVITE"
                required
              />
            </label>
          ) : null}

          <label>
            用户名
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              minLength={3}
              required
            />
          </label>

          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 8 位"
              minLength={8}
              required
            />
          </label>

          {auth.error ? <div className="error-box">{auth.error}</div> : null}

          <button type="submit" className="new-chat-btn" disabled={auth.loading}>
            {submitLabel}
          </button>
        </form>
      </div>
    </div>
  );
}
