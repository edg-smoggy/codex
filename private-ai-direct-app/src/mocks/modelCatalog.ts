import type { ModelTag, UIModel } from "../types/view";
import type { ModelInfo } from "../types/api";

interface CatalogItem {
  id: string;
  name: string;
  desc: string;
  icon: string;
  bgClass: string;
  color: string;
  category: string;
  tags: ModelTag[];
}

const tag = (label: string, kind: ModelTag["kind"]): ModelTag => ({ label, kind });

const CATALOG: CatalogItem[] = [
  {
    id: "gpt-4o",
    name: "GPT-4o",
    desc: "最强大的多模态模型",
    icon: "O",
    bgClass: "bg-gpt4",
    color: "#ab68ff",
    category: "OpenAI",
    tags: [tag("强力", "smart"), tag("多模态", "vision")],
  },
  {
    id: "gpt-4o-mini",
    name: "GPT-4o Mini",
    desc: "快速、经济的轻量模型",
    icon: "O",
    bgClass: "bg-gpt",
    color: "#10a37f",
    category: "OpenAI",
    tags: [tag("快速", "fast")],
  },
  {
    id: "gpt-4.1-mini",
    name: "GPT-4.1 Mini",
    desc: "稳定均衡的通用助手",
    icon: "O",
    bgClass: "bg-gpt",
    color: "#10a37f",
    category: "OpenAI",
    tags: [tag("快速", "fast"), tag("强力", "smart")],
  },
  {
    id: "o1",
    name: "o1",
    desc: "深度推理，复杂问题求解",
    icon: "O",
    bgClass: "bg-gpt4",
    color: "#ab68ff",
    category: "OpenAI",
    tags: [tag("强力", "smart")],
  },
  {
    id: "anthropic/claude-opus-4.6",
    name: "Claude Opus 4.6",
    desc: "Claude 旗舰模型，复杂任务与深度推理",
    icon: "C",
    bgClass: "bg-claude",
    color: "#d4a574",
    category: "Anthropic",
    tags: [tag("强力", "smart"), tag("新", "new")],
  },
  {
    id: "anthropic/claude-sonnet-4.6",
    name: "Claude Sonnet 4.6",
    desc: "速度与质量平衡，适合主力日常使用",
    icon: "C",
    bgClass: "bg-claude",
    color: "#c0834a",
    category: "Anthropic",
    tags: [tag("强力", "smart"), tag("快速", "fast"), tag("新", "new")],
  },
  {
    id: "gemini-2.0-pro",
    name: "Gemini 2.0 Pro",
    desc: "Google 最新旗舰模型",
    icon: "G",
    bgClass: "bg-gemini",
    color: "#4285f4",
    category: "Google",
    tags: [tag("强力", "smart"), tag("多模态", "vision"), tag("新", "new")],
  },
  {
    id: "gemini-2.0-flash",
    name: "Gemini 2.0 Flash",
    desc: "极速响应，高性价比",
    icon: "G",
    bgClass: "bg-gemini",
    color: "#34a853",
    category: "Google",
    tags: [tag("快速", "fast")],
  },
  {
    id: "gemini-1.5-pro",
    name: "Gemini 1.5 Pro",
    desc: "复杂分析与长上下文",
    icon: "G",
    bgClass: "bg-gemini",
    color: "#4285f4",
    category: "Google",
    tags: [tag("强力", "smart")],
  },
  {
    id: "deepseek-r1",
    name: "DeepSeek R1",
    desc: "强推理能力开源模型",
    icon: "D",
    bgClass: "bg-deepseek",
    color: "#1e90ff",
    category: "开源模型",
    tags: [tag("强力", "smart"), tag("新", "new")],
  },
  {
    id: "qwen-max",
    name: "Qwen Max",
    desc: "通义千问旗舰版",
    icon: "Q",
    bgClass: "bg-qwen",
    color: "#6c5ce7",
    category: "开源模型",
    tags: [tag("强力", "smart")],
  },
  {
    id: "llama-3.1-405b",
    name: "Llama 3.1 405B",
    desc: "Meta 开源最大模型",
    icon: "L",
    bgClass: "bg-llama",
    color: "#667eea",
    category: "开源模型",
    tags: [tag("强力", "smart")],
  },
  {
    id: "mistral-large",
    name: "Mistral Large",
    desc: "欧洲顶级开源模型",
    icon: "M",
    bgClass: "bg-mistral",
    color: "#ff6b35",
    category: "开源模型",
    tags: [tag("强力", "smart"), tag("快速", "fast")],
  },
  {
    id: "kimi-k2.5",
    name: "Kimi K2.5",
    desc: "Moonshot K 系列旗舰模型",
    icon: "K",
    bgClass: "bg-kimi",
    color: "#6c5ce7",
    category: "Moonshot",
    tags: [tag("强力", "smart"), tag("新", "new")],
  },
  {
    id: "moonshot-v1-8k",
    name: "Moonshot v1 8K",
    desc: "Kimi 上下文 8K",
    icon: "M",
    bgClass: "bg-kimi",
    color: "#7865ff",
    category: "Moonshot",
    tags: [tag("快速", "fast")],
  },
  {
    id: "moonshot-v1-32k",
    name: "Moonshot v1 32K",
    desc: "Kimi 上下文 32K",
    icon: "M",
    bgClass: "bg-kimi",
    color: "#7865ff",
    category: "Moonshot",
    tags: [tag("强力", "smart")],
  },
];

const PROVIDER_CATEGORY: Record<string, string> = {
  openai: "OpenAI",
  gemini: "Google",
  kimi: "Moonshot",
  openrouter: "Anthropic",
};

const PROVIDER_ICON: Record<string, string> = {
  openai: "O",
  gemini: "G",
  kimi: "K",
  openrouter: "C",
};

const PROVIDER_BG: Record<string, string> = {
  openai: "bg-gpt",
  gemini: "bg-gemini",
  kimi: "bg-kimi",
  openrouter: "bg-claude",
};

const PROVIDER_COLOR: Record<string, string> = {
  openai: "#10a37f",
  gemini: "#4285f4",
  kimi: "#6c5ce7",
  openrouter: "#d4a574",
};

const DEFAULT_TAGS: Record<string, ModelTag[]> = {
  openai: [tag("强力", "smart")],
  gemini: [tag("快速", "fast")],
  kimi: [tag("强力", "smart")],
  openrouter: [tag("强力", "smart")],
};

export function getModelMeta(model: string, provider: string): Omit<UIModel, keyof ModelInfo> {
  const hit = CATALOG.find((item) => item.id === model);
  if (hit) {
    return {
      name: hit.name,
      desc: hit.desc,
      icon: hit.icon,
      bgClass: hit.bgClass,
      color: hit.color,
      category: hit.category,
      tags: hit.tags,
    };
  }

  return {
    name: model,
    desc: `${provider.toUpperCase()} 模型`,
    icon: PROVIDER_ICON[provider] || "✨",
    bgClass: PROVIDER_BG[provider] || "bg-gpt",
    color: PROVIDER_COLOR[provider] || "#6c5ce7",
    category: PROVIDER_CATEGORY[provider] || "其他",
    tags: DEFAULT_TAGS[provider] || [tag("强力", "smart")],
  };
}

export function toUIModel(item: ModelInfo): UIModel {
  return {
    ...item,
    ...getModelMeta(item.model, item.provider),
  };
}

export function groupModelsByCategory(models: UIModel[]): Array<{ category: string; models: UIModel[] }> {
  const map = new Map<string, UIModel[]>();
  models.forEach((model) => {
    const list = map.get(model.category) || [];
    list.push(model);
    map.set(model.category, list);
  });

  return Array.from(map.entries()).map(([category, entries]) => ({
    category,
    models: entries.sort((a, b) => a.name.localeCompare(b.name)),
  }));
}

export const QUICK_PROMPTS: Array<{ icon: string; text: string }> = [
  { icon: "💡", text: "帮我写一封正式的商务邮件" },
  { icon: "📊", text: "用 Python 分析一份 CSV 数据" },
  { icon: "🎨", text: "帮我设计一个 App 的配色方案" },
  { icon: "📝", text: "将这段文字翻译成英文" },
];
