import type { UIModel } from "../../types/view";

interface WelcomeScreenProps {
  models: UIModel[];
  selectedModelId: string;
  onChooseModel: (modelId: string) => void;
}

export function WelcomeScreen({ models, selectedModelId, onChooseModel }: WelcomeScreenProps) {
  const topModels = models.slice(0, 6);

  return (
    <div className="welcome-screen">
      <div className="welcome-hero">
        <div className="welcome-icon">✦</div>
        <h1 className="welcome-title">AI Hub</h1>
        <p className="welcome-subtitle">
          选择你喜欢的 AI 模型，开始对话
          <br />
          支持 GPT、Gemini、Claude、Kimi 等主流模型
        </p>
      </div>

      <div className="welcome-models">
        {topModels.map((model) => (
          <button
            key={model.model}
            type="button"
            className={model.model === selectedModelId ? "model-card selected" : "model-card"}
            onClick={() => onChooseModel(model.model)}
            aria-label={`选择 ${model.name}`}
          >
            {model.tags.some((tag) => tag.kind === "new") ? (
              <span className="model-card-badge model-card-badge-new">NEW</span>
            ) : model.model === "kimi-k2.5" ? (
              <span className="model-card-badge model-card-badge-hot">HOT</span>
            ) : null}

            <div className="model-card-main">
              <div className={`model-card-icon ${model.bgClass}`}>{model.icon}</div>
              <div className="model-card-copy">
                <div className="model-card-name">{model.name}</div>
                <div className="model-card-desc">{model.desc}</div>
              </div>
              {model.model === selectedModelId ? <div className="model-card-check">✓</div> : null}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
