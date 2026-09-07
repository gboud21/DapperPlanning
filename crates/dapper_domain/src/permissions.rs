use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum UserRole {
    ProductManager,
    ProductOwner,
    ScrumMaster,
    Engineer,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ViewName {
    Backlog,
    PiPlanner,
    Settings,
    Integrations,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Permission {
    ViewBacklog,
    ViewPiPlanner,
    ViewSettings,
    ViewIntegrations,
    EditBacklog,
    EditPiPlanning,
    EditGlobalUtilization,
    SyncGitlab,
    EditSettings,
}

pub struct RolePermissionManager;

impl RolePermissionManager {
    pub fn has_permission(role: UserRole, permission: Permission) -> bool {
        match (role, permission) {
            (UserRole::ProductManager, _) => true,
            (UserRole::ProductOwner, Permission::EditGlobalUtilization) => false,
            (UserRole::ProductOwner, _) => true,
            (UserRole::ScrumMaster, Permission::ViewBacklog) => true,
            (UserRole::ScrumMaster, Permission::ViewPiPlanner) => true,
            (UserRole::ScrumMaster, Permission::ViewSettings) => true,
            (UserRole::ScrumMaster, Permission::EditPiPlanning) => true,
            (UserRole::ScrumMaster, Permission::SyncGitlab) => true,
            (UserRole::ScrumMaster, _) => false,
            (UserRole::Engineer, Permission::ViewBacklog) => true,
            (UserRole::Engineer, Permission::ViewPiPlanner) => true,
            (UserRole::Engineer, _) => false,
        }
    }

    pub fn is_view_visible(role: UserRole, view: ViewName) -> bool {
        match (role, view) {
            (UserRole::ProductManager, _) => true,
            (UserRole::ProductOwner, _) => true,
            (UserRole::ScrumMaster, ViewName::Integrations) => false,
            (UserRole::ScrumMaster, _) => true,
            (UserRole::Engineer, ViewName::Backlog) | (UserRole::Engineer, ViewName::PiPlanner) => {
                true
            }
            (UserRole::Engineer, _) => false,
        }
    }
}
