import type { AppConfigSummary } from "../../types/api";
import { Modal } from "../shared/Modal";

interface SettingsModalProps {
  open: boolean;
  config?: AppConfigSummary;
  onClose: () => void;
}

export function SettingsModal({ open, config, onClose }: SettingsModalProps) {
  return (
    <Modal open={open} title="本地设置" onClose={onClose}>
      <div className="modal-header">
        <span className="modal-title">本地设置</span>
        <button className="modal-close" onClick={onClose} type="button" aria-label="关闭设置">
          ✕
        </button>
      </div>

      <div className="modal-body">
        <div className="model-category">
          <div className="model-category-title">运行模式</div>
          <div className="model-option selected" role="presentation">
            <div className="model-option-icon bg-gpt">L</div>
            <div className="model-option-info">
              <div className="model-option-name">本地直连</div>
              <div className="model-option-desc">当前版本不依赖云服务器，模型请求直接由桌面 App 发出。</div>
            </div>
          </div>
        </div>

        <div className="model-category">
          <div className="model-category-title">配置文件</div>
          <div className="history-empty">{config?.config_path || "加载中..."}</div>
        </div>

        <div className="model-category">
          <div className="model-category-title">数据目录</div>
          <div className="history-empty">{config?.data_dir || "加载中..."}</div>
        </div>

        <div className="model-category">
          <div className="model-category-title">Provider 状态</div>
          {(config?.providers || []).map((provider) => (
            <div key={provider.provider} className="model-option" role="presentation">
              <div className="model-option-icon bg-gpt">{provider.provider.slice(0, 1).toUpperCase()}</div>
              <div className="model-option-info">
                <div className="model-option-name">{provider.provider}</div>
                <div className="model-option-desc">
                  {provider.enabled ? "已启用" : "未启用（通常是 key 为空）"}
                </div>
              </div>
              <div className="model-option-tags">
                <span className={provider.enabled ? "model-tag tag-fast" : "model-tag tag-smart"}>
                  {provider.models.length} 个模型
                </span>
              </div>
            </div>
          ))}
          {config && config.providers.length === 0 ? <div className="history-empty">未发现可用 provider 配置</div> : null}
        </div>
      </div>
    </Modal>
  );
}
