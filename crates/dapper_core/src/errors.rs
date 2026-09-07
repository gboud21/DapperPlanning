use thiserror::Error;

#[derive(Error, Debug)]
pub enum CoreError {
    #[error("Command dispatch failed: {0}")]
    CommandDispatchError(String),

    #[error("Event send error: {0}")]
    EventSendError(String),

    #[error("Channel closed unexpectedly")]
    ChannelClosed,
}
