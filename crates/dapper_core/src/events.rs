use crate::constants::DEFAULT_EVENT_CHANNEL_CAPACITY;
use crate::errors::CoreError;
use dapper_domain::Workspace;
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::instrument;

#[derive(Debug, Clone)]
pub enum Event {
    WorkspaceLoaded { workspace: Arc<Workspace> },
    WorkspaceSaved { path: String },
    StoryCreated { story_id: String },
    StoryUpdated { story_id: String },
    StoryDeleted { story_id: String },
    SyncStarted { mode: String },
    SyncCompleted { mode: String },
    SyncFailed { error: String },
    DryPushCompleted { summary: String, items_count: usize },
    ConflictDetected { item_id: String },
}

#[derive(Clone, Debug)]
pub struct EventDispatcher {
    sender: broadcast::Sender<Event>,
}

impl Default for EventDispatcher {
    fn default() -> Self {
        Self::new(DEFAULT_EVENT_CHANNEL_CAPACITY)
    }
}

impl EventDispatcher {
    pub fn new(capacity: usize) -> Self {
        let (sender, _) = broadcast::channel(capacity);
        Self { sender }
    }

    #[instrument(skip(self), fields(event = ?event))]
    pub fn dispatch(&self, event: Event) -> Result<usize, CoreError> {
        self.sender
            .send(event)
            .map_err(|e| CoreError::EventSendError(e.to_string()))
    }

    pub fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.sender.subscribe()
    }
}
