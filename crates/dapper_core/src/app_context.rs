use crate::command_bus::CommandBus;
use crate::events::EventDispatcher;
use dapper_domain::Workspace;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone, Debug)]
pub struct AppContext {
    pub workspace: Arc<RwLock<Workspace>>,
    pub command_bus: CommandBus,
    pub event_dispatcher: EventDispatcher,
}

impl AppContext {
    pub fn new(command_bus: CommandBus, event_dispatcher: EventDispatcher) -> Self {
        Self {
            workspace: Arc::new(RwLock::new(Workspace::new())),
            command_bus,
            event_dispatcher,
        }
    }

    pub fn with_workspace(
        workspace: Workspace,
        command_bus: CommandBus,
        event_dispatcher: EventDispatcher,
    ) -> Self {
        Self {
            workspace: Arc::new(RwLock::new(workspace)),
            command_bus,
            event_dispatcher,
        }
    }
}
