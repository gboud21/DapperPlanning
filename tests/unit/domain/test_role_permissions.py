import pytest
from src.domain.role_permissions import (
    RolePermissionManager, UserRole, ViewName, Permission
)

def test_product_manager_role_permissions():
    """
    Product Manager role:
    - Visible Views: Backlog, PI Planner, Settings, Integrations
    - Permissions: All permissions including EDIT_GLOBAL_UTILIZATION
    """
    role = UserRole.PRODUCT_MANAGER

    # Views
    assert RolePermissionManager.is_view_visible(role, ViewName.BACKLOG) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.PI_PLANNER) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.SETTINGS) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.INTEGRATIONS) is True

    # Permissions
    assert RolePermissionManager.has_permission(role, Permission.EDIT_BACKLOG) is True
    assert RolePermissionManager.has_permission(role, Permission.EDIT_PI_PLANNING) is True
    assert RolePermissionManager.has_permission(role, Permission.EDIT_GLOBAL_UTILIZATION) is True
    assert RolePermissionManager.has_permission(role, Permission.SYNC_GITLAB) is True
    assert RolePermissionManager.has_permission(role, Permission.EDIT_SETTINGS) is True

def test_product_owner_role_permissions():
    """
    Product Owner role:
    - Visible Views: Backlog, PI Planner, Settings, Integrations
    - Permissions: EDIT_BACKLOG, EDIT_PI_PLANNING, SYNC_GITLAB, EDIT_SETTINGS
    - Constraint: EDIT_GLOBAL_UTILIZATION is False
    """
    role = UserRole.PRODUCT_OWNER

    # Views
    assert RolePermissionManager.is_view_visible(role, ViewName.BACKLOG) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.PI_PLANNER) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.SETTINGS) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.INTEGRATIONS) is True

    # Permissions
    assert RolePermissionManager.has_permission(role, Permission.EDIT_BACKLOG) is True
    assert RolePermissionManager.has_permission(role, Permission.EDIT_PI_PLANNING) is True
    assert RolePermissionManager.has_permission(role, Permission.SYNC_GITLAB) is True
    assert RolePermissionManager.has_permission(role, Permission.EDIT_SETTINGS) is True

    # Constraint check
    assert RolePermissionManager.has_permission(role, Permission.EDIT_GLOBAL_UTILIZATION) is False

def test_scrum_master_role_permissions():
    """
    Scrum Master role:
    - Visible Views: Backlog, PI Planner, Settings (Integrations hidden)
    - Permissions: VIEW_BACKLOG, VIEW_PI_PLANNER, EDIT_PI_PLANNING, SYNC_GITLAB
    - Constraints: EDIT_GLOBAL_UTILIZATION is False, EDIT_SETTINGS is False
    """
    role = UserRole.SCRUM_MASTER

    # Views
    assert RolePermissionManager.is_view_visible(role, ViewName.BACKLOG) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.PI_PLANNER) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.SETTINGS) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.INTEGRATIONS) is False

    # Permissions
    assert RolePermissionManager.has_permission(role, Permission.EDIT_PI_PLANNING) is True
    assert RolePermissionManager.has_permission(role, Permission.SYNC_GITLAB) is True

    # Constraints
    assert RolePermissionManager.has_permission(role, Permission.EDIT_GLOBAL_UTILIZATION) is False
    assert RolePermissionManager.has_permission(role, Permission.EDIT_SETTINGS) is False

def test_engineer_role_permissions():
    """
    Engineer role:
    - Visible Views: Backlog, PI Planner (Settings and Integrations hidden)
    - Permissions: VIEW_BACKLOG, VIEW_PI_PLANNER
    - Constraints: All edit/sync permissions are False
    """
    role = UserRole.ENGINEER

    # Views
    assert RolePermissionManager.is_view_visible(role, ViewName.BACKLOG) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.PI_PLANNER) is True
    assert RolePermissionManager.is_view_visible(role, ViewName.SETTINGS) is False
    assert RolePermissionManager.is_view_visible(role, ViewName.INTEGRATIONS) is False

    # Permissions
    assert RolePermissionManager.has_permission(role, Permission.VIEW_BACKLOG) is True
    assert RolePermissionManager.has_permission(role, Permission.VIEW_PI_PLANNER) is True

    # Constraints
    assert RolePermissionManager.has_permission(role, Permission.EDIT_BACKLOG) is False
    assert RolePermissionManager.has_permission(role, Permission.EDIT_PI_PLANNING) is False
    assert RolePermissionManager.has_permission(role, Permission.EDIT_GLOBAL_UTILIZATION) is False
    assert RolePermissionManager.has_permission(role, Permission.SYNC_GITLAB) is False
    assert RolePermissionManager.has_permission(role, Permission.EDIT_SETTINGS) is False
