import { Toggle } from "../shared/Toggle";
import type { ModelConfig } from "../../types/view";

interface ModelsSectionProps {
  models: ModelConfig[];
  onToggle: (id: string) => void;
}

export function ModelsSection({ models, onToggle }: ModelsSectionProps) {
  return (
    <section className="page-section active">
      <div className="models-header">
        <div>
          <div className="section-subtitle">管理和配置所有可用的 AI 模型</div>
        </div>
      </div>
      <div className="model-mgmt-grid">
        {models.map((model) => (
          <div key={model.id} className={model.enabled ? "model-mgmt-card" : "model-mgmt-card disabled"}>
            <div className="model-mgmt-top">
              <div className="model-mgmt-icon" style={{ background: model.bg }}>
                {model.icon}
              </div>
              <Toggle checked={model.enabled} onChange={() => onToggle(model.id)} label={`切换 ${model.name}`} />
            </div>
            <div className="model-mgmt-name">{model.name}</div>
            <div className="model-mgmt-provider">{model.provider}</div>
            <div className="model-mgmt-stats">
              <div className="model-mgmt-stat">
                <div className="model-mgmt-stat-val">{model.calls.toLocaleString()}</div>
                <div className="model-mgmt-stat-label">今日调用</div>
              </div>
              <div className="model-mgmt-stat">
                <div className="model-mgmt-stat-val">${model.cost.toFixed(2)}</div>
                <div className="model-mgmt-stat-label">今日花费</div>
              </div>
            </div>
            <div className="model-mgmt-bar">
              <div className="model-mgmt-bar-fill" style={{ width: `${model.usagePct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
