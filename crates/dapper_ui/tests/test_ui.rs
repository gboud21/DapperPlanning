use dapper_core::{AppContext, CommandBus, EventDispatcher};
use dapper_ui::panes::backlog_pane::{generate_template, BacklogPane, SelectedItem};
use dapper_ui::{ActiveTab, DapperApp};

#[test]
fn test_dapper_app_initialization() {
    let (bus, _rx) = CommandBus::default_bus();
    let dispatcher = EventDispatcher::default();
    let app_ctx = AppContext::new(bus, dispatcher);

    let app = DapperApp::new(app_ctx);
    assert_eq!(app.active_tab, ActiveTab::Backlog);
    assert!(!app.settings_dialog.is_open);
    assert!(!app.integrations_dialog.is_open);
    assert!(!app.dry_push_modal.is_open);
    assert!(!app.conflict_modal.is_open);
}

#[test]
fn test_integrations_dialog_initialization() {
    use dapper_ui::dialogs::integrations_dialog::{IntegrationsDialog, IntegrationsTab};
    let dialog = IntegrationsDialog::default();
    assert!(!dialog.is_open);
    assert_eq!(dialog.active_tab, IntegrationsTab::Authentication);
    assert_eq!(dialog.host_url, "https://gitlab.com");
    assert_eq!(dialog.label_backlog, "Status::Backlog");
    assert_eq!(dialog.label_in_progress, "Status::In Progress");
}


#[test]
fn test_backlog_pane_selected_item() {
    let mut pane = BacklogPane::default();
    assert_eq!(pane.selected_item, None);

    pane.selected_item = Some(SelectedItem::Epic("epic-1".to_string()));
    assert_eq!(
        pane.selected_item,
        Some(SelectedItem::Epic("epic-1".to_string()))
    );

    pane.selected_item = Some(SelectedItem::Story("story-1".to_string()));
    assert_eq!(
        pane.selected_item,
        Some(SelectedItem::Story("story-1".to_string()))
    );
}

#[test]
fn test_template_generator_gitlab_heavyweight() {
    let template = generate_template("Story", "GitLab", "Heavyweight", true, true);
    assert!(template.contains("## User Story"));
    assert!(template.contains("## Acceptance Criteria"));
    assert!(template.contains("## Out of Scope"));
    assert!(template.contains("## Security & Compliance"));
}

#[test]
fn test_widget_id_generator_and_make_unique_salt() {
    use dapper_ui::utils::{make_unique_id, make_unique_salt, WidgetIdGenerator};

    let gen = WidgetIdGenerator::new();
    let s1 = gen.next_salt("scroll");
    let s2 = gen.next_salt("scroll");
    assert_ne!(s1, s2);
    assert_eq!(s1, "scroll_0");
    assert_eq!(s2, "scroll_1");

    let _id1 = gen.next_id("combo");
    let _id2 = gen.next_id("combo");

    let salt_item = make_unique_salt("product_master", "core");
    assert_eq!(salt_item, "product_master_core");

    let _id_item = make_unique_id("label", 42);
}

#[test]
fn test_integration_settings_save_and_load() {
    use dapper_persistence::{IntegrationSettings, SettingsManager};
    use dapper_ui::dialogs::integrations_dialog::IntegrationsDialog;

    let unique_id = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let settings_path = std::env::temp_dir().join(format!("test_integration_settings_{}.json", unique_id));
    std::env::set_var("DAPPER_SETTINGS_PATH", &settings_path);

    let dialog = IntegrationsDialog {
        pat_token: "glpat-secret-123".to_string(),
        root_group_id: "998877".to_string(),
        ..Default::default()
    };

    let settings_to_save = IntegrationSettings {
        auth_url: dialog.host_url.clone(),
        auth_pat: dialog.pat_token.clone(),
        epic_group_id: dialog.root_group_id.clone(),
        epic_sync_label: dialog.epic_sync_label.clone(),
        feature_sync_label: dialog.feature_sync_label.clone(),
        legacy_status_enabled: dialog.legacy_status_enabled,
        label_backlog: dialog.label_backlog.clone(),
        label_in_progress: dialog.label_in_progress.clone(),
        label_in_review: dialog.label_in_review.clone(),
        label_done: dialog.label_done.clone(),
        label_closed: dialog.label_closed.clone(),
    };
    SettingsManager::save_integration_settings(&settings_to_save);

    let loaded = SettingsManager::load_integration_settings();
    assert_eq!(loaded.auth_pat, "glpat-secret-123");
    assert_eq!(loaded.epic_group_id, "998877");

    let mut dialog_reopened = IntegrationsDialog::default();
    dialog_reopened.open();
    assert_eq!(dialog_reopened.pat_token, "glpat-secret-123");
    assert_eq!(dialog_reopened.root_group_id, "998877");

    std::env::remove_var("DAPPER_SETTINGS_PATH");
    let _ = std::fs::remove_file(&settings_path);
}


