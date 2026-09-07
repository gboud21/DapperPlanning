use crate::commands::Command;
use crate::constants::DEFAULT_COMMAND_CHANNEL_CAPACITY;
use crate::errors::CoreError;
use tokio::sync::mpsc;
use tracing::instrument;

#[derive(Clone, Debug)]
pub struct CommandBus {
    sender: mpsc::Sender<Command>,
}

impl CommandBus {
    pub fn new(capacity: usize) -> (Self, mpsc::Receiver<Command>) {
        let (sender, receiver) = mpsc::channel(capacity);
        (Self { sender }, receiver)
    }

    pub fn default_bus() -> (Self, mpsc::Receiver<Command>) {
        Self::new(DEFAULT_COMMAND_CHANNEL_CAPACITY)
    }

    #[instrument(skip(self), fields(command = ?command))]
    pub async fn dispatch(&self, command: Command) -> Result<(), CoreError> {
        self.sender
            .send(command)
            .await
            .map_err(|e| CoreError::CommandDispatchError(e.to_string()))
    }

    #[instrument(skip(self), fields(command = ?command))]
    pub fn try_dispatch(&self, command: Command) -> Result<(), CoreError> {
        self.sender
            .try_send(command)
            .map_err(|e| CoreError::CommandDispatchError(e.to_string()))
    }
}
