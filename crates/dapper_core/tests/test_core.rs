use dapper_core::{AppContext, Command, CommandBus, Event, EventDispatcher};
use dapper_domain::{Epic, Workspace};
use std::path::PathBuf;
use std::sync::Arc;

#[tokio::test]
async fn test_command_bus_async_dispatch_receive() {
    let (bus, mut rx) = CommandBus::default_bus();

    let cmd = Command::LoadWorkspace {
        path: PathBuf::from("test.json"),
    };

    let dispatch_handle = tokio::spawn(async move {
        bus.dispatch(cmd.clone()).await.unwrap();
    });

    dispatch_handle.await.unwrap();

    let received = rx.recv().await.expect("Failed to receive command");
    match received {
        Command::LoadWorkspace { path } => assert_eq!(path, PathBuf::from("test.json")),
        _ => panic!("Unexpected command received"),
    }
}

#[tokio::test]
async fn test_event_dispatcher_pub_sub_broadcasting() {
    let dispatcher = EventDispatcher::new(10);
    let mut rx1 = dispatcher.subscribe();
    let mut rx2 = dispatcher.subscribe();

    let mut ws = Workspace::new();
    ws.active_product_name = Some("Event Test Product".to_string());
    let ws_arc = Arc::new(ws);

    let event = Event::WorkspaceLoaded {
        workspace: Arc::clone(&ws_arc),
    };

    dispatcher.dispatch(event).unwrap();

    let msg1 = rx1.recv().await.unwrap();
    let msg2 = rx2.recv().await.unwrap();

    match (msg1, msg2) {
        (
            Event::WorkspaceLoaded { workspace: w1 },
            Event::WorkspaceLoaded { workspace: w2 },
        ) => {
            assert_eq!(w1.active_product_name, Some("Event Test Product".to_string()));
            assert_eq!(w2.active_product_name, Some("Event Test Product".to_string()));
        }
        _ => panic!("Unexpected event payload"),
    }
}

#[tokio::test]
async fn test_app_context_shared_workspace_rwlock() {
    let (bus, _rx) = CommandBus::default_bus();
    let dispatcher = EventDispatcher::default();
    let ctx = AppContext::new(bus, dispatcher);

    // Mutate workspace state across async task
    let ctx_clone = ctx.clone();
    let task = tokio::spawn(async move {
        let mut ws = ctx_clone.workspace.write().await;
        ws.epics.push(Epic {
            id: "epic-core-1".to_string(),
            title: "Core Epic".to_string(),
            description: "".to_string(),
            features: vec![],
            metadata: None,
            labels: vec![],
            products: vec![],
            capabilities: vec![],
            gitlab_id: None,
            gitlab_iid: None,
            last_synced_at: None,
            is_conflicted: false,
        });
    });

    task.await.unwrap();

    let ws = ctx.workspace.read().await;
    assert_eq!(ws.epics.len(), 1);
    assert_eq!(ws.epics[0].id, "epic-core-1");
}
