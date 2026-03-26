import { useMemo } from "react";

import { groupModelsByCategory } from "../../mocks/modelCatalog";
import type { UIModel } from "../../types/view";
import { Modal } from "../shared/Modal";

interface ModelSelectorModalProps {
  open: boolean;
  models: UIModel[];
  selectedModelId: string;
  search: string;
  onSearchChange: (value: string) => void;
  onSelect: (modelId: string) => void;
  onClose: () => void;
}

function renderTagClass(kind: string): string {
  switch (kind) {
    case "fast":
      return "tag-fast";
    case "smart":
      return "tag-smart";
    case "creative":
      return "tag-creative";
    case "vision":
      return "tag-vision";
    case "new":
      return "tag-new";
    default:
      return "tag-smart";
  }
}

export function ModelSelectorModal({
  open,
  models,
  selectedModelId,
  search,
  onSearchChange,
  onSelect,
  onClose,
}: ModelSelectorModalProps) {
  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    if (!s) return models;
    return models.filter((item) => item.name.toLowerCase().includes(s) || item.model.toLowerCase().includes(s));
  }, [models, search]);

  const categories = useMemo(() => groupModelsByCategory(filtered), [filtered]);

  return (
    <Modal open={open} title="选择模型" onClose={onClose}>
      <div className="modal-header">
        <span className="modal-title">选择模型</span>
        <button className="modal-close" onClick={onClose} type="button" aria-label="关闭模型选择">
          ✕
        </button>
      </div>

      <div className="modal-search">
        <input
          type="text"
          placeholder="搜索模型..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          autoFocus
          aria-label="搜索模型"
        />
      </div>

      <div className="modal-body">
        {categories.length === 0 ? (
          <div className="modal-empty">未找到匹配的模型</div>
        ) : (
          categories.map((group) => (
            <div className="model-category" key={group.category}>
              <div className="model-category-title">{group.category}</div>
              {group.models.map((model) => (
                <button
                  key={model.model}
                  type="button"
                  className={model.model === selectedModelId ? "model-option selected" : "model-option"}
                  onClick={() => {
                    onSelect(model.model);
                    onClose();
                  }}
                >
                  <div className={`model-option-icon ${model.bgClass}`}>{model.icon}</div>
                  <div className="model-option-info">
                    <div className="model-option-name">{model.name}</div>
                    <div className="model-option-desc">{model.desc}</div>
                  </div>
                  <div className="model-option-tags">
                    {model.tags.map((tag) => (
                      <span key={tag.label} className={`model-tag ${renderTagClass(tag.kind)}`}>
                        {tag.label}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          ))
        )}
      </div>
    </Modal>
  );
}
