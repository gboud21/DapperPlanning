# Capabilities
## UI
- Desktop GUI: The tool must provide a native desktop Graphical User Interface (GUI).

### Resolution
- Adjustable/Scalable UI in windowed mode
    - Should prevent buttons from disapearing, etc

### Quick Actions
- Window Management Buttons (Top Right)
    - Minimize Button
    - Maximize Button
    - Close Button (Done)

### Menu Bar
- File
- Edit
- View
- Help

## Planning
- Creation & Workflow: The GUI must allow Product Owners to create Capabilities, Epics, Features, and Stories directly within the application. 
- The tool manages the hierarchy and mapping: Capabilities map to Epics (cross-team), Epics break down into Features (single-team), and Features break down into Stories.
- Customization: The GUI must allow users to select specific GitLab templates for issue/epic descriptions. It must also provide input fields to populate all other standard GitLab data (assignees, milestones, weights, labels, etc.).
- Agnostic & Scalable: The tool's architecture must be completely agnostic to the number of teams, the teams' specific domains, and the tool's own deployment environment. Teams must be easily added, removed, or reorganized dynamically within the application.
- Save Context locally to prevent the user from having to retrieve data every time/allow users to make a bunch of edits and push them all at once
    - Will probably need some sync resolution similar to how git does management of merges
    - Need to determine what format to save data in, assume JSON for now
- Needs to provide multiple views targeted at the different engineering roles:
    - Product Manager
        - Focuses on Products, Capabilities and Epics
            - Products: The list of all devices/programs being developed
            - Capabilities: The list of High-level capabilities provided by the system
            - Epics: The software functionalities being planned that provide the capabilities
                - Several Features are integrated together within an Epic
    - Product Owner
        - Focuses on the Epics, Features and Stories
            - Features: A set of deliverable software implemented by a team that can be integrated into the application
            - Stories: Individual tasks that make up a feature and are executed by an engineer
    - Scrum Master
        - Focues on Features and Stories

## Integration
- GitLab Integration: The tool must format and push this entire generated hierarchy to GitLab via direct API integration
    - Output of formatting is in CSV
    - Epics: Created as standard GitLab Epics.
    - Features: Created as GitLab Epics, but heavily differentiated using specific labels (e.g., "Feature").
    - Stories: Created as GitLab Issues.

## Help
- Needs to contain a dialog with version information
- Needs to contain a manual to help learn how to use the tool
- Needs to provide an interactive walkthrough on how to use the tool