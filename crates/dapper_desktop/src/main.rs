#![deny(unsafe_code)]

use anyhow::Result;
use dapper_core::{AppContext, CommandBus, EventDispatcher};
use dapper_ui::DapperApp;
use dapper_workflows::CommandHandlerLoop;
use eframe::egui;
use human_panic::setup_panic;
use tracing::info;

#[tokio::main]
async fn main() -> Result<()> {
    // 1. Setup human panic hook for user-friendly diagnostic crash reports
    setup_panic!();

    // 2. Initialize tracing subscriber telemetry
    tracing_subscriber::fmt::init();
    info!("Starting DapperPlanning Native Desktop Application...");

    // 3. Initialize CQRS buses and AppContext DI container
    let (command_bus, cmd_rx) = CommandBus::default_bus();
    let event_dispatcher = EventDispatcher::default();
    let app_context = AppContext::new(command_bus, event_dispatcher);

    // 4. Spawn background command execution loop
    let app_ctx_clone = app_context.clone();
    tokio::spawn(async move {
        let mut handler = CommandHandlerLoop::new(app_ctx_clone);
        handler.run(cmd_rx).await;
    });

    // 5. Configure eframe viewport options (1920x1080)
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1920.0, 1080.0])
            .with_min_inner_size([1024.0, 728.0])
            .with_title("DapperPlanning - Native Rust Desktop"),
        ..Default::default()
    };

    // 6. Launch native GUI event loop
    eframe::run_native(
        "DapperPlanning",
        native_options,
        Box::new(|_cc| Ok(Box::new(DapperApp::new(app_context)))),
    )
    .map_err(|e| anyhow::anyhow!("Native desktop window runtime error: {}", e))
}
