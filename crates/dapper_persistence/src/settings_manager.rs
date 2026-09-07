use serde_json::{json, Value};
use std::fs::{self, File};
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};
use tracing::{info, warn};

fn home_dir() -> Option<PathBuf> {
    if cfg!(target_os = "windows") {
        std::env::var_os("USERPROFILE").map(PathBuf::from)
    } else {
        std::env::var_os("HOME").map(PathBuf::from)
    }
}

#[derive(Debug, Default, Clone)]
pub struct SettingsManager;

impl SettingsManager {
    pub fn new() -> Self {
        Self
    }

    pub fn get_user_data_dir() -> PathBuf {
        let base = if cfg!(target_os = "windows") {
            std::env::var_os("APPDATA")
                .map(PathBuf::from)
                .unwrap_or_else(|| {
                    home_dir()
                        .unwrap_or_else(|| PathBuf::from("."))
                        .join("AppData")
                        .join("Roaming")
                })
        } else if cfg!(target_os = "macos") {
            home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("Library")
                .join("Application Support")
        } else {
            std::env::var_os("XDG_CONFIG_HOME")
                .map(PathBuf::from)
                .unwrap_or_else(|| {
                    home_dir()
                        .unwrap_or_else(|| PathBuf::from("."))
                        .join(".config")
                })
        };
        let dir = base.join("DapperPlanning");
        let _ = fs::create_dir_all(&dir);
        dir
    }

    pub fn get_settings_path() -> PathBuf {
        if let Ok(env_path) = std::env::var("DAPPER_SETTINGS_PATH") {
            return PathBuf::from(env_path);
        }
        Self::get_user_data_dir().join("settings.json")
    }

    pub fn load_all_settings() -> Value {
        let path = Self::get_settings_path();
        if !path.exists() {
            let defaults = json!({
                "last_workspace": Value::Null,
                "is_dark": true,
                "theme": "dark",
                "auto_save": false,
                "log_level": "INFO"
            });
            let _ = Self::save_all_settings(&defaults);
            return defaults;
        }

        match File::open(&path) {
            Ok(file) => {
                let reader = BufReader::new(file);
                serde_json::from_reader(reader).unwrap_or_else(|_| json!({}))
            }
            Err(_) => json!({}),
        }
    }

    pub fn save_all_settings(settings: &Value) -> Result<(), std::io::Error> {
        let path = Self::get_settings_path();
        let file = File::create(&path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, settings)?;
        Ok(())
    }

    pub fn get_last_workspace() -> Option<PathBuf> {
        let settings = Self::load_all_settings();
        settings
            .get("last_workspace")
            .and_then(|v| v.as_str())
            .map(PathBuf::from)
    }

    pub fn set_last_workspace(path: &Path) {
        let mut settings = Self::load_all_settings();
        if let Some(obj) = settings.as_object_mut() {
            obj.insert(
                "last_workspace".to_string(),
                Value::String(path.to_string_lossy().to_string()),
            );
        }
        if let Err(e) = Self::save_all_settings(&settings) {
            warn!("Failed to save last_workspace setting: {}", e);
        } else {
            info!("Updated last_workspace setting to {:?}", path);
        }
    }

    pub fn load_integration_settings() -> IntegrationSettings {
        let settings = Self::load_all_settings();
        let default = IntegrationSettings::default();

        let status_mappings = settings.get("status_label_mappings");

        let get_mapping = |key: &str, flat_key: &str, default_val: &str| -> String {
            if let Some(map) = status_mappings.and_then(|v| v.as_object()) {
                if let Some(val) = map.get(key).and_then(|v| v.as_str()) {
                    return val.to_string();
                }
            }
            if let Some(val) = settings.get(flat_key).and_then(|v| v.as_str()) {
                return val.to_string();
            }
            default_val.to_string()
        };

        IntegrationSettings {
            auth_url: settings
                .get("auth_url")
                .and_then(|v| v.as_str())
                .unwrap_or(&default.auth_url)
                .to_string(),
            auth_pat: settings
                .get("auth_pat")
                .and_then(|v| v.as_str())
                .unwrap_or(&default.auth_pat)
                .to_string(),
            epic_group_id: settings
                .get("epic_group_id")
                .and_then(|v| v.as_str())
                .unwrap_or(&default.epic_group_id)
                .to_string(),
            epic_sync_label: settings
                .get("epic_sync_label")
                .and_then(|v| v.as_str())
                .unwrap_or(&default.epic_sync_label)
                .to_string(),
            feature_sync_label: settings
                .get("feature_sync_label")
                .and_then(|v| v.as_str())
                .unwrap_or(&default.feature_sync_label)
                .to_string(),
            legacy_status_enabled: settings
                .get("legacy_status_enabled")
                .and_then(|v| v.as_bool())
                .unwrap_or(default.legacy_status_enabled),
            label_backlog: get_mapping("Backlog", "label_backlog", &default.label_backlog),
            label_in_progress: get_mapping(
                "In Progress",
                "label_in_progress",
                &default.label_in_progress,
            ),
            label_in_review: get_mapping("In Review", "label_in_review", &default.label_in_review),
            label_done: get_mapping("Done", "label_done", &default.label_done),
            label_closed: get_mapping("Closed", "label_closed", &default.label_closed),
        }
    }

    pub fn save_integration_settings(integration: &IntegrationSettings) {
        let mut settings = Self::load_all_settings();
        if let Some(obj) = settings.as_object_mut() {
            obj.insert(
                "auth_url".to_string(),
                Value::String(integration.auth_url.clone()),
            );
            obj.insert(
                "auth_pat".to_string(),
                Value::String(integration.auth_pat.clone()),
            );
            obj.insert(
                "epic_group_id".to_string(),
                Value::String(integration.epic_group_id.clone()),
            );
            obj.insert(
                "epic_sync_label".to_string(),
                Value::String(integration.epic_sync_label.clone()),
            );
            obj.insert(
                "feature_sync_label".to_string(),
                Value::String(integration.feature_sync_label.clone()),
            );
            obj.insert(
                "legacy_status_enabled".to_string(),
                Value::Bool(integration.legacy_status_enabled),
            );
            obj.insert(
                "label_backlog".to_string(),
                Value::String(integration.label_backlog.clone()),
            );
            obj.insert(
                "label_in_progress".to_string(),
                Value::String(integration.label_in_progress.clone()),
            );
            obj.insert(
                "label_in_review".to_string(),
                Value::String(integration.label_in_review.clone()),
            );
            obj.insert(
                "label_done".to_string(),
                Value::String(integration.label_done.clone()),
            );
            obj.insert(
                "label_closed".to_string(),
                Value::String(integration.label_closed.clone()),
            );

            let mappings = json!({
                "Backlog": integration.label_backlog,
                "In Progress": integration.label_in_progress,
                "In Review": integration.label_in_review,
                "Done": integration.label_done,
                "Closed": integration.label_closed,
            });
            obj.insert("status_label_mappings".to_string(), mappings);
        }
        if let Err(e) = Self::save_all_settings(&settings) {
            warn!("Failed to save integration settings: {}", e);
        } else {
            info!("Successfully saved integration settings.");
        }
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
pub struct IntegrationSettings {
    pub auth_url: String,
    pub auth_pat: String,
    pub epic_group_id: String,
    pub epic_sync_label: String,
    pub feature_sync_label: String,
    pub legacy_status_enabled: bool,
    pub label_backlog: String,
    pub label_in_progress: String,
    pub label_in_review: String,
    pub label_done: String,
    pub label_closed: String,
}

impl Default for IntegrationSettings {
    fn default() -> Self {
        Self {
            auth_url: "https://gitlab.com".to_string(),
            auth_pat: String::new(),
            epic_group_id: String::new(),
            epic_sync_label: "Epic".to_string(),
            feature_sync_label: "Feature".to_string(),
            legacy_status_enabled: false,
            label_backlog: "Status::Backlog".to_string(),
            label_in_progress: "Status::In Progress".to_string(),
            label_in_review: "Status::In Review".to_string(),
            label_done: "Status::Done".to_string(),
            label_closed: "Status::Closed".to_string(),
        }
    }
}
