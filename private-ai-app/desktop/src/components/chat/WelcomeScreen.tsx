import { QUICK_PROMPTS } from "../../mocks/modelCatalog";
import type { UIModel } from "../../types/view";

interface WelcomeScreenProps {
  models: UIModel[];
  selectedModelId: string;
  onChooseModel: (modelId: string) => void;
  onUsePrompt: (text: string) => void;
}

export function WelcomeScreen({ models, selectedModelId, onChooseModel, onUsePrompt }: WelcomeScreenProps) {
  const topModels = models.slice(0, 6);

  return (
    <div className="welcome-screen">
      <div className="welcome-icon">✦</div>
      <h1 className="welcome-title">AI Hub</h1>
      <p className="welcome-subtitle">
        选择你喜欢的 AI 模型，开始对话。
        <br />
        支持 GPT、Gemini、Kimi 等主流模型。
      </p>

      <div className="model-grid">
        {topModels.map((model) => (
          <button
            key={model.model}
            type="button"
            className={model.model === selectedModelId ? "model-card selected" : "model-card"}
            onClick={() => onChooseModel(model.model)}
            aria-label={`选择 ${model.name}`}
          >
            <div className={`model-card-icon ${model.bgClass}`}>{model.icon}</div>
            <div className="model-card-name">{model.name}</div>
            <div className="model-card-desc">{model.desc}</div>
          </button>
        ))}
      </div>

      <div className="quick-prompts">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt.text}
            type="button"
            className="quick-prompt"
            onClick={() => onUsePrompt(prompt.text)}
            aria-label={`快速提问 ${prompt.text}`}
          >
            <span className="quick-prompt-icon">{prompt.icon}</span>
            {prompt.text}
          </button>
        ))}
      </div>
    </div>
  );
}
