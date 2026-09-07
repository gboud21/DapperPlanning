#![deny(unsafe_code)]

pub mod app_context;
pub mod command_bus;
pub mod commands;
pub mod constants;
pub mod errors;
pub mod events;

pub use app_context::AppContext;
pub use command_bus::CommandBus;
pub use commands::Command;
pub use constants::{DEFAULT_COMMAND_CHANNEL_CAPACITY, DEFAULT_EVENT_CHANNEL_CAPACITY};
pub use errors::CoreError;
pub use events::{Event, EventDispatcher};
