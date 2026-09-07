use dapper_domain::Story;
use serde_json::Value;

pub struct GitLabTransformer;

impl GitLabTransformer {
    pub fn map_status_label(labels: &[String], legacy_state: Option<&str>) -> String {
        for label in labels {
            if let Some(status_part) = label.strip_prefix("status::") {
                return match status_part {
                    "new" | "todo" => "New".to_string(),
                    "in_development" | "doing" | "in_progress" => "In Progress".to_string(),
                    "in_testing" | "testing" => "In Testing".to_string(),
                    "blocked" => "Blocked".to_string(),
                    "complete" | "done" | "closed" => "Complete".to_string(),
                    other => other.to_string(),
                };
            }
        }

        if let Some(state) = legacy_state {
            match state {
                "opened" => "In Progress".to_string(),
                "closed" => "Complete".to_string(),
                _ => "New".to_string(),
            }
        } else {
            "New".to_string()
        }
    }

    pub fn transform_issue_to_story(issue: &Value, parent_feature_id: Option<String>) -> Story {
        let id = issue["id"]
            .as_i64()
            .map(|i| format!("story-gl-{}", i))
            .unwrap_or_else(|| "story-gl-0".to_string());

        let title = issue["title"]
            .as_str()
            .unwrap_or("Untitled Issue")
            .to_string();
        let description = issue["description"].as_str().unwrap_or("").to_string();

        let labels: Vec<String> = issue["labels"]
            .as_array()
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();

        let state = issue["state"].as_str();
        let status = Self::map_status_label(&labels, state);

        let weight = issue["weight"].as_f64().unwrap_or(0.0);
        let assignee_id = issue["assignee"]["id"]
            .as_i64()
            .or_else(|| issue["assignees"][0]["id"].as_i64());
        let iteration_id = issue["iteration"]["id"].as_i64();
        let gitlab_id = issue["id"].as_i64();
        let gitlab_iid = issue["iid"].as_i64();

        Story {
            id,
            title,
            description,
            team: None,
            metadata: None,
            labels,
            interface_boundary: None,
            products: vec![],
            capabilities: vec![],
            weight,
            status,
            assignee_id,
            iteration_id,
            parent_feature_id,
            gitlab_id,
            gitlab_iid,
            last_synced_at: None,
            is_conflicted: false,
        }
    }
}
