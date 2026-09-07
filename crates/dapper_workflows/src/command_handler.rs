use crate::sync_worker::SyncWorker;
use dapper_core::{AppContext, Command, Event};
use dapper_gitlab::ReqwestGitLabClient;
use dapper_persistence::{JsonWorkspaceRepository, WorkspaceRepository};
use std::sync::Arc;
use tokio::sync::mpsc::Receiver;
use tracing::{error, info, instrument};

pub struct CommandHandlerLoop {
    app_context: AppContext,
    repository: JsonWorkspaceRepository,
    sync_worker: SyncWorker,
}

impl CommandHandlerLoop {
    pub fn new(app_context: AppContext) -> Self {
        let repo = JsonWorkspaceRepository::new();
        let client = Arc::new(ReqwestGitLabClient::new(
            "https://gitlab.com".to_string(),
            "".to_string(),
        ));
        let worker = SyncWorker::new(app_context.clone(), client);

        Self {
            app_context,
            repository: repo,
            sync_worker: worker,
        }
    }

    #[instrument(skip(self, rx))]
    pub async fn run(&mut self, mut rx: Receiver<Command>) {
        info!("CommandHandlerLoop started listening for CQRS commands...");
        while let Some(command) = rx.recv().await {
            info!("Processing command: {:?}", command);
            if let Err(e) = self.process_command(command).await {
                error!("Error executing command: {}", e);
            }
        }
    }

    async fn process_command(&self, command: Command) -> Result<(), anyhow::Error> {
        match command {
            Command::LoadWorkspace { path } => {
                let loaded_ws = self.repository.load_from_file(&path)?;
                let ws_arc = Arc::new(loaded_ws.clone());
                {
                    let mut ws = self.app_context.workspace.write().await;
                    *ws = loaded_ws;
                }
                let _ = self.app_context.event_dispatcher.dispatch(Event::WorkspaceLoaded {
                    workspace: ws_arc,
                });
            }
            Command::SaveWorkspace { path } => {
                let ws = self.app_context.workspace.read().await;
                self.repository.save_to_file(&ws, &path)?;
                let _ = self.app_context.event_dispatcher.dispatch(Event::WorkspaceSaved {
                    path: path.to_string_lossy().to_string(),
                });
            }
            Command::UpdateStory { story } => {
                let mut ws = self.app_context.workspace.write().await;
                let story_id = story.id.clone();
                for epic in &mut ws.epics {
                    for feature in &mut epic.features {
                        for s in &mut feature.stories {
                            if s.id == story_id {
                                *s = story.clone();
                            }
                        }
                    }
                }
                let _ = self.app_context.event_dispatcher.dispatch(Event::StoryUpdated {
                    story_id,
                });
            }
            Command::CreateStory { parent_feature_id, story } => {
                let mut ws = self.app_context.workspace.write().await;
                let story_id = story.id.clone();
                for epic in &mut ws.epics {
                    for feature in &mut epic.features {
                        if feature.id == parent_feature_id {
                            feature.stories.push(story.clone());
                        }
                    }
                }
                let _ = self.app_context.event_dispatcher.dispatch(Event::StoryCreated {
                    story_id,
                });
            }
            Command::DeleteStory { story_id } => {
                let mut ws = self.app_context.workspace.write().await;
                for epic in &mut ws.epics {
                    for feature in &mut epic.features {
                        feature.stories.retain(|s| s.id != story_id);
                    }
                }
                let _ = self.app_context.event_dispatcher.dispatch(Event::StoryDeleted {
                    story_id,
                });
            }
            Command::TriggerGitLabPull => {
                let _ = self.sync_worker.execute_pull(0).await;
            }
            Command::TriggerDryPush => {
                let _ = self.sync_worker.execute_dry_push().await;
            }
            Command::TriggerGitLabPush => {
                let _ = self.sync_worker.execute_push().await;
            }
            Command::ResolveConflict { item_id, .. } => {
                let mut ws = self.app_context.workspace.write().await;
                for epic in &mut ws.epics {
                    for feature in &mut epic.features {
                        for s in &mut feature.stories {
                            if s.id == item_id {
                                s.is_conflicted = false;
                            }
                        }
                    }
                }
                ws.save_shadow_hierarchy();
            }
            _ => {}
        }
        Ok(())
    }
}
