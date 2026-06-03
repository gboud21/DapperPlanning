import urllib.request
import urllib.error
import json
from src.domain.entities import Epic, Story

class GitLabBaseError(Exception):
    def __init__(self, error_message: str, suggested_solution: str):
        super().__init__(error_message)
        self.error_message = error_message
        self.suggested_solution = suggested_solution

class GitLabAuthError(GitLabBaseError):
    pass

class GitLabNotFoundError(GitLabBaseError):
    pass

class GitLabNetworkError(GitLabBaseError):
    pass

class GitLabClient:
    def __init__(self, base_url: str, token: str, group_id: str, project_id: str):
        self.base_url = base_url
        self.headers = {"PRIVATE-TOKEN": token, "Content-Type": "application/json"}
        self.group_id = group_id
        self.project_id = project_id

    def _request(self, endpoint: str, payload: dict = None, method: str = 'GET') -> dict:
        url = f"{self.base_url}/api/v4/{endpoint}"
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise GitLabAuthError(
                    f"Authentication Failed ({e.code})", 
                    "Verify your Personal Access Token in Integrations Settings and ensure it has API scope."
                )
            elif e.code == 404:
                raise GitLabNotFoundError(
                    f"Resource Not Found ({e.code})", 
                    "Verify your GitLab Project ID/Group ID is correct and that the resource exists."
                )
            else:
                raise GitLabBaseError(f"API Error: {e}", "Check the GitLab status or contact your administrator.")
        except urllib.error.URLError as e:
            raise GitLabNetworkError(
                f"Network Error: {e.reason}", 
                "Check your internet connection and verify the GitLab URL is reachable."
            )
        except Exception as e:
            raise GitLabBaseError(f"Unexpected Error: {e}", "An internal error occurred.")

    def get_epics(self) -> list:
        """Fetches all epics for the group."""
        return self._request(f"groups/{self.group_id}/epics")

    def get_issues(self) -> list:
        """Fetches all issues for the project."""
        return self._request(f"projects/{self.project_id}/issues")

    def create_epic(self, epic: Epic, is_feature: bool = False, parent_id: str = None) -> dict:
        labels = epic.metadata.labels.copy()
        if is_feature: labels.append("Feature")
        payload = {
            "title": epic.title,
            "description": f"{epic.metadata.template}\n\n{epic.description}",
            "labels": ",".join(labels)
        }
        if parent_id: payload["parent_id"] = parent_id
        return self._request(f"groups/{self.group_id}/epics", payload, method='POST')

    def update_epic(self, gitlab_id: int, epic: Epic) -> dict:
        payload = {"title": epic.title, "description": epic.description}
        return self._request(f"groups/{self.group_id}/epics/{gitlab_id}", payload, method='PUT')

    def create_story(self, story: Story, epic_iid: int) -> dict:
        labels = story.metadata.labels.copy()
        payload = {
            "title": story.title,
            "description": story.description,
            "epic_iid": epic_iid,
            "labels": ",".join(labels),
            "weight": round(story.weight)
        }
        return self._request(f"projects/{self.project_id}/issues", payload, method='POST')

    def update_story(self, gitlab_id: int, story: Story) -> dict:
        payload = {
            "title": story.title,
            "description": story.description,
            "weight": round(story.weight)
        }
        return self._request(f"projects/{self.project_id}/issues/{gitlab_id}", payload, method='PUT')
