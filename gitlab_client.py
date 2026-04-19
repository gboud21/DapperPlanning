import urllib.request
import json
from models import Epic, Story

class GitLabClient:
    def __init__(self, base_url: str, token: str, group_id: str, project_id: str):
        self.base_url = base_url
        self.headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}
        self.group_id = group_id
        self.project_id = project_id

    def _post(self, endpoint: str, payload: dict) -> dict:
        """Standard library HTTP POST request."""
        url = f"{self.base_url}/api/v4/{endpoint}"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=self.headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            print(f"API Error: {e}")
            return {}

    def create_epic(self, epic: Epic, is_feature: bool = False, parent_id: str = None) -> str:
        """Creates a standard Epic, or a Feature-level Epic with specific labels."""
        labels = epic.metadata.labels.copy()
        if is_feature:
            labels.append("Feature")
            
        payload = {
            "title": epic.title,
            "description": f"{epic.metadata.template}\n\n{epic.description}",
            "labels": ",".join(labels)
        }
        if parent_id:
            payload["parent_id"] = parent_id
            
        # Epics are created at the group level in GitLab
        response = self._post(f"groups/{self.group_id}/epics", payload)
        return str(response.get("iid", ""))

    def create_story(self, story: Story, epic_iid: str) -> str:
        """Creates an Issue under a specific project, linked to an Epic."""
        labels = story.metadata.labels.copy()
        if story.interface_boundary:
            labels.append(f"boundary::{story.interface_boundary}")

        payload = {
            "title": story.title,
            "description": f"{story.metadata.template}\n\n{story.description}",
            "epic_iid": epic_iid,
            "labels": ",".join(labels),
            "weight": story.metadata.weight
        }
        
        # Issues are created at the project level
        response = self._post(f"projects/{self.project_id}/issues", payload)
        return str(response.get("iid", ""))
