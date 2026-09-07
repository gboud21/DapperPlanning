use async_trait::async_trait;
use dapper_gitlab::{GitLabClientTrait, GitLabError, GitLabTransformer};
use dapper_domain::{Epic, Feature, Iteration, Label, Member, Story};
use serde_json::json;

struct MockGitLabClient;

#[async_trait]
impl GitLabClientTrait for MockGitLabClient {
    async fn fetch_members(&self, _group_id: i64) -> Result<Vec<Member>, GitLabError> {
        Ok(vec![Member {
            id: 42,
            name: "Mock Member".to_string(),
            username: "mock_user".to_string(),
            group_ids: vec![101],
            project_ids: vec![201],
        }])
    }
    async fn fetch_labels(&self, _group_id: i64) -> Result<Vec<Label>, GitLabError> {
        Ok(vec![])
    }
    async fn fetch_iterations(&self, _group_id: i64) -> Result<Vec<Iteration>, GitLabError> {
        Ok(vec![])
    }
    async fn fetch_group_epics(&self, _group_id: i64) -> Result<Vec<Epic>, GitLabError> {
        Ok(vec![])
    }
    async fn fetch_project_issues(&self, _project_id: i64) -> Result<Vec<Story>, GitLabError> {
        Ok(vec![])
    }
    async fn push_story(&self, story: &Story) -> Result<Story, GitLabError> {
        Ok(story.clone())
    }
    async fn push_feature(&self, feature: &Feature) -> Result<Feature, GitLabError> {
        Ok(feature.clone())
    }
    async fn push_epic(&self, epic: &Epic) -> Result<Epic, GitLabError> {
        Ok(epic.clone())
    }
}

#[test]
fn test_gitlab_transformer_map_status_label() {
    let labels = vec!["status::in_development".to_string()];
    let status = GitLabTransformer::map_status_label(&labels, Some("opened"));
    assert_eq!(status, "In Progress");

    let blocked_labels = vec!["status::blocked".to_string()];
    assert_eq!(
        GitLabTransformer::map_status_label(&blocked_labels, None),
        "Blocked"
    );

    let empty_labels: Vec<String> = vec![];
    assert_eq!(
        GitLabTransformer::map_status_label(&empty_labels, Some("closed")),
        "Complete"
    );
}

#[test]
fn test_gitlab_transformer_issue_conversion() {
    let raw_issue = json!({
        "id": 901,
        "iid": 12,
        "title": "Raw GitLab Issue",
        "description": "Issue Body",
        "state": "opened",
        "labels": ["status::in_testing"],
        "weight": 8,
        "assignee": { "id": 42 },
        "iteration": { "id": 301 }
    });

    let story = GitLabTransformer::transform_issue_to_story(&raw_issue, Some("feat-100".to_string()));
    assert_eq!(story.id, "story-gl-901");
    assert_eq!(story.title, "Raw GitLab Issue");
    assert_eq!(story.status, "In Testing");
    assert_eq!(story.weight, 8.0);
    assert_eq!(story.assignee_id, Some(42));
    assert_eq!(story.iteration_id, Some(301));
    assert_eq!(story.parent_feature_id, Some("feat-100".to_string()));
}

#[tokio::test]
async fn test_mock_gitlab_client() {
    let client = MockGitLabClient;
    let members = client.fetch_members(101).await.unwrap();
    assert_eq!(members.len(), 1);
    assert_eq!(members[0].name, "Mock Member");
}
