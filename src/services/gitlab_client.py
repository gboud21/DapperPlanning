import urllib.request
import json
from src.models.entities import Epic, Story

class GitLabClient:
    def __init__(self, base_url: str, token: str, group_id: str, project_id: str):
        """
        Initializes the GitLabClient with necessary authentication and project details.

        Args:
            base_url (str): The base URL of the GitLab instance (e.g., "https://gitlab.com").
            token (str): A private access token with appropriate permissions.
            group_id (str): The ID of the GitLab group where epics are managed.
            project_id (str): The ID of the GitLab project where issues (stories) are managed.
        """
        self.base_url = base_url
        self.headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}
        self.group_id = group_id
        self.project_id = project_id

    def _post(self, endpoint: str, payload: dict) -> dict:
        """
        Sends a POST request to the GitLab API.

        Args:
            endpoint (str): The API endpoint to hit (e.g., "groups/{group_id}/epics").
            payload (dict): The JSON payload to send with the request.

        Returns:
            dict: The JSON response from the GitLab API, or an empty dictionary
                  if an error occurs.
        """
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
        """
        Creates a new epic in GitLab.

        Args:
            epic (Epic): The Epic object containing details for the new epic.
            is_feature (bool): If True, adds a "Feature" label to the epic.
                               (Note: In GitLab, features are often represented as epics with a specific label).
            parent_id (str, optional): The ID of the parent epic if this is a sub-epic.

        Returns:
            str: The IID (internal ID) of the newly created GitLab epic, or an empty string if creation fails.
        """
        labels = epic.metadata.labels.copy()
        if is_feature:
            labels.append("Feature")
            
        payload = {
            "title": epic.title,
            "description": f"{epic.metadata.template}\\n\\n{epic.description}",
            "labels": ",".join(labels)
        }
        if parent_id:
            payload["parent_id"] = parent_id
            
        response = self._post(f"groups/{self.group_id}/epics", payload)
        return str(response.get("iid", ""))

    def create_story(self, story: Story, epic_iid: str) -> str:
        """
        Creates a new issue (story) in GitLab, associating it with a given epic.

        Args:
            story (Story): The Story object containing details for the new issue.
            epic_iid (str): The IID (internal ID) of the parent epic to associate this story with.

        Returns:
            str: The IID (internal ID) of the newly created GitLab issue, or an empty string if creation fails.
        """
        labels = story.metadata.labels.copy()
        if story.interface_boundary:
            labels.append(f"boundary::{story.interface_boundary}")

        payload = {
            "title": story.title,
            "description": f"{story.metadata.template}\\n\\n{story.description}",
            "epic_iid": epic_iid,
            "labels": ",".join(labels),
            "weight": story.metadata.weight
        }
        
        response = self._post(f"projects/{self.project_id}/issues", payload)
        return str(response.get("iid", ""))