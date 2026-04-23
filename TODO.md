1. Planning & Data Hierarchy

    Role-Based Access Control (RBAC): You mentioned specific views for PMs, POs, and Scrum Masters. Should the tool enforce permissions (e.g., preventing a Scrum Master from deleting a Capability), or is it purely a view-filtering mechanism?
        - It should implement both view filtering and it should provide the option for locking down permissions. Permission locking includes the ability to create and edit the types of features that each role is responsible for. All buttons to edit those features should be disabled. The views should always be accessible though.
        - For the views, the ability to switch between the following categories should be available:
            - All
                - Displays the entire hiearchy of products through stories
            - Product Manager
                - Displays the Products, Capabilities, Epics and Features
                - The story level is hidden
            - Product Owner
                - Displays the Epics, Features and Stories
                - The capability level is hidden
                - The product level is hidden
            - Scrum Master
                - Displays the Features and Stories
                - The epic level is hidden
                - The capability level is hidden
                - The product level is hidden
            - Engineer
                - Displays the Stories
                - The feature level is hidden
                - The epic level is hidden
                - The capability level is hidden
                - The product level is hidden


    Product vs. Capability: Your list introduces "Products" as the top level above "Capabilities," but the current entities.py starts at Capability. Should a "Product" be a separate class, or just a metadata tag on a Capability?
        - Products are a separate class. Capabilities make up the products

    Cross-Project Mapping: Since Epics map to Features (single-team) and Stories (executed by engineers), how should the tool handle scenarios where different teams reside in different GitLab projects?
        - The Product, Capability, Epic and Features should include metadata containing the GitLab URL that it is linked to
        - By default each level should inherit from the parent, but allow it to be overriden 

    Dependency Mapping: Do you need a capability to visualize or create links between Features (e.g., "Feature A blocks Feature B") before pushing to GitLab?
        - Yes. This probably needs to be expanded upon

2. Integration & Sync Logic

    Bidirectional Sync: The current GitLabClient only shows _post methods for creation. Do you need the ability to import existing issues from GitLab into the tool, or is it strictly a "push-only" workflow?
        - The tool needs to support both pulling existing Epics and issues from GitLab and pushing new issues to GitLab

    Conflict Resolution: You mentioned needing sync resolution similar to Git. If two users edit the same local JSON file and then try to sync to GitLab, how should the tool identify the "source of truth"?
        - The tool should attempt a pull of the remote prior to executing a push and then analyze the updates for conflicts. If a conflict is detected then the user needs to resolve the conflict prior to completing the push

    CSV vs. API: Your requirements mention both "direct API integration" and "Output of formatting is in CSV." Is the CSV intended for manual upload as a fallback, or as an intermediate log of what was pushed?
        - The CSV is meant as a fallback. The API should be used to download/upload from/to GitLab

3. Local Storage & Context

    Draft State Management: Should the tool support "Draft" items that exist locally but are excluded from the GitLab sync until a specific "Ready" flag is toggled?
        - Defer this feature for now

    Auto-Save: Given the goal of preventing data loss, should the JSON save occur on every edit (via UIItemSaveRequestedEvent) or only when the user explicitly clicks "Save"?
        - For now the JSON Save should only occur when the user explicitly clicks "Save"

4. UI & User Experience

    Bulk Operations: Beyond editing individual items, do you need capabilities for bulk-moving stories between features or bulk-assigning milestones?
        - Yes. But this feature can be deferred for now.

    Interactive Walkthrough: For the "Help" section, should the walkthrough be a static overlay or a "live" tutorial that guides the user through creating their first Epic?
        - The ultimate goal is to create both a static overlay and a live tutorial. But this feature should be deferred for now.

    Validation Rules: Should the GUI prevent a user from saving a Story if certain GitLab metadata (like "Weight" or "Team") is missing?
        - Yes

5. Agnostic & Scalable Architecture

    Environment Profiles: Since it must be agnostic to the deployment environment, do you need a "Settings" capability to manage multiple GitLab instances (e.g., switching between Production and Staging GitLab)?
        - Defer this feature for now.

    Dynamic Team Onboarding: How should the "Teams" be managed? Do they need to be fetched from a central company directory, or defined manually within the workspace JSON?
        - Team management should be manually defined