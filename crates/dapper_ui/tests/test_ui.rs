use dapper_core::{AppContext, CommandBus, EventDispatcher};
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
