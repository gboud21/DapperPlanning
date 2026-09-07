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
    assert!(!app.dry_push_modal.is_open);
    assert!(!app.conflict_modal.is_open);
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


