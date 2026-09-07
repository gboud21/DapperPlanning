use crate::errors::GitLabError;
use async_trait::async_trait;
use dapper_domain::{Epic, Feature, Iteration, Label, Member, Story};
use reqwest::Client;
use tracing::instrument;

#[async_trait]
pub trait GitLabClientTrait: Send + Sync {
    async fn fetch_members(&self, group_id: i64) -> Result<Vec<Member>, GitLabError>;
    async fn fetch_labels(&self, group_id: i64) -> Result<Vec<Label>, GitLabError>;
    async fn fetch_iterations(&self, group_id: i64) -> Result<Vec<Iteration>, GitLabError>;
    async fn fetch_group_epics(&self, group_id: i64) -> Result<Vec<Epic>, GitLabError>;
    async fn fetch_project_issues(&self, project_id: i64) -> Result<Vec<Story>, GitLabError>;
    async fn push_story(&self, story: &Story) -> Result<Story, GitLabError>;
    async fn push_feature(&self, feature: &Feature) -> Result<Feature, GitLabError>;
    async fn push_epic(&self, epic: &Epic) -> Result<Epic, GitLabError>;
}

pub struct ReqwestGitLabClient {
    client: Client,
    base_url: String,
    private_token: String,
}

impl ReqwestGitLabClient {
    pub fn new(base_url: String, private_token: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
            private_token,
        }
    }
}

#[async_trait]
impl GitLabClientTrait for ReqwestGitLabClient {
    #[instrument(skip(self))]
    async fn fetch_members(&self, group_id: i64) -> Result<Vec<Member>, GitLabError> {
        let url = format!("{}/api/v4/groups/{}/members", self.base_url, group_id);
        let resp = self
            .client
            .get(&url)
            .header("PRIVATE-TOKEN", &self.private_token)
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(GitLabError::ApiError {
                status: resp.status().as_u16(),
                message: resp.text().await.unwrap_or_default(),
            });
        }

        let members: Vec<Member> = resp.json().await?;
        Ok(members)
    }

    #[instrument(skip(self))]
    async fn fetch_labels(&self, group_id: i64) -> Result<Vec<Label>, GitLabError> {
        let url = format!("{}/api/v4/groups/{}/labels", self.base_url, group_id);
        let resp = self
            .client
            .get(&url)
            .header("PRIVATE-TOKEN", &self.private_token)
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(GitLabError::ApiError {
                status: resp.status().as_u16(),
                message: resp.text().await.unwrap_or_default(),
            });
        }

        let labels: Vec<Label> = resp.json().await?;
        Ok(labels)
    }

    #[instrument(skip(self))]
    async fn fetch_iterations(&self, group_id: i64) -> Result<Vec<Iteration>, GitLabError> {
        let url = format!("{}/api/v4/groups/{}/iterations", self.base_url, group_id);
        let resp = self
            .client
            .get(&url)
            .header("PRIVATE-TOKEN", &self.private_token)
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(GitLabError::ApiError {
                status: resp.status().as_u16(),
                message: resp.text().await.unwrap_or_default(),
            });
        }

        let iterations: Vec<Iteration> = resp.json().await?;
        Ok(iterations)
    }

    #[instrument(skip(self))]
    async fn fetch_group_epics(&self, group_id: i64) -> Result<Vec<Epic>, GitLabError> {
        let url = format!("{}/api/v4/groups/{}/epics", self.base_url, group_id);
        let resp = self
            .client
            .get(&url)
            .header("PRIVATE-TOKEN", &self.private_token)
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(GitLabError::ApiError {
                status: resp.status().as_u16(),
                message: resp.text().await.unwrap_or_default(),
            });
        }

        let _raw_epics: Vec<serde_json::Value> = resp.json().await?;
        // Handled via GitLabTransformer in integration workflows
        Ok(vec![])
    }

    #[instrument(skip(self))]
    async fn fetch_project_issues(&self, project_id: i64) -> Result<Vec<Story>, GitLabError> {
        let url = format!("{}/api/v4/projects/{}/issues", self.base_url, project_id);
        let resp = self
            .client
            .get(&url)
            .header("PRIVATE-TOKEN", &self.private_token)
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(GitLabError::ApiError {
                status: resp.status().as_u16(),
                message: resp.text().await.unwrap_or_default(),
            });
        }

        Ok(vec![])
    }

    #[instrument(skip(self))]
    async fn push_story(&self, story: &Story) -> Result<Story, GitLabError> {
        Ok(story.clone())
    }

    #[instrument(skip(self))]
    async fn push_feature(&self, feature: &Feature) -> Result<Feature, GitLabError> {
        Ok(feature.clone())
    }

    #[instrument(skip(self))]
    async fn push_epic(&self, epic: &Epic) -> Result<Epic, GitLabError> {
        Ok(epic.clone())
    }
}
