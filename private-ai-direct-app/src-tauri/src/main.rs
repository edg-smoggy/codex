#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    collections::HashMap,
    fs,
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};

use chrono::Utc;
use futures_util::StreamExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{Emitter, State, WebviewWindow};
use tokio::sync::Mutex;
use uuid::Uuid;

const APP_DIR_NAME: &str = "AIHubDirect";
const DEFAULT_TEMPERATURE: f32 = 0.7;
const DEFAULT_MAX_TOKENS: u32 = 8192;
const CONNECT_TIMEOUT_SECONDS: u64 = 15;
const MAX_AUTO_CONTINUATIONS: usize = 1;
const CONTINUE_PROMPT: &str = "继续";

#[derive(Clone)]
struct DirectState {
    client: Client,
    active_streams: Arc<Mutex<HashMap<String, Arc<AtomicBool>>>>,
}

impl DirectState {
    fn new() -> Self {
        let client = Client::builder()
            .connect_timeout(std::time::Duration::from_secs(CONNECT_TIMEOUT_SECONDS))
            .build()
            .expect("failed to build reqwest client");

        Self {
            client,
            active_streams: Arc::new(Mutex::new(HashMap::new())),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ProvidersFile {
    providers: Vec<ProviderConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ProviderConfig {
    provider: String,
    api_key: String,
    base_url: String,
    models: Vec<String>,
    #[serde(default = "default_true")]
    enabled: bool,
    #[serde(default)]
    title: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ConversationRecord {
    id: String,
    title: String,
    model: String,
    created_at: String,
    updated_at: String,
    messages: Vec<MessageItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ModelInfo {
    model: String,
    provider: String,
    enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ConversationSummary {
    id: String,
    title: String,
    model: String,
    created_at: String,
    updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct MessageItem {
    id: String,
    conversation_id: String,
    role: String,
    content: String,
    model: String,
    provider: String,
    input_tokens: i64,
    output_tokens: i64,
    cost: f64,
    created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ProviderStatus {
    provider: String,
    enabled: bool,
    models: Vec<String>,
    config_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct AppConfigSummary {
    app_name: String,
    data_dir: String,
    config_path: String,
    providers: Vec<ProviderStatus>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StreamUsage {
    input_tokens: i64,
    output_tokens: i64,
    cost: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StreamMetaEvent {
    request_id: String,
    conversation_id: String,
    assistant_message_id: String,
    model: String,
    provider: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StreamChunkEvent {
    request_id: String,
    delta: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StreamDoneEvent {
    request_id: String,
    usage: StreamUsage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StreamErrorEvent {
    request_id: String,
    detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct StartChatRequest {
    request_id: String,
    conversation_id: Option<String>,
    message: String,
    model: String,
    thinking_mode: Option<String>,
    regenerate_assistant_id: Option<String>,
}

#[derive(Debug, Clone)]
struct ProviderResult {
    provider: String,
    content: String,
    input_tokens: i64,
    output_tokens: i64,
    cost: f64,
}

fn default_true() -> bool {
    true
}

fn app_data_dir() -> Result<PathBuf, String> {
    let base = dirs::data_local_dir()
        .or_else(dirs::data_dir)
        .ok_or_else(|| "无法定位本地数据目录".to_string())?;
    let dir = base.join(APP_DIR_NAME);
    fs::create_dir_all(&dir).map_err(|err| format!("创建数据目录失败: {err}"))?;
    Ok(dir)
}

fn providers_path() -> Result<PathBuf, String> {
    Ok(app_data_dir()?.join("providers.json"))
}

fn conversations_path() -> Result<PathBuf, String> {
    Ok(app_data_dir()?.join("conversations.json"))
}

fn has_usable_provider_config(raw: &str) -> bool {
    serde_json::from_str::<ProvidersFile>(raw)
        .map(|config| {
            config
                .providers
                .iter()
                .any(|provider| provider.enabled && !provider.api_key.trim().is_empty() && !provider.models.is_empty())
        })
        .unwrap_or(false)
}

fn ensure_seed_files() -> Result<(), String> {
    let providers = providers_path()?;
    let bundled_providers = include_str!("../resources/providers.json");
    if !providers.exists() {
        fs::write(&providers, bundled_providers)
            .map_err(|err| format!("写入默认 providers.json 失败: {err}"))?;
    } else if has_usable_provider_config(bundled_providers) {
        let local_providers = fs::read_to_string(&providers).unwrap_or_default();
        if !has_usable_provider_config(&local_providers) {
            fs::write(&providers, bundled_providers)
                .map_err(|err| format!("恢复默认 providers.json 失败: {err}"))?;
        }
    }

    let conversations = conversations_path()?;
    if !conversations.exists() {
        fs::write(&conversations, "[]").map_err(|err| format!("写入默认 conversations.json 失败: {err}"))?;
    }

    Ok(())
}

fn load_providers() -> Result<ProvidersFile, String> {
    ensure_seed_files()?;
    let path = providers_path()?;
    let raw = fs::read_to_string(&path).map_err(|err| format!("读取 providers.json 失败: {err}"))?;
    serde_json::from_str(&raw).map_err(|err| format!("解析 providers.json 失败: {err}"))
}

fn save_conversations(conversations: &[ConversationRecord]) -> Result<(), String> {
    ensure_seed_files()?;
    let path = conversations_path()?;
    let body = serde_json::to_string_pretty(conversations).map_err(|err| format!("序列化会话失败: {err}"))?;
    fs::write(path, body).map_err(|err| format!("保存会话失败: {err}"))
}

fn load_conversations() -> Result<Vec<ConversationRecord>, String> {
    ensure_seed_files()?;
    let path = conversations_path()?;
    let raw = fs::read_to_string(path).map_err(|err| format!("读取会话失败: {err}"))?;
    serde_json::from_str(&raw).map_err(|err| format!("解析会话失败: {err}"))
}

fn provider_enabled(provider: &ProviderConfig) -> bool {
    provider.enabled && !provider.api_key.trim().is_empty()
}

fn count_tokens(text: &str) -> i64 {
    if text.trim().is_empty() {
        return 1;
    }
    let count = text.chars().count() as i64;
    (count / 4).max(1)
}

fn count_message_tokens(messages: &[Value]) -> i64 {
    serde_json::to_string(messages)
        .map(|body| count_tokens(&body))
        .unwrap_or(1)
}

fn estimate_cost(provider: &str, model: &str, input_tokens: i64, output_tokens: i64) -> f64 {
    let (input_rate, output_rate) = match provider {
        "gemini" => match model {
            "gemini-2.0-flash" => (0.0003_f64, 0.001_f64),
            "gemini-1.5-pro" => (0.00125_f64, 0.005_f64),
            _ => (0.00035_f64, 0.00105_f64),
        },
        "kimi" => match model {
            "kimi-k2.5" => (0.0002_f64, 0.001_f64),
            "moonshot-v1-8k" => (0.00015_f64, 0.0008_f64),
            "moonshot-v1-32k" => (0.0003_f64, 0.0015_f64),
            _ => (0.0002_f64, 0.001_f64),
        },
        "openrouter" => match model {
            "anthropic/claude-opus-4.6" => (0.005_f64, 0.025_f64),
            "anthropic/claude-sonnet-4.6" => (0.003_f64, 0.015_f64),
            _ => (0.003_f64, 0.015_f64),
        },
        _ => (0.0, 0.0),
    };

    (((input_tokens as f64 / 1000.0) * input_rate) + ((output_tokens as f64 / 1000.0) * output_rate)).max(0.0)
}

fn summarize_title(message: &str) -> String {
    let trimmed = message.trim();
    let mut title = trimmed.chars().take(28).collect::<String>();
    if trimmed.chars().count() > 28 {
        title.push('…');
    }
    if title.is_empty() {
        "新会话".to_string()
    } else {
        title
    }
}

fn to_model_infos(config: &ProvidersFile) -> Vec<ModelInfo> {
    let mut models = Vec::new();
    for provider in &config.providers {
        for model in &provider.models {
            models.push(ModelInfo {
                model: model.clone(),
                provider: provider.provider.clone(),
                enabled: provider_enabled(provider),
            });
        }
    }
    models
}

fn find_provider<'a>(config: &'a ProvidersFile, model: &str) -> Option<&'a ProviderConfig> {
    config
        .providers
        .iter()
        .find(|provider| provider.models.iter().any(|item| item == model))
}

fn messages_for_provider(messages: &[MessageItem]) -> Vec<Value> {
    messages
        .iter()
        .map(|item| {
            json!({
                "role": item.role,
                "content": item.content,
            })
        })
        .collect()
}

fn parse_openai_stream_delta(payload: &Value) -> Option<String> {
    let choices = payload.get("choices")?.as_array()?;
    let first = choices.first()?;
    let delta = first.get("delta")?;
    if let Some(content) = delta.get("content") {
        if let Some(text) = content.as_str() {
            return Some(text.to_string());
        }
        if let Some(parts) = content.as_array() {
            let text = parts
                .iter()
                .filter_map(|part| {
                    if let Some(text) = part.as_str() {
                        return Some(text.to_string());
                    }
                    part.get("text").and_then(|value| value.as_str()).map(|s| s.to_string())
                })
                .collect::<String>();
            if !text.is_empty() {
                return Some(text);
            }
        }
    }
    None
}

fn parse_openai_finish_reason(payload: &Value) -> Option<String> {
    payload
        .get("choices")
        .and_then(|value| value.as_array())
        .and_then(|choices| choices.first())
        .and_then(|choice| choice.get("finish_reason"))
        .and_then(|value| value.as_str())
        .map(|value| value.to_string())
}

async fn stream_openai_like(
    client: &Client,
    provider: &ProviderConfig,
    model: &str,
    messages: &[Value],
    thinking_mode: &str,
    request_id: &str,
    window: &WebviewWindow,
    cancel: &Arc<AtomicBool>,
) -> Result<ProviderResult, String> {
    let mut overrides = vec![None];
    if provider.provider == "kimi" && thinking_mode == "thinking" {
        overrides = vec![
            Some(json!({"thinking": {"enabled": true}})),
            Some(json!({"thinking": {"type": "enabled"}})),
            Some(json!({"thinking": {"mode": "enabled"}})),
            Some(json!({"thinking": true})),
        ];
    }
    if provider.provider == "openrouter"
        && thinking_mode == "thinking"
        && [
            "anthropic/claude-opus-4.6",
            "anthropic/claude-sonnet-4.6",
        ]
        .contains(&model)
    {
        overrides = vec![Some(json!({"reasoning": {"enabled": true}}))];
    }

    let mut full_content = String::new();
    let mut total_input_tokens = 0_i64;
    let mut total_output_tokens = 0_i64;
    let url = format!("{}/chat/completions", provider.base_url.trim_end_matches('/'));
    for continuation in 0..=MAX_AUTO_CONTINUATIONS {
        let request_messages = if continuation == 0 {
            messages.to_vec()
        } else {
            let mut extended = messages.to_vec();
            extended.push(json!({
                "role": "assistant",
                "content": full_content,
            }));
            extended.push(json!({
                "role": "user",
                "content": CONTINUE_PROMPT,
            }));
            extended
        };

        let payload = json!({
            "model": model,
            "messages": request_messages,
            "temperature": if provider.provider == "kimi" && model.starts_with("kimi-k2.5") { 1.0 } else { DEFAULT_TEMPERATURE },
            "stream": true,
            "max_tokens": DEFAULT_MAX_TOKENS,
        });

        let mut segment_content = String::new();
        let mut usage_obj = Value::Null;
        let mut finish_reason: Option<String> = None;

        for (idx, override_payload) in overrides.iter().enumerate() {
            let mut body = payload.clone();
            if let Some(override_payload) = override_payload {
                if let (Some(dst), Some(src)) = (body.as_object_mut(), override_payload.as_object()) {
                    for (key, value) in src {
                        dst.insert(key.clone(), value.clone());
                    }
                }
            }

            let mut request = client
                .post(&url)
                .header("Authorization", format!("Bearer {}", provider.api_key))
                .header("Content-Type", "application/json")
                .header("Accept", "text/event-stream")
                .json(&body);

            if provider.provider == "openrouter" {
                if let Some(title) = &provider.title {
                    request = request.header("X-OpenRouter-Title", title);
                }
            }

            let response = request.send().await.map_err(|err| format!("请求模型失败: {err}"))?;
            let status = response.status();
            if !status.is_success() {
                let detail = response.text().await.unwrap_or_default();
                if provider.provider == "kimi"
                    && thinking_mode == "thinking"
                    && idx < 3
                    && [400_u16, 422_u16].contains(&status.as_u16())
                {
                    continue;
                }
                return Err(if detail.is_empty() {
                    format!("provider 返回错误状态: {status}")
                } else {
                    format!("provider 返回错误状态: {status} - {detail}")
                });
            }

            let mut stream = response.bytes_stream();
            let mut buffer = String::new();
            let mut saw_done = false;

            while let Some(chunk) = stream.next().await {
                if cancel.load(Ordering::Relaxed) {
                    break;
                }
                let bytes = chunk.map_err(|err| format!("读取流失败: {err}"))?;
                let text = String::from_utf8_lossy(&bytes);
                buffer.push_str(&text);

                while let Some(pos) = buffer.find('\n') {
                    let line = buffer[..pos].trim_end_matches('\r').to_string();
                    buffer.drain(..=pos);
                    if !line.starts_with("data:") {
                        continue;
                    }
                    let data = line.trim_start_matches("data:").trim();
                    if data.is_empty() {
                        continue;
                    }
                    if data == "[DONE]" {
                        saw_done = true;
                        break;
                    }

                    let payload: Value = match serde_json::from_str(data) {
                        Ok(payload) => payload,
                        Err(_) => continue,
                    };

                    if let Some(usage) = payload.get("usage") {
                        usage_obj = usage.clone();
                    }
                    if let Some(reason) = parse_openai_finish_reason(&payload) {
                        finish_reason = Some(reason);
                    }

                    if let Some(delta) = parse_openai_stream_delta(&payload) {
                        if !delta.is_empty() {
                            segment_content.push_str(&delta);
                            full_content.push_str(&delta);
                            let _ = window.emit(
                                "chat://chunk",
                                StreamChunkEvent {
                                    request_id: request_id.to_string(),
                                    delta,
                                },
                            );
                        }
                    }
                }

                if saw_done {
                    break;
                }
            }

            let input_tokens = usage_obj
                .get("prompt_tokens")
                .and_then(|value| value.as_i64())
                .unwrap_or_else(|| count_message_tokens(&request_messages));
            let output_tokens = usage_obj
                .get("completion_tokens")
                .and_then(|value| value.as_i64())
                .unwrap_or_else(|| count_tokens(&segment_content));

            total_input_tokens += input_tokens;
            total_output_tokens += output_tokens;
            break;
        }

        let truncated = matches!(finish_reason.as_deref(), Some("length"));
        if cancel.load(Ordering::Relaxed) || !truncated || segment_content.is_empty() {
            break;
        }
    }

    Ok(ProviderResult {
        provider: provider.provider.clone(),
        content: full_content,
        input_tokens: total_input_tokens,
        output_tokens: total_output_tokens,
        cost: estimate_cost(&provider.provider, model, total_input_tokens, total_output_tokens),
    })
}

async fn stream_gemini(
    client: &Client,
    provider: &ProviderConfig,
    model: &str,
    messages: &[Value],
    request_id: &str,
    window: &WebviewWindow,
    cancel: &Arc<AtomicBool>,
) -> Result<ProviderResult, String> {
    let url = format!("{}/models/{}:streamGenerateContent", provider.base_url.trim_end_matches('/'), model);
    let mut full_content = String::new();
    let mut total_input_tokens = 0_i64;
    let mut total_output_tokens = 0_i64;

    for continuation in 0..=MAX_AUTO_CONTINUATIONS {
        let request_messages = if continuation == 0 {
            messages.to_vec()
        } else {
            let mut extended = messages.to_vec();
            extended.push(json!({
                "role": "assistant",
                "content": full_content,
            }));
            extended.push(json!({
                "role": "user",
                "content": CONTINUE_PROMPT,
            }));
            extended
        };

        let contents = request_messages
            .iter()
            .filter_map(|message| {
                let role = message.get("role")?.as_str()?;
                let text = message.get("content")?.as_str()?;
                Some(json!({
                    "role": if role == "assistant" { "model" } else { "user" },
                    "parts": [{"text": text}],
                }))
            })
            .collect::<Vec<_>>();

        let body = json!({
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": DEFAULT_MAX_TOKENS,
                "temperature": DEFAULT_TEMPERATURE
            }
        });

        let response = client
            .post(&url)
            .query(&[("key", provider.api_key.as_str()), ("alt", "sse")])
            .header("Content-Type", "application/json")
            .header("Accept", "text/event-stream")
            .json(&body)
            .send()
            .await
            .map_err(|err| format!("请求 Gemini 失败: {err}"))?;

        let status = response.status();
        if !status.is_success() {
            let detail = response.text().await.unwrap_or_default();
            return Err(if detail.is_empty() {
                format!("Gemini 返回错误状态: {status}")
            } else {
                format!("Gemini 返回错误状态: {status} - {detail}")
            });
        }

        let mut segment_content = String::new();
        let mut usage_obj = Value::Null;
        let mut finish_reason: Option<String> = None;
        let mut stream = response.bytes_stream();
        let mut buffer = String::new();

        while let Some(chunk) = stream.next().await {
            if cancel.load(Ordering::Relaxed) {
                break;
            }
            let bytes = chunk.map_err(|err| format!("读取 Gemini 流失败: {err}"))?;
            let text = String::from_utf8_lossy(&bytes);
            buffer.push_str(&text);

            while let Some(pos) = buffer.find('\n') {
                let line = buffer[..pos].trim_end_matches('\r').to_string();
                buffer.drain(..=pos);
                if !line.starts_with("data:") {
                    continue;
                }
                let data = line.trim_start_matches("data:").trim();
                if data.is_empty() {
                    continue;
                }

                let payload: Value = match serde_json::from_str(data) {
                    Ok(payload) => payload,
                    Err(_) => continue,
                };

                if let Some(usage) = payload.get("usageMetadata") {
                    usage_obj = usage.clone();
                }

                if let Some(candidates) = payload.get("candidates").and_then(|value| value.as_array()) {
                    for candidate in candidates {
                        if let Some(reason) = candidate.get("finishReason").and_then(|value| value.as_str()) {
                            finish_reason = Some(reason.to_string());
                        }
                        if let Some(parts) = candidate
                            .get("content")
                            .and_then(|value| value.get("parts"))
                            .and_then(|value| value.as_array())
                        {
                            for part in parts {
                                if let Some(text) = part.get("text").and_then(|value| value.as_str()) {
                                    if !text.is_empty() {
                                        segment_content.push_str(text);
                                        full_content.push_str(text);
                                        let _ = window.emit(
                                            "chat://chunk",
                                            StreamChunkEvent {
                                                request_id: request_id.to_string(),
                                                delta: text.to_string(),
                                            },
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        let input_tokens = usage_obj
            .get("promptTokenCount")
            .and_then(|value| value.as_i64())
            .unwrap_or_else(|| count_message_tokens(&request_messages));
        let output_tokens = usage_obj
            .get("candidatesTokenCount")
            .and_then(|value| value.as_i64())
            .unwrap_or_else(|| count_tokens(&segment_content));

        total_input_tokens += input_tokens;
        total_output_tokens += output_tokens;

        let truncated = matches!(finish_reason.as_deref(), Some("MAX_TOKENS"));
        if cancel.load(Ordering::Relaxed) || !truncated || segment_content.is_empty() {
            break;
        }
    }

    Ok(ProviderResult {
        provider: provider.provider.clone(),
        content: full_content,
        input_tokens: total_input_tokens,
        output_tokens: total_output_tokens,
        cost: estimate_cost(&provider.provider, model, total_input_tokens, total_output_tokens),
    })
}

async fn run_stream(
    client: &Client,
    provider: &ProviderConfig,
    model: &str,
    messages: &[Value],
    thinking_mode: &str,
    request_id: &str,
    window: &WebviewWindow,
    cancel: &Arc<AtomicBool>,
) -> Result<ProviderResult, String> {
    match provider.provider.as_str() {
        "gemini" => stream_gemini(client, provider, model, messages, request_id, window, cancel).await,
        "kimi" | "openrouter" => {
            stream_openai_like(client, provider, model, messages, thinking_mode, request_id, window, cancel).await
        }
        other => Err(format!("暂不支持 provider: {other}")),
    }
}

async fn handle_chat_stream(
    client: Client,
    window: WebviewWindow,
    request: StartChatRequest,
    cancel: Arc<AtomicBool>,
) -> Result<(), String> {
    let providers = load_providers()?;
    let provider = find_provider(&providers, &request.model)
        .cloned()
        .ok_or_else(|| format!("找不到模型对应的 provider: {}", request.model))?;

    if !provider_enabled(&provider) {
        return Err(format!("{} 尚未配置可用 API key", provider.provider));
    }

    let mut conversations = load_conversations()?;
    let now = Utc::now().to_rfc3339();
    let thinking_mode = request.thinking_mode.clone().unwrap_or_else(|| "standard".to_string());

    if let Some(regenerate_id) = request.regenerate_assistant_id.clone() {
        let conversation_id = request
            .conversation_id
            .clone()
            .ok_or_else(|| "重新生成需要提供 conversationId".to_string())?;
        let convo = conversations
            .iter_mut()
            .find(|item| item.id == conversation_id)
            .ok_or_else(|| "未找到目标会话".to_string())?;
        let assistant_idx = convo
            .messages
            .iter()
            .position(|item| item.id == regenerate_id && item.role == "assistant")
            .ok_or_else(|| "未找到目标回复".to_string())?;
        let previous_user = convo.messages[..assistant_idx]
            .iter()
            .rev()
            .find(|item| item.role == "user")
            .cloned()
            .ok_or_else(|| "未找到可重生成的用户消息".to_string())?;

        let provider_messages = messages_for_provider(&convo.messages[..assistant_idx]);
        let _ = window.emit(
            "chat://meta",
            StreamMetaEvent {
                request_id: request.request_id.clone(),
                conversation_id: convo.id.clone(),
                assistant_message_id: regenerate_id.clone(),
                model: request.model.clone(),
                provider: provider.provider.clone(),
            },
        );

        let result = run_stream(
            &client,
            &provider,
            &request.model,
            &provider_messages,
            &thinking_mode,
            &request.request_id,
            &window,
            &cancel,
        )
        .await?;

        let updated = MessageItem {
            id: regenerate_id,
            conversation_id: convo.id.clone(),
            role: "assistant".to_string(),
            content: result.content.clone(),
            model: request.model.clone(),
            provider: result.provider.clone(),
            input_tokens: result.input_tokens,
            output_tokens: result.output_tokens,
            cost: result.cost,
            created_at: now.clone(),
        };
        convo.messages[assistant_idx] = updated;
        convo.updated_at = now.clone();
        save_conversations(&conversations)?;

        let _ = previous_user;
        let _ = window.emit(
            "chat://done",
            StreamDoneEvent {
                request_id: request.request_id,
                usage: StreamUsage {
                    input_tokens: result.input_tokens,
                    output_tokens: result.output_tokens,
                    cost: result.cost,
                },
            },
        );
        return Ok(());
    }

    let conversation_id = request
        .conversation_id
        .clone()
        .unwrap_or_else(|| Uuid::new_v4().to_string());
    let user_message = MessageItem {
        id: Uuid::new_v4().to_string(),
        conversation_id: conversation_id.clone(),
        role: "user".to_string(),
        content: request.message.clone(),
        model: request.model.clone(),
        provider: "local".to_string(),
        input_tokens: 0,
        output_tokens: 0,
        cost: 0.0,
        created_at: now.clone(),
    };
    let assistant_message_id = Uuid::new_v4().to_string();

    let convo_idx = if let Some(idx) = conversations.iter().position(|item| item.id == conversation_id) {
        idx
    } else {
        conversations.push(ConversationRecord {
            id: conversation_id.clone(),
            title: summarize_title(&request.message),
            model: request.model.clone(),
            created_at: now.clone(),
            updated_at: now.clone(),
            messages: Vec::new(),
        });
        conversations.len() - 1
    };

    conversations[convo_idx].model = request.model.clone();
    conversations[convo_idx].updated_at = now.clone();
    conversations[convo_idx].messages.push(user_message);
    save_conversations(&conversations)?;

    let provider_messages = messages_for_provider(&conversations[convo_idx].messages);

    let _ = window.emit(
        "chat://meta",
        StreamMetaEvent {
            request_id: request.request_id.clone(),
            conversation_id: conversation_id.clone(),
            assistant_message_id: assistant_message_id.clone(),
            model: request.model.clone(),
            provider: provider.provider.clone(),
        },
    );

    let result = run_stream(
        &client,
        &provider,
        &request.model,
        &provider_messages,
        &thinking_mode,
        &request.request_id,
        &window,
        &cancel,
    )
    .await?;

    conversations[convo_idx].messages.push(MessageItem {
        id: assistant_message_id,
        conversation_id,
        role: "assistant".to_string(),
        content: result.content.clone(),
        model: request.model,
        provider: result.provider.clone(),
        input_tokens: result.input_tokens,
        output_tokens: result.output_tokens,
        cost: result.cost,
        created_at: Utc::now().to_rfc3339(),
    });
    conversations[convo_idx].updated_at = Utc::now().to_rfc3339();
    save_conversations(&conversations)?;

    let _ = window.emit(
        "chat://done",
        StreamDoneEvent {
            request_id: request.request_id,
            usage: StreamUsage {
                input_tokens: result.input_tokens,
                output_tokens: result.output_tokens,
                cost: result.cost,
            },
        },
    );

    Ok(())
}

#[tauri::command]
fn load_app_config() -> Result<AppConfigSummary, String> {
    ensure_seed_files()?;
    let config_path = providers_path()?;
    let data_dir = app_data_dir()?;
    let providers = load_providers()?;

    Ok(AppConfigSummary {
        app_name: "AI Hub Direct".to_string(),
        data_dir: data_dir.display().to_string(),
        config_path: config_path.display().to_string(),
        providers: providers
            .providers
            .into_iter()
            .map(|provider| ProviderStatus {
                provider: provider.provider.clone(),
                enabled: provider_enabled(&provider),
                models: provider.models.clone(),
                config_path: config_path.display().to_string(),
            })
            .collect(),
    })
}

#[tauri::command]
fn list_models() -> Result<Vec<ModelInfo>, String> {
    let config = load_providers()?;
    Ok(to_model_infos(&config))
}

#[tauri::command]
fn list_conversations() -> Result<Vec<ConversationSummary>, String> {
    let conversations = load_conversations()?;
    let mut summaries = conversations
        .into_iter()
        .map(|item| ConversationSummary {
            id: item.id,
            title: item.title,
            model: item.model,
            created_at: item.created_at,
            updated_at: item.updated_at,
        })
        .collect::<Vec<_>>();
    summaries.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    Ok(summaries)
}

#[tauri::command]
fn get_conversation_messages(conversation_id: String) -> Result<Vec<MessageItem>, String> {
    let conversations = load_conversations()?;
    let convo = conversations
        .into_iter()
        .find(|item| item.id == conversation_id)
        .ok_or_else(|| "未找到会话".to_string())?;
    Ok(convo.messages)
}

#[tauri::command]
fn delete_conversation(conversation_id: String) -> Result<(), String> {
    let mut conversations = load_conversations()?;
    let before = conversations.len();
    conversations.retain(|item| item.id != conversation_id);
    if conversations.len() == before {
        return Err("未找到会话".to_string());
    }
    save_conversations(&conversations)
}

#[tauri::command]
async fn start_chat_stream(
    window: WebviewWindow,
    state: State<'_, DirectState>,
    request: StartChatRequest,
) -> Result<(), String> {
    let cancel = Arc::new(AtomicBool::new(false));
    state
        .active_streams
        .lock()
        .await
        .insert(request.request_id.clone(), cancel.clone());

    let state_inner = state.inner().clone();
    let request_id = request.request_id.clone();
    tauri::async_runtime::spawn(async move {
        if let Err(err) = handle_chat_stream(state_inner.client.clone(), window.clone(), request, cancel.clone()).await {
            eprintln!("start_chat_stream error: {err}");
            let _ = window.emit(
                "chat://error",
                StreamErrorEvent {
                    request_id: request_id.clone(),
                    detail: err,
                },
            );
        }
        state_inner.active_streams.lock().await.remove(&request_id);
    });

    Ok(())
}

#[tauri::command]
async fn stop_chat_stream(state: State<'_, DirectState>, request_id: String) -> Result<(), String> {
    if let Some(cancel) = state.active_streams.lock().await.get(&request_id).cloned() {
        cancel.store(true, Ordering::Relaxed);
    }
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(DirectState::new())
        .invoke_handler(tauri::generate_handler![
            load_app_config,
            list_models,
            list_conversations,
            get_conversation_messages,
            delete_conversation,
            start_chat_stream,
            stop_chat_stream
        ])
        .run(tauri::generate_context!())
        .expect("failed to run tauri application");
}
