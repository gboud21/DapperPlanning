import urllib.request
import urllib.error
import json
from typing import List, Optional, Union, Any
from src.domain.entities import Epic, Story
from src.infrastructure.telemetry.logger import logger, audit_payload

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
    def __init__(self, base_url: str, token: str, group_id: str, project_id: str, epic_sync_label: str = "Epic", feature_sync_label: str = "Feature"):
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
        self.epic_sync_label = epic_sync_label
        self.feature_sync_label = feature_sync_label

    def _request(self, endpoint: str, payload: dict = None, method: str = 'GET') -> dict:
        # This remains for single requests (POST, PUT, single GET)
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.base_url}/api/v4/{clean_endpoint}"
        
        # Network Telemetry
        logger.info(f"GitLab API Request: {method.upper()} {url}")
        if payload:
            logger.debug(f"Payload: {json.dumps(payload)}")
        
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                status_code = response.getcode()
                response_data = json.loads(response.read().decode())
                logger.info(f"GitLab API Response: {status_code} OK")
                
                # Auditing successful PUSH/PULL
                if method.upper() in ('POST', 'PUT'):
                    audit_payload(f"push_{method.upper()}_{clean_endpoint.replace('/', '_')}", {
                        "request": payload,
                        "response": response_data
                    })
                elif method.upper() == 'GET':
                    # Create a filesystem-safe string from the endpoint
                    safe_endpoint = endpoint.replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')
                    # Truncate if the endpoint string is too long for a filename
                    safe_endpoint = safe_endpoint[:50] 
                    audit_payload(f"pull_{safe_endpoint}", response_data)
                     
                return response_data
        except urllib.error.HTTPError as e:
            # Try to get more detail from the response body
            error_body = ""
            try:
                error_body = e.read().decode()
            except:
                pass
            
            # Network Telemetry for Errors
            logger.error(f"GitLab API Error: {e.code} - {error_body}")
            
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

    def _request_all(self, endpoint: str) -> list:
        """Handles GitLab pagination to fetch all records for a GET request."""
        results = []
        page = 1
        per_page = 100
        
        # Ensure endpoint doesn't have query params yet, or handle them
        connector = "&" if "?" in endpoint else "?"
        
        while True:
            paged_endpoint = f"{endpoint}{connector}page={page}&per_page={per_page}"
            clean_endpoint = paged_endpoint.lstrip('/')
            url = f"{self.base_url}/api/v4/{clean_endpoint}"
            
            # Network Telemetry
            print(f"[GitLab API] GET {url}")
            
            req = urllib.request.Request(url, headers=self.headers, method='GET')
            try:
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                    if not data:
                        break
                    
                    # Audit paginated GET response
                    safe_endpoint = paged_endpoint.replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')
                    safe_endpoint = safe_endpoint[:50]
                    audit_payload(f"pull_paged_{safe_endpoint}", data)
                    
                    results.extend(data)
                    
                    # Check X-Next-Page header if available
                    next_page = response.getheader('X-Next-Page')
                    if not next_page:
                        break
                    page = int(next_page)
            except urllib.error.HTTPError as e:
                # Reuse error handling logic or raise
                if e.code in (401, 403, 404):
                    # We can call self._request to trigger standard error handling
                    self._request(paged_endpoint)
                raise GitLabBaseError(f"API Error: {e}", "Check the GitLab status.")
            except Exception as e:
                raise GitLabBaseError(f"Unexpected Error: {e}", "An error occurred during paginated fetch.")
                
        return results

    def fetch_group_epics(self, group_id: Union[int, str]) -> list[dict]:
        """Fetches all epics for a given group ID."""
        return self._request_all(f"groups/{group_id}/epics")

    def fetch_project_issues(self, project_id: Union[int, str], issue_type: str = "issue") -> list[dict]:
        """Fetches all issues/tasks for a given project ID."""
        return self._request_all(f"projects/{project_id}/issues?issue_type={issue_type}")

    def fetch_group_members(self, group_id: Union[int, str]) -> list[dict]:
        """Fetches all members for a given group ID."""
        return self._request_all(f"groups/{group_id}/members/all")

    def fetch_project_members(self, project_id: Union[int, str]) -> list[dict]:
        """Fetches all members for a given project ID."""
        return self._request_all(f"projects/{project_id}/members/all")

    def fetch_group_labels(self, group_id: Union[int, str]) -> list[dict]:
        """Fetches all labels for a given group ID."""
        return self._request_all(f"groups/{group_id}/labels")

    def fetch_project_labels(self, project_id: Union[int, str]) -> list[dict]:
        """Fetches all labels for a given project ID."""
        return self._request_all(f"projects/{project_id}/labels")

    def fetch_group_iterations(self, group_id: Union[int, str]) -> list[dict]:
        """Fetches all iterations for a given group ID."""
        return self._request_all(f"groups/{group_id}/iterations")

    def fetch_project_iterations(self, project_id: Union[int, str]) -> list[dict]:
        """Fetches all iterations for a given project ID."""
        return self._request_all(f"projects/{project_id}/iterations")

    def create_issue_note(self, project_id: Union[int, str], issue_iid: int, body: str) -> dict:
        """Posts a discussion note/comment to a project issue to trigger Quick Actions."""
        return self._request(f"projects/{project_id}/issues/{issue_iid}/notes", {"body": body}, method='POST')

    def create_group_label(self, group_id: Union[int, str], label_data: dict) -> dict:
        """Creates a label in the Group."""
        return self._request(f"groups/{group_id}/labels", label_data, method='POST')

    def create_project_label(self, project_id: Union[int, str], label_data: dict) -> dict:
        """Creates a label in the Project."""
        return self._request(f"projects/{project_id}/labels", label_data, method='POST')

    def create_group_epic(self, group_id: Union[int, str], epic: Epic, parent_id: Optional[int] = None, labels: str = None) -> dict:
        """Premium Tier: Creates an Epic in the Group."""
        payload = {
            "title": epic.title,
            "description": epic.description,
            "labels": labels if labels is not None else (",".join(epic.labels) if epic.labels else "")
        }
        if parent_id:
            payload["parent_id"] = parent_id
            
        return self._request(f"groups/{group_id}/epics", payload, method='POST')

    def update_group_epic(self, group_id: Union[int, str], gitlab_iid: int, epic: Epic, parent_id: Optional[int] = None, labels: str = None) -> dict:
        """Premium Tier: Updates the Group-level Epic."""
        payload = {
            "title": epic.title, 
            "description": epic.description,
            "labels": labels if labels is not None else (",".join(epic.labels) if epic.labels else "")
        }
        if parent_id:
            payload["parent_id"] = parent_id
        return self._request(f"groups/{group_id}/epics/{gitlab_iid}", payload, method='PUT')

    def create_project_task(self, project_id: Union[int, str], epic: Epic, is_feature: bool = False, parent_id: Optional[str] = None, labels: str = None) -> dict:
        """Free Tier: Creates a Task to act as an Epic or Feature."""
        item_labels = epic.labels + ([self.epic_sync_label if not is_feature else self.feature_sync_label])
        task_labels = labels if labels is not None else (",".join(item_labels) if item_labels else "")
        
        # In Free Tier, we use labels and description links for hierarchy
        hierarchy_note = f"\n\n---\n**Parent ID:** {parent_id}" if parent_id else ""
        
        payload = {
            "title": epic.title,
            "description": f"{epic.metadata.template}\n\n{epic.description}{hierarchy_note}",
            "labels": task_labels,
            "issue_type": "task"
        }
        
        if getattr(epic, 'assignee_id', None):
            payload['assignee_ids'] = [epic.assignee_id]
            
        return self._request(f"projects/{project_id}/issues", payload, method='POST')

    def update_project_task(self, project_id: Union[int, str], gitlab_iid: int, epic: Epic, parent_id: Optional[str] = None, labels: str = None) -> dict:
        """Free Tier: Updates a Task acting as an Epic or Feature."""
        payload = {
            "title": epic.title, 
            "description": epic.description,
            "labels": labels if labels is not None else (",".join(epic.labels) if epic.labels else "")
        }
        if parent_id:
            # Note: Changing parent in Free Tier (description link) might require careful string replacement,
            # but for now we follow the instruction to include it in the payload logic.
            # Usually parent_id for Tasks/Issues is handled via metadata or links in Free Tier.
            pass
            
        if getattr(epic, 'assignee_id', None):
            payload['assignee_ids'] = [epic.assignee_id]
            
        return self._request(f"projects/{project_id}/issues/{gitlab_iid}", payload, method='PUT')

    def create_story(self, project_id: Union[int, str], story: Story, epic_iid: Optional[int] = None, labels: str = None) -> dict:
        """Creates a standard Issue for the Story."""
        story_labels = labels if labels is not None else (",".join(story.labels) if story.labels else "")
        payload = {
            "title": story.title,
            "description": f"Parent Feature IID: {epic_iid}\n\n{story.description}" if epic_iid else story.description,
            "labels": story_labels,
            "weight": round(story.weight),
            "issue_type": "issue"
        }
        if epic_iid:
            payload["epic_iid"] = epic_iid
            
        if getattr(story, 'assignee_id', None):
            payload['assignee_ids'] = [story.assignee_id]
            
        # Execute primary issue registration
        resp = self._request(f"projects/{project_id}/issues", payload, method='POST')
        
        # Process sequential quick actions follow-up for iterations
        issue_iid = resp.get('iid')
        if issue_iid and getattr(story, 'iteration_id', None):
            try:
                self.create_issue_note(project_id, issue_iid, f"/iteration *iteration:{story.iteration_id}")
            except Exception as e:
                logger.warning(f"Failed to append iteration quick action on remote issue creation: {e}")
                
        return resp

    def update_story(self, project_id: Union[int, str], gitlab_iid: int, story: Story, epic_iid: Optional[int] = None, labels: str = None) -> dict:
        """Updates the project-level Issue with title, description, weight, and state."""
        # Map local status to GitLab state_event
        state_event = 'close' if story.status == 'Done' else 'reopen'
        
        payload = {
            "title": story.title,
            "description": story.description,
            "labels": labels if labels is not None else (",".join(story.labels) if story.labels else ""),
            "weight": round(story.weight) if hasattr(story, 'weight') else 0,
            "state_event": state_event
        }
        if epic_iid:
            payload["epic_iid"] = epic_iid
            
        if getattr(story, 'assignee_id', None):
            payload['assignee_ids'] = [story.assignee_id]
            
        # Execute core details modification request
        resp = self._request(f"projects/{project_id}/issues/{gitlab_iid}", payload, method='PUT')
        
        # Apply Quick Actions to set or remove iteration state fields securely
        try:
            if getattr(story, 'iteration_id', None):
                self.create_issue_note(project_id, gitlab_iid, f"/iteration *iteration:{story.iteration_id}")
            else:
                self.create_issue_note(project_id, gitlab_iid, "/remove_iteration")
        except Exception as e:
            logger.warning(f"Failed to modify iteration quick action state on remote issue update: {e}")
            
        return resp

    def delete_group_epic(self, group_id: Union[int, str], gitlab_iid: int) -> dict:
        """Deletes an Epic from the Group."""
        return self._request(f"groups/{group_id}/epics/{gitlab_iid}", method='DELETE')

    def delete_project_task(self, project_id: Union[int, str], gitlab_iid: int) -> dict:
        """Deletes a Task (Epic/Feature/Story) from the Project."""
        return self._request(f"projects/{project_id}/issues/{gitlab_iid}", method='DELETE')
