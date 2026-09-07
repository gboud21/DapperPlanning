use async_trait::async_trait;
use dapper_core::{AppContext, Command, CommandBus, Event, EventDispatcher};
use dapper_domain::{Epic, Feature, Iteration, Label, Member, Story, Workspace};
use dapper_gitlab::{GitLabClientTrait, GitLabError};
use dapper_workflows::{CommandHandlerLoop, ConflictEngine, DryPushEngine, SyncWorker};
use std::sync::Arc;

struct MockGitLabClient;

#[async_trait]
impl GitLabClientTrait for MockGitLabClient {
    async fn fetch_members(&self, _group_id: i64) -> Result<Vec<Member>, GitLabError> {
        Ok(vec![Member {
            id: 42,
            name: "Mock Dev".to_string(),
            username: "mock_dev".to_string(),
            group_ids: vec![],
            project_ids: vec![],
        }])
    }
    async fn fetch_labels(&self, _group_id: i64) -> Result<Vec<Label>, GitLabError> {
        Ok(vec![])
    }
    async fn fetch_iterations(&self, _group_id: i64) -> Result<Vec<Iteration>, GitLabError> {
        Ok(vec![])
    }
    async fn fetch_group_epics(&self, _group_id: i64) -> Result<Vec<Epic>, GitLabError> {
        Ok(vec![])
    }
    async fn fetch_project_issues(&self, _project_id: i64) -> Result<Vec<Story>, GitLabError> {
        Ok(vec![])
    }
    async fn push_story(&self, story: &Story) -> Result<Story, GitLabError> {
        Ok(story.clone())
    }
    async fn push_feature(&self, feature: &Feature) -> Result<Feature, GitLabError> {
        Ok(feature.clone())
    }
    async fn push_epic(&self, epic: &Epic) -> Result<Epic, GitLabError> {
        Ok(epic.clone())
    }
}

fn create_base_story(id: &str, title: &str, parent: &str) -> Story {
    Story {
        id: id.to_string(),
        title: title.to_string(),
        description: "Desc".to_string(),
        team: None,
        metadata: None,
        labels: vec![],
        interface_boundary: None,
        products: vec![],
        capabilities: vec![],
        weight: 5.0,
        status: "In Progress".to_string(),
        assignee_id: Some(42),
        iteration_id: Some(101),
        parent_feature_id: Some(parent.to_string()),
        gitlab_id: Some(1001),
        gitlab_iid: Some(1),
        last_synced_at: None,
        is_conflicted: false,
    }
}

#[test]
fn test_conflict_engine_structural_reparenting_diff() {
    let local = create_base_story("s1", "Modified Local Title", "feat-NEW");
    let remote = create_base_story("s1", "Modified Remote Title", "feat-OLD");

    let shadow_story = create_base_story("s1", "Original Title", "feat-OLD");
    let shadow_val = serde_json::to_value(&shadow_story).unwrap();

    let diff = ConflictEngine::evaluate_story_diff(&local, &remote, Some(&shadow_val));

    assert!(diff.has_local_changed);
    assert!(diff.has_remote_changed);
    assert!(diff.is_conflicted);
    assert!(diff.field_diffs.contains(&"parent_feature_id".to_string()));
    assert!(diff.field_diffs.contains(&"title".to_string()));
}

#[test]
fn test_dry_push_engine_simulation() {
    let mut ws = Workspace::new();
    let epic = Epic {
        id: "e1".to_string(),
        title: "Epic".to_string(),
        description: "".to_string(),
        features: vec![Feature {
            id: "f1".to_string(),
            title: "Feat".to_string(),
            description: "".to_string(),
            team: None,
            stories: vec![create_base_story("s1", "New Unsynced Story", "f1")],
            metadata: None,
            labels: vec![],
            products: vec![],
            capabilities: vec![],
            parent_epic_id: None,
            gitlab_id: None,
            gitlab_iid: None,
            last_synced_at: None,
            is_conflicted: false,
        }],
        metadata: None,
        labels: vec![],
        products: vec![],
        capabilities: vec![],
        gitlab_id: None,
        gitlab_iid: None,
        last_synced_at: None,
        is_conflicted: false,
    };
    ws.epics.push(epic);

    let summary = DryPushEngine::simulate_push(&ws);
    assert_eq!(summary.creations_list.len(), 1);
    assert_eq!(summary.creations_list[0], "Story: New Unsynced Story");
}

#[tokio::test]
async fn test_sync_worker_post_push_shadow_baseline_update() {
    let (bus, _rx) = CommandBus::default_bus();
    let dispatcher = EventDispatcher::default();
    let mut rx = dispatcher.subscribe();

    let app_ctx = AppContext::new(bus, dispatcher);
    let mock_client = Arc::new(MockGitLabClient);
    let worker = SyncWorker::new(app_ctx.clone(), mock_client);

    // Setup initial story in workspace
    {
        let mut ws = app_ctx.workspace.write().await;
        let story = create_base_story("s1", "Pre-push Story", "f1");
        ws.epics.push(Epic {
            id: "e1".to_string(),
            title: "Epic".to_string(),
            description: "".to_string(),
            features: vec![Feature {
                id: "f1".to_string(),
                title: "Feat".to_string(),
                description: "".to_string(),
                team: None,
                stories: vec![story],
                metadata: None,
                labels: vec![],
                products: vec![],
                capabilities: vec![],
                parent_epic_id: None,
                gitlab_id: None,
                gitlab_iid: None,
                last_synced_at: None,
                is_conflicted: false,
            }],
            metadata: None,
            labels: vec![],
            products: vec![],
            capabilities: vec![],
            gitlab_id: None,
            gitlab_iid: None,
            last_synced_at: None,
            is_conflicted: false,
        });
    }

    // Execute push
    worker.execute_push().await.unwrap();

    // Verify post-push shadow baseline update
    {
        let ws = app_ctx.workspace.read().await;
        assert!(ws.shadow_hierarchy.contains_key("s1"));
    }

    // Verify event dispatch
    let start_event = rx.recv().await.unwrap();
    match start_event {
        Event::SyncStarted { mode } => assert_eq!(mode, "Push"),
        _ => panic!("Expected SyncStarted event"),
    }

    let end_event = rx.recv().await.unwrap();
    match end_event {
        Event::SyncCompleted { mode } => assert_eq!(mode, "Push"),
        _ => panic!("Expected SyncCompleted event"),
    }
}

#[tokio::test]
async fn test_command_handler_clone_story() {
    let (bus, rx) = CommandBus::default_bus();
    let dispatcher = EventDispatcher::default();
    let mut event_rx = dispatcher.subscribe();

    let app_ctx = AppContext::new(bus.clone(), dispatcher);

    // Populate initial workspace with a story
    {
        let mut ws = app_ctx.workspace.write().await;
        ws.epics.push(Epic {
            id: "e1".to_string(),
            title: "Epic".to_string(),
            description: "".to_string(),
            features: vec![Feature {
                id: "f1".to_string(),
                title: "Feat".to_string(),
                description: "".to_string(),
                team: None,
                stories: vec![create_base_story("s1", "Original Story", "f1")],
                metadata: None,
                labels: vec![],
                products: vec![],
                capabilities: vec![],
                parent_epic_id: None,
                gitlab_id: None,
                gitlab_iid: None,
                last_synced_at: None,
                is_conflicted: false,
            }],
            metadata: None,
            labels: vec![],
            products: vec![],
            capabilities: vec![],
            gitlab_id: None,
            gitlab_iid: None,
            last_synced_at: None,
            is_conflicted: false,
        });
    }

    let app_ctx_clone = app_ctx.clone();
    tokio::spawn(async move {
        let mut handler = CommandHandlerLoop::new(app_ctx_clone);
        handler.run(rx).await;
    });

    // Dispatch CloneStory
    bus.dispatch(Command::CloneStory { story_id: "s1".to_string() })
        .await
        .unwrap();

    let event = event_rx.recv().await.unwrap();
    match event {
        Event::StoryCreated { story_id } => assert_eq!(story_id, "s1-clone"),
        _ => panic!("Expected StoryCreated event"),
    }

    let ws = app_ctx.workspace.read().await;
    assert_eq!(ws.epics[0].features[0].stories.len(), 2);
    assert_eq!(ws.epics[0].features[0].stories[1].title, "Original Story (Copy)");
}

#[tokio::test]
async fn test_command_handler_split_story() {
    let (bus, rx) = CommandBus::default_bus();
    let dispatcher = EventDispatcher::default();
    let mut event_rx = dispatcher.subscribe();

    let app_ctx = AppContext::new(bus.clone(), dispatcher);

    // Populate initial workspace with a story (weight = 5.0)
    {
        let mut ws = app_ctx.workspace.write().await;
        ws.epics.push(Epic {
            id: "e1".to_string(),
            title: "Epic".to_string(),
            description: "".to_string(),
            features: vec![Feature {
                id: "f1".to_string(),
                title: "Feat".to_string(),
                description: "".to_string(),
                team: None,
                stories: vec![create_base_story("s1", "Large Story", "f1")],
                metadata: None,
                labels: vec![],
                products: vec![],
                capabilities: vec![],
                parent_epic_id: None,
                gitlab_id: None,
                gitlab_iid: None,
                last_synced_at: None,
                is_conflicted: false,
            }],
            metadata: None,
            labels: vec![],
            products: vec![],
            capabilities: vec![],
            gitlab_id: None,
            gitlab_iid: None,
            last_synced_at: None,
            is_conflicted: false,
        });
    }

    let app_ctx_clone = app_ctx.clone();
    tokio::spawn(async move {
        let mut handler = CommandHandlerLoop::new(app_ctx_clone);
        handler.run(rx).await;
    });

    // Dispatch SplitStory with split_weight = 2.0
    bus.dispatch(Command::SplitStory {
        story_id: "s1".to_string(),
        split_weight: 2.0,
    })
    .await
    .unwrap();

    let update_evt = event_rx.recv().await.unwrap();
    match update_evt {
        Event::StoryUpdated { story_id } => assert_eq!(story_id, "s1"),
        _ => panic!("Expected StoryUpdated event"),
    }

    let create_evt = event_rx.recv().await.unwrap();
    match create_evt {
        Event::StoryCreated { story_id } => assert_eq!(story_id, "s1-part2"),
        _ => panic!("Expected StoryCreated event"),
    }

    let ws = app_ctx.workspace.read().await;
    assert_eq!(ws.epics[0].features[0].stories.len(), 2);
    assert_eq!(ws.epics[0].features[0].stories[0].weight, 3.0);
    assert_eq!(ws.epics[0].features[0].stories[1].weight, 2.0);
    assert_eq!(ws.epics[0].features[0].stories[1].title, "Large Story (Part 2)");
}
