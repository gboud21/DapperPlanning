use crate::sync_worker::SyncWorker;
use dapper_core::{AppContext, Command, Event};
use dapper_domain::{Story, Workspace};
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
            Command::NewWorkspace => {
                let empty_ws = Workspace::new();
                let ws_arc = Arc::new(empty_ws.clone());
                {
                    let mut ws = self.app_context.workspace.write().await;
                    *ws = empty_ws;
                }
                let _ = self.app_context.event_dispatcher.dispatch(Event::WorkspaceLoaded {
                    workspace: ws_arc,
                });
            }
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
            Command::SaveWorkspace { path } | Command::SaveWorkspaceAs { path } => {
                let ws = self.app_context.workspace.read().await;
                self.repository.save_to_file(&ws, &path)?;
                let _ = self.app_context.event_dispatcher.dispatch(Event::WorkspaceSaved {
                    path: path.to_string_lossy().to_string(),
                });
            }
            Command::ImportWorkspace { path, format: _ } => {
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
            Command::ExportWorkspace { path, format: _ } => {
                let ws = self.app_context.workspace.read().await;
                self.repository.save_to_file(&ws, &path)?;
                let _ = self.app_context.event_dispatcher.dispatch(Event::WorkspaceSaved {
                    path: path.to_string_lossy().to_string(),
                });
            }
            Command::CreateEpic { epic } => {
                let mut ws = self.app_context.workspace.write().await;
                ws.epics.push(epic);
            }
            Command::CreateFeature { parent_epic_id, feature } => {
                let mut ws = self.app_context.workspace.write().await;
                for epic in &mut ws.epics {
                    if epic.id == parent_epic_id {
                        epic.features.push(feature.clone());
                    }
                }
            }
            Command::UpdateEpic { epic } => {
                let mut ws = self.app_context.workspace.write().await;
                let epic_id = epic.id.clone();
                for e in &mut ws.epics {
                    if e.id == epic_id {
                        e.title = epic.title.clone();
                        e.description = epic.description.clone();
                        e.products = epic.products.clone();
                        e.capabilities = epic.capabilities.clone();
                        e.labels = epic.labels.clone();
                    }
                }
            }
            Command::UpdateFeature { feature } => {
                let mut ws = self.app_context.workspace.write().await;
                let feat_id = feature.id.clone();
                for epic in &mut ws.epics {
                    for f in &mut epic.features {
                        if f.id == feat_id {
                            f.title = feature.title.clone();
                            f.description = feature.description.clone();
                            f.products = feature.products.clone();
                            f.capabilities = feature.capabilities.clone();
                            f.labels = feature.labels.clone();
                        }
                    }
                }
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
            Command::AddLocalLabel { label } => {
                let mut ws = self.app_context.workspace.write().await;
                ws.labels.insert(label.name.clone(), label);
            }
            Command::AddProduct { product_name } => {
                let mut ws = self.app_context.workspace.write().await;
                if !ws.products.iter().any(|p| p.name == product_name) {
                    ws.products.push(dapper_domain::Product {
                        name: product_name,
                        gitlab_project_id: None,
                        gitlab_group_id: None,
                    });
                }
            }
            Command::DeleteProduct { product_name } => {
                let mut ws = self.app_context.workspace.write().await;
                ws.products.retain(|p| p.name != product_name);
                for epic in &mut ws.epics {
                    epic.products.retain(|p| p != &product_name);
                    for feature in &mut epic.features {
                        feature.products.retain(|p| p != &product_name);
                        for story in &mut feature.stories {
                            story.products.retain(|p| p != &product_name);
                        }
                    }
                }
            }
            Command::AddCapability { capability_name: _ } => {}
            Command::DeleteCapability { capability_name } => {
                let mut ws = self.app_context.workspace.write().await;
                for epic in &mut ws.epics {
                    epic.capabilities.retain(|c| c != &capability_name);
                    for feature in &mut epic.features {
                        feature.capabilities.retain(|c| c != &capability_name);
                        for story in &mut feature.stories {
                            story.capabilities.retain(|c| c != &capability_name);
                        }
                    }
                }
            }
            Command::CloneStory { story_id } => {
                let mut ws = self.app_context.workspace.write().await;
                let mut cloned_story: Option<(String, Story)> = None;

                for epic in &mut ws.epics {
                    for feature in &mut epic.features {
                        for s in &feature.stories {
                            if s.id == story_id {
                                let mut clone = s.clone();
                                clone.id = format!("{}-clone", s.id);
                                clone.title = format!("{} (Copy)", s.title);
                                clone.gitlab_id = None;
                                clone.gitlab_iid = None;
                                cloned_story = Some((feature.id.clone(), clone));
                                break;
                            }
                        }
                    }
                }

                if let Some((parent_feat_id, clone)) = cloned_story {
                    let new_id = clone.id.clone();
                    'outer_clone: for epic in &mut ws.epics {
                        for feature in &mut epic.features {
                            if feature.id == parent_feat_id {
                                feature.stories.push(clone);
                                break 'outer_clone;
                            }
                        }
                    }
                    let _ = self.app_context.event_dispatcher.dispatch(Event::StoryCreated {
                        story_id: new_id,
                    });
                }
            }
            Command::SplitStory { story_id, split_weight } => {
                let mut ws = self.app_context.workspace.write().await;
                let mut split_result: Option<(String, Story, Story)> = None;

                for epic in &mut ws.epics {
                    for feature in &mut epic.features {
                        for s in &mut feature.stories {
                            if s.id == story_id {
                                s.weight = (s.weight - split_weight).max(0.0);
                                let mut part2 = s.clone();
                                part2.id = format!("{}-part2", s.id);
                                part2.title = format!("{} (Part 2)", s.title);
                                part2.weight = split_weight;
                                part2.gitlab_id = None;
                                part2.gitlab_iid = None;
                                split_result = Some((feature.id.clone(), s.clone(), part2));
                                break;
                            }
                        }
                    }
                }

                if let Some((parent_feat_id, orig, part2)) = split_result {
                    let orig_id = orig.id.clone();
                    let part2_id = part2.id.clone();

                    'outer_split: for epic in &mut ws.epics {
                        for feature in &mut epic.features {
                            if feature.id == parent_feat_id {
                                feature.stories.push(part2);
                                break 'outer_split;
                            }
                        }
                    }

                    let _ = self.app_context.event_dispatcher.dispatch(Event::StoryUpdated {
                        story_id: orig_id,
                    });
                    let _ = self.app_context.event_dispatcher.dispatch(Event::StoryCreated {
                        story_id: part2_id,
                    });
                }
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
