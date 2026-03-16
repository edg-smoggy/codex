import type { ApiKeyItem } from "../../types/view";

interface KeysSectionProps {
  keys: ApiKeyItem[];
}

export function KeysSection({ keys }: KeysSectionProps) {
  return (
    <section className="page-section active">
      <div className="settings-grid">
        <div className="settings-card" style={{ gridColumn: "1/-1" }}>
          <div className="settings-card-title">API 密钥管理</div>
          <div className="settings-card-desc">管理各大模型服务商的 API Key，支持多密钥轮询和自动故障转移。</div>
          <div>
            {keys.map((key) => (
              <div className="key-item" key={key.id}>
                <div className="key-info">
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: key.color }} />
                  <div>
                    <div className="key-provider">{key.provider}</div>
                    <div className="key-value">{key.maskedKey}</div>
                  </div>
                </div>
                <span className={key.status === "正常" ? "status-badge status-active" : "status-badge status-warning"}>
                  {key.status}
                </span>
                <div className="key-actions">
                  <button className="btn btn-ghost" type="button">
                    编辑
                  </button>
                  <button className="btn btn-danger" type="button">
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button className="btn btn-primary" type="button" style={{ marginTop: 8 }}>
            + 添加新密钥
          </button>
        </div>
      </div>
    </section>
  );
}
