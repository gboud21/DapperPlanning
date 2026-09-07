use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Team {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub domain: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct Metadata {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub assignee: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub milestone: Option<String>,
    #[serde(default)]
    pub weight: f64,
    #[serde(default)]
    pub labels: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub template: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Story {
    pub id: String,
    pub title: String,
    #[serde(default)]
    pub description: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub team: Option<Team>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Metadata>,
    #[serde(default)]
    pub labels: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub interface_boundary: Option<String>,
    #[serde(default)]
    pub products: Vec<String>,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub weight: f64,
    #[serde(default)]
    pub status: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub assignee_id: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub iteration_id: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_feature_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_id: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_iid: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub last_synced_at: Option<String>,
    #[serde(default)]
    pub is_conflicted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Feature {
    pub id: String,
    pub title: String,
    #[serde(default)]
    pub description: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub team: Option<Team>,
    #[serde(default)]
    pub stories: Vec<Story>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Metadata>,
    #[serde(default)]
    pub labels: Vec<String>,
    #[serde(default)]
    pub products: Vec<String>,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_epic_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_id: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_iid: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub last_synced_at: Option<String>,
    #[serde(default)]
    pub is_conflicted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Epic {
    pub id: String,
    pub title: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub features: Vec<Feature>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Metadata>,
    #[serde(default)]
    pub labels: Vec<String>,
    #[serde(default)]
    pub products: Vec<String>,
    #[serde(default)]
    pub capabilities: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_id: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_iid: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub last_synced_at: Option<String>,
    #[serde(default)]
    pub is_conflicted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Product {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_project_id: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gitlab_group_id: Option<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Member {
    pub id: i64,
    pub name: String,
    pub username: String,
    #[serde(default)]
    pub group_ids: Vec<i64>,
    #[serde(default)]
    pub project_ids: Vec<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Label {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<i64>,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub color: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scope: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scope_name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Iteration {
    pub id: i64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub iid: Option<i64>,
    pub title: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub start_date: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub end_date: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub state: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProductTeam {
    pub id: String,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub product_id: Option<String>,
    #[serde(default)]
    pub member_ids: Vec<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MemberCapacity {
    pub team_id: String,
    pub member_id: i64,
    pub iteration_id: i64,
    #[serde(default)]
    pub pto: f64,
    #[serde(default)]
    pub allocation_pct: f64,
    #[serde(default)]
    pub velocity_factor: f64,
    #[serde(default = "default_utilization")]
    pub utilization_factor: f64,
}

fn default_utilization() -> f64 {
    100.0
}
