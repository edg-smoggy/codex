import type { AppConfigSummary, ModelInfo } from "./api";

export interface ModelTag {
  label: string;
  kind: "fast" | "smart" | "creative" | "vision" | "new";
}

export interface UIModel extends ModelInfo {
  name: string;
  desc: string;
  icon: string;
  bgClass: string;
  color: string;
  category: string;
  tags: ModelTag[];
}

export interface SettingsViewModel extends AppConfigSummary {
  app_name: string;
}
