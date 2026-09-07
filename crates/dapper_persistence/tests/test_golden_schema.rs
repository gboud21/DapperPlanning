use dapper_persistence::{JsonWorkspaceRepository, WorkspaceRepository};
use std::fs;
use std::path::Path;

#[test]
fn test_golden_workspace_schema_round_trip() {
    let repo = JsonWorkspaceRepository::new();
    let golden_path = Path::new("../../tests/fixtures/golden_workspace.json");

    // Fallback to absolute path or workspace root relative if needed
    let target_path = if golden_path.exists() {
        golden_path.to_path_buf()
    } else {
        Path::new("tests/fixtures/golden_workspace.json").to_path_buf()
    };

    assert!(
        target_path.exists(),
        "Golden workspace fixture not found at {:?}",
        target_path
    );

    // 1. Load golden workspace fixture
    let workspace = repo
        .load_from_file(&target_path)
        .expect("Failed to load golden_workspace.json");

    assert_eq!(
        workspace.active_product_name.as_deref(),
        Some("Golden Product")
    );
    assert_eq!(workspace.products.len(), 1);
    assert_eq!(workspace.members.len(), 2);
    assert_eq!(workspace.epics.len(), 1);
    assert_eq!(workspace.epics[0].features.len(), 1);
    assert_eq!(workspace.epics[0].features[0].stories.len(), 1);
    assert_eq!(
        workspace.epics[0].features[0].stories[0].title,
        "Golden Story"
    );

    // 2. Perform round-trip save to temp file
    let temp_dir = std::env::temp_dir();
    let temp_file = temp_dir.join("rust_golden_roundtrip_test.json");

    repo.save_to_file(&workspace, &temp_file)
        .expect("Failed to save workspace roundtrip file");

    // 3. Re-load from temp file
    let reloaded_workspace = repo
        .load_from_file(&temp_file)
        .expect("Failed to reload saved workspace file");

    assert_eq!(workspace, reloaded_workspace);

    // Clean up temp file
    let _ = fs::remove_file(temp_file);
}
