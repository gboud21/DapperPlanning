use dapper_domain::{
    CapacityCalculator, Epic, Feature, MemberCapacity, Permission, RolePermissionManager, Story,
    UserRole, ViewName, Workspace,
};

#[test]
fn test_capacity_calculator_formula_standard() {
    let cap = CapacityCalculator::calculate_member_capacity(10.0, 0.0, 100.0, 100.0, 100.0);
    assert_eq!(cap, 10.0);
}

#[test]
fn test_capacity_calculator_formula_with_pto_and_factors() {
    let cap = CapacityCalculator::calculate_member_capacity(10.0, 2.0, 80.0, 90.0, 100.0);
    assert!((cap - 5.76).abs() < 1e-4);
}

#[test]
fn test_capacity_calculator_excess_pto_clamped_to_zero() {
    let cap = CapacityCalculator::calculate_member_capacity(10.0, 12.0, 100.0, 100.0, 100.0);
    assert_eq!(cap, 0.0);
}

#[test]
fn test_capacity_calculator_from_record() {
    let record = MemberCapacity {
        team_id: "team-1".to_string(),
        member_id: 42,
        iteration_id: 100,
        pto: 3.0,
        allocation_pct: 50.0,
        velocity_factor: 100.0,
        utilization_factor: 100.0,
    };
    let cap = CapacityCalculator::calculate_member_capacity_from_record(&record, 10.0, Some(90.0));
    assert!((cap - 3.15).abs() < 1e-4);
}

#[test]
fn test_role_permissions() {
    assert!(RolePermissionManager::has_permission(
        UserRole::ProductManager,
        Permission::EditGlobalUtilization
    ));
    assert!(!RolePermissionManager::has_permission(
        UserRole::ProductOwner,
        Permission::EditGlobalUtilization
    ));
    assert!(RolePermissionManager::is_view_visible(
        UserRole::Engineer,
        ViewName::Backlog
    ));
    assert!(!RolePermissionManager::is_view_visible(
        UserRole::Engineer,
        ViewName::Integrations
    ));
}

#[test]
fn test_save_shadow_hierarchy() {
    let mut ws = Workspace::new();
    let epic = Epic {
        id: "epic-1".to_string(),
        title: "Epic Title".to_string(),
        description: "Epic Desc".to_string(),
        features: vec![Feature {
            id: "feat-1".to_string(),
            title: "Feat Title".to_string(),
            description: "Feat Desc".to_string(),
            team: None,
            stories: vec![Story {
                id: "story-1".to_string(),
                title: "Story Title".to_string(),
                description: "Story Desc".to_string(),
                team: None,
                metadata: None,
                labels: vec![],
                interface_boundary: None,
                products: vec![],
                capabilities: vec![],
                weight: 3.0,
                status: "New".to_string(),
                assignee_id: None,
                iteration_id: None,
                parent_feature_id: Some("feat-1".to_string()),
                gitlab_id: None,
                gitlab_iid: None,
                last_synced_at: None,
                is_conflicted: false,
            }],
            metadata: None,
            labels: vec![],
            products: vec![],
            capabilities: vec![],
            parent_epic_id: Some("epic-1".to_string()),
            gitlab_id: None,
            gitlab_iid: None,
            last_synced_at: None,
            is_conflicted: false,
        }],
        metadata: None,
        labels: vec![],
        products: vec![],
        capabilities: vec![],
        gitlab_id: None,
        gitlab_iid: None,
        last_synced_at: None,
        is_conflicted: false,
    };
    ws.epics.push(epic);
    ws.save_shadow_hierarchy();

    assert!(ws.shadow_hierarchy.contains_key("epic-1"));
    assert!(ws.shadow_hierarchy.contains_key("feat-1"));
    assert!(ws.shadow_hierarchy.contains_key("story-1"));
}
