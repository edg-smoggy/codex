import type { SystemSettings } from "../../types/view";

interface SettingsSectionProps {
  settings?: SystemSettings;
}

export function SettingsSection({ settings }: SettingsSectionProps) {
  if (!settings) return null;

  return (
    <section className="page-section active">
      <div className="settings-grid">
        <div className="settings-card">
          <div className="settings-card-title">基本信息</div>
          <div className="settings-card-desc">应用的基本配置</div>
          <div className="form-group">
            <label className="form-label">应用名称</label>
            <input className="form-input" value={settings.appName} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">应用描述</label>
            <input className="form-input" value={settings.description} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">域名</label>
            <input className="form-input form-input-mono" value={settings.domain} readOnly />
          </div>
        </div>

        <div className="settings-card">
          <div className="settings-card-title">注册与邀请</div>
          <div className="settings-card-desc">控制用户注册方式</div>
          <div className="form-group">
            <label className="form-label">注册方式</label>
            <input className="form-input" value={settings.registrationMode} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">当前邀请码</label>
            <input className="form-input form-input-mono" value={settings.inviteCode} readOnly />
            <div className="form-hint">点击复制，分享给你的朋友</div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">新用户默认角色</label>
              <input className="form-input" value={settings.defaultRole} readOnly />
            </div>
            <div className="form-group">
              <label className="form-label">最大用户数</label>
              <input className="form-input" value={settings.maxUsers} readOnly />
            </div>
          </div>
        </div>

        <div className="settings-card">
          <div className="settings-card-title">安全设置</div>
          <div className="settings-card-desc">保护应用和用户数据</div>
          <div className="form-group">
            <label className="form-label">会话超时 (分钟)</label>
            <input className="form-input" value={settings.sessionTimeoutMinutes} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">最大并发会话</label>
            <input className="form-input" value={settings.maxConcurrentSessions} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">IP 速率限制 (次/分)</label>
            <input className="form-input" value={settings.rateLimitPerMinute} readOnly />
          </div>
        </div>
      </div>
    </section>
  );
}
