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
        # Sanitize base_url: strip slashes and ensure we don't have /api/v4 repeated
        self.base_url = base_url.rstrip('/')
        if "/api/v4" in self.base_url:
            self.base_url = self.base_url.split("/api/v4")[0]
            
        self.token = token.strip()
        
        # Standard API headers
        # Use a more 'standard' browser-like User-Agent and specify Accept type
        self.headers = {
            "PRIVATE-TOKEN": self.token, 
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        self.group_id = group_id
        self.project_id = project_id

    def _request(self, endpoint: str, payload: dict = None, method: str = 'GET') -> dict:
        # Ensure endpoint doesn't start with a slash
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/api/v4/{clean_endpoint}"
        
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            # Try to get more detail from the response body
            error_body = ""
            try:
                error_body = e.read().decode()
            except:
                pass
            
            if e.code in (401, 403):
                solution = "Verify your Personal Access Token in Integrations Settings and ensure it has API scope."
                if e.code == 403:
                    solution += " Also note that Epics require a GitLab Premium/Ultimate subscription; this error may occur if you are on the Free/CE tier."
                
                msg = f"Authentication Failed ({e.code})"
                if error_body:
                    msg += f" - {error_body}"
                raise GitLabAuthError(msg, solution)
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
        """Free Tier: Fetches Tasks (issue_type=task) to act as Epics/Features."""
        return self._request(f"projects/{self.project_id}/issues?issue_type=task")

    def get_issues(self) -> list:
        """Fetches all standard issues for the project."""
        return self._request(f"projects/{self.project_id}/issues?issue_type=issue")

    def create_epic(self, epic: Epic, is_feature: bool = False, parent_id: str = None) -> dict:
        """Free Tier: Creates a Task to act as an Epic or Feature."""
        labels = epic.metadata.labels.copy()
        labels.append("Epic" if not is_feature else "Feature")
        
        # In Free Tier, we use labels and description links for hierarchy
        hierarchy_note = f"\n\n---\n**Parent ID:** {parent_id}" if parent_id else ""
        
        payload = {
            "title": epic.title,
            "description": f"{epic.metadata.template}\n\n{epic.description}{hierarchy_note}",
            "labels": ",".join(labels),
            "issue_type": "task"
        }
        return self._request(f"projects/{self.project_id}/issues", payload, method='POST')

    def update_epic(self, gitlab_id: int, epic: Epic) -> dict:
        """Updates the project-level Task."""
        payload = {"title": epic.title, "description": epic.description}
        return self._request(f"projects/{self.project_id}/issues/{gitlab_id}", payload, method='PUT')

    def create_story(self, story: Story, epic_iid: int) -> dict:
        """Creates a standard Issue for the Story."""
        labels = story.metadata.labels.copy()
        payload = {
            "title": story.title,
            "description": f"Parent Feature IID: {epic_iid}\n\n{story.description}",
            "labels": ",".join(labels),
            "weight": round(story.weight),
            "issue_type": "issue"
        }
        return self._request(f"projects/{self.project_id}/issues", payload, method='POST')

    def update_story(self, gitlab_id: int, story: Story) -> dict:
        """Updates the project-level Issue."""
        payload = {
            "title": story.title,
            "description": story.description,
            "weight": round(story.weight)
        }
        return self._request(f"projects/{self.project_id}/issues/{gitlab_id}", payload, method='PUT')
