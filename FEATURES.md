Based on your initial requirements and the refinements from our recent discussion, here is the updated **Capabilities** text for the Dapper Planning tool:

# Capabilities

## UI
- **Desktop GUI**: The tool must provide a native desktop Graphical User Interface (GUI).
- **Resolution**: Adjustable/Scalable UI in windowed mode to prevent UI elements (like buttons) from disappearing.
- **Quick Actions**: Standard window management (Minimize, Maximize, Close).
- **Menu Bar**: Includes File, Edit, View, and Help menus.
- **Role-Based Views**: The GUI must provide a mechanism to switch between the following filtered views:
    - **All**: Displays the entire hierarchy from Products down to Stories.
    - **Product Manager**: Displays Products, Capabilities, Epics, and Features (Stories hidden).
    - **Product Owner**: Displays Epics, Features, and Stories (Products and Capabilities hidden).
    - **Scrum Master**: Displays Features and Stories (higher levels hidden).
    - **Engineer**: Displays Stories only (all higher levels hidden).

## Planning
- **Data Hierarchy**: The tool manages a strict hierarchy: **Products** map to **Capabilities**, which map to **Epics** (cross-team), which break down into **Features** (single-team), and finally into **Stories**.
- **Creation & Workflow**: Product Owners and relevant roles can create these entities directly within the application.
- **Role-Based Permissions**: 
    - The tool must enforce permission locking based on the active role.
    - Users can only create or edit the types of entities their role is responsible for.
    - UI buttons for unauthorized actions must be disabled, though views remain accessible.
- **Customization**: Users can select specific GitLab templates for descriptions and populate standard GitLab metadata (assignees, milestones, weights, labels, etc.).
- **Inheritance & Overrides**: Entities (Product through Feature) must include a GitLab URL. By default, children inherit the URL from their parent but can manually override it.
- **Dependency Mapping**: The tool must allow users to visualize and create links (e.g., "blocks" or "blocked by") between Features.
- **Validation**: The GUI must prevent saving a Story if mandatory GitLab metadata (like Weight or Team) is missing.
- **Agnostic & Scalable**: The architecture must be agnostic to the number of teams and their domains. Teams are manually defined and managed within the workspace JSON.

## Integration
- **GitLab API Integration**: Primary method for synchronization.
    - **Bidirectional Sync**: The tool must support pulling existing Epics and Issues from GitLab and pushing new/updated items.
    - **Conflict Resolution**: The tool must attempt a "Pull" prior to any "Push." If conflicts are detected between local and remote data, the user must resolve them before completing the push.
- **Fallback Export**: The tool must be able to format the hierarchy into a CSV for manual upload as a fallback.
    - **Mapping**: Epics are created as standard GitLab Epics; Features as GitLab Epics with a "Feature" label; Stories as GitLab Issues.

## Local Storage & Context
- **Explicit Save**: To prevent data loss and allow for bulk edits, the workspace is saved to a local JSON file only when the user explicitly clicks "Save".

## Help
- **Information**: A dialog containing version information.
- **Manual**: A comprehensive user manual to help learn the tool.

## Deferred Features
- **Draft State**: Support for items that exist locally but are excluded from sync until a "Ready" flag is toggled.
- **Bulk Operations**: Moving multiple stories between features or bulk-assigning milestones.
- **Interactive Walkthrough**: Live tutorials and static overlays for onboarding.
- **Environment Profiles**: Managing multiple GitLab instances (e.g., switching between Production and Staging).