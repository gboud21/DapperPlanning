from enum import Enum
from typing import Set, Dict

class UserRole(str, Enum):
    PRODUCT_MANAGER = "Product Manager"
    PRODUCT_OWNER = "Product Owner"
    SCRUM_MASTER = "Scrum Master"
    ENGINEER = "Engineer"

class ViewName(str, Enum):
    BACKLOG = "Backlog"
    PI_PLANNER = "PI Planner"
    SETTINGS = "Settings"
    INTEGRATIONS = "Integrations"

class Permission(str, Enum):
    VIEW_BACKLOG = "view_backlog"
    VIEW_PI_PLANNER = "view_pi_planner"
    VIEW_SETTINGS = "view_settings"
    VIEW_INTEGRATIONS = "view_integrations"
    
    EDIT_BACKLOG = "edit_backlog"
    EDIT_PI_PLANNING = "edit_pi_planning"
    EDIT_GLOBAL_UTILIZATION = "edit_global_utilization"
    SYNC_GITLAB = "sync_gitlab"
    EDIT_SETTINGS = "edit_settings"

class RolePermissionManager:
    """
    Manages view visibility and permission constraints across DapperPlanning user roles.
    """
    ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
        UserRole.PRODUCT_MANAGER: {
            Permission.VIEW_BACKLOG,
            Permission.VIEW_PI_PLANNER,
            Permission.VIEW_SETTINGS,
            Permission.VIEW_INTEGRATIONS,
            Permission.EDIT_BACKLOG,
            Permission.EDIT_PI_PLANNING,
            Permission.EDIT_GLOBAL_UTILIZATION,
            Permission.SYNC_GITLAB,
            Permission.EDIT_SETTINGS,
        },
        UserRole.PRODUCT_OWNER: {
            Permission.VIEW_BACKLOG,
            Permission.VIEW_PI_PLANNER,
            Permission.VIEW_SETTINGS,
            Permission.VIEW_INTEGRATIONS,
            Permission.EDIT_BACKLOG,
            Permission.EDIT_PI_PLANNING,
            Permission.SYNC_GITLAB,
            Permission.EDIT_SETTINGS,
        },
        UserRole.SCRUM_MASTER: {
            Permission.VIEW_BACKLOG,
            Permission.VIEW_PI_PLANNER,
            Permission.VIEW_SETTINGS,
            Permission.EDIT_PI_PLANNING,
            Permission.SYNC_GITLAB,
        },
        UserRole.ENGINEER: {
            Permission.VIEW_BACKLOG,
            Permission.VIEW_PI_PLANNER,
        },
    }

    ROLE_VISIBLE_VIEWS: Dict[UserRole, Set[ViewName]] = {
        UserRole.PRODUCT_MANAGER: {
            ViewName.BACKLOG,
            ViewName.PI_PLANNER,
            ViewName.SETTINGS,
            ViewName.INTEGRATIONS,
        },
        UserRole.PRODUCT_OWNER: {
            ViewName.BACKLOG,
            ViewName.PI_PLANNER,
            ViewName.SETTINGS,
            ViewName.INTEGRATIONS,
        },
        UserRole.SCRUM_MASTER: {
            ViewName.BACKLOG,
            ViewName.PI_PLANNER,
            ViewName.SETTINGS,
        },
        UserRole.ENGINEER: {
            ViewName.BACKLOG,
            ViewName.PI_PLANNER,
        },
    }

    @classmethod
    def has_permission(cls, role: UserRole, permission: Permission) -> bool:
        """
        Returns True if the specified role has the requested permission.
        """
        return permission in cls.ROLE_PERMISSIONS.get(role, set())

    @classmethod
    def is_view_visible(cls, role: UserRole, view: ViewName) -> bool:
        """
        Returns True if the specified view should be visible to the given role.
        """
        return view in cls.ROLE_VISIBLE_VIEWS.get(role, set())
