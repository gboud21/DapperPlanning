# Overview
This is a wireframe to update the PI Planning UI with use it for reference when designing the plan to develop the following workflow.

The PI Planning screen is intended to be used by Product Owners and Product Managers to assist them estimating capacity for the team and verifying the team's planned workload during PI Planning.

## Goal
1. Ask clarifying questions to flush out the design to ensure there are no gaps in the workflows.
2. Generate a summary of the design, including any modifications/additional details flushed out through the clarifying questions.
3. Develop an execution plan to implement step 2.
4. Generate the prompts for an AI Agent to implement the design. Prompts should be divided into the steps detailed by the execution plan in step 3. The AI Agent executing the implementation will be using the Gemini 3.1 Flash model. The prompts should be optimized for that model.

#  Design
## UI Layout
The UI Layout for the PI Planner view will follow a similar layout as the Backlog view. The high-level layout is detailed in the image attached in the previous prompt. The following high-level sections should be placed from left-to-right:
- The View Selction: Contains the buttons for changing UI Views (ie Backlog and PI Planner)
- The Tree View: A column containing high-level overview/summaries that drive edits in the right-most pane
- The Editting Pane: The area of the screen where work the user can edit specific objects

### The View Selection
This section is already complete. There are no further edits that need to be made to this seciton for this feature. It provides the ability to swap between the Backlog Editting view and the PI Planner view.

### The Tree View
This section is divided into two parts:
- Team Composition Tree View
- Members List Box

#### Team Composition Tree View
This widget provides a cascading list through which engineers can be added to Product Teams. The tree follows a three-layer heirarchy:
1. The Product: This is the highest-level tree view object. It represents a specific product/project under which multiple product teams can be managed.
2. The Product Team: This is the middle-level tree view object. A Product Team is a child of excatly one product. It represents a specific domain being developed under which multiple engineers can be managed.
3. The Members: This is the lowest-level tree view object. A Member represents an engineer within a Product Team. Engineers can be assigned to multiple Product Teams. Members cannot be direct children of Products.

The Tree View should provide similar right-click context creation capabilities as the Backlog view. The rules are:

##### Add Product
Products should always be able to be created via the Right-click menu. A Product will create a new top-level object.

##### Add Product Team
When right-clicking on Products, the Add Product Team selection should create a new empty product team underneath that product.

The Add Product Team selection should be disabled any other time the right-click context menu is opened if it is not on a Product

##### Add Member
When right-clicking on Product Teams, the Add Member selection should add a member to the product. This can follow one of two patterns:
- If a member is currently selected in the Members List Box then that member is added to the Product Team
- If a member is not currently selected in the Members List Box then a prompt should appear that provides the ability to enter the member to be added to the Product Team.

The Add Product Team selection should be disabled any other time the right-click context menu is opened if it is not on a Product Team

#### Members List Box
This is a list box that is generated from the list of users sync-ed from GitLab. It does not provide any editing capabilities. Members in the Members List Box should be able to be dragged from the Members List Box to Product Teams to be assigned to those teams. 

### The Editting Pane
The Editting Pane for the PI Planning View is significantly more complex than and Backlog View. The goal of this pane is to provide the ability for Product Owners the ability to modify values for members of their team to calculate the capacity of their team on an iteraiton by iteraiton basis. It also provides a roll-up of the number of points currently allocated to each of their engineers through the assigned GitLab stories in the Backlog.

The Editting Pane will consit of three sections laid out from top-to-bottom:
- The Capacity Planning Spreadsheet Title Section
- The Capacity Planning Spreadsheet Seciton
- The Capacity Planning Modification Section

#### The Capacity Planning Spreadsheet Title Section
This seciton will contain two things: 
- A Read-Only text label describing the Data Set being viewed
- A Drop-down to select the Data Set populated within the Capacity Planning Spreadsheet Section. For the initial implementation, the drop-down will only contain one option: Capacity
    - In future releases, the drop-down will change what data is displayed in The Capacity Planning Spreadsheet Seciton
    

#### The Capacity Planning Spreadsheet Seciton
This seciton displays the data for the currently selected item in the Team Composition Tree View. The data displayed varies depending on the item selected within the Team Composition Tree View.

the applciaiton will have to calculate it dynamically. The application should maintain a database of loads. When stories are modified with the Backlog view, the values should be updated so that they can be populated when transitioning to the view.

##### General Layout
For the Capacity view inside the Capacity Planning Spreadheet, the layout is as follows:
- The first row will contain the titles of each column. The first coulmn will be one the Tree View Objects currently populated into the table. Each of the other columns will contain the GitLab Iterations.
- The second row will contain sub-columns within the main columns to create sub-data fields of the columns. The Members column will not contain any sub-columns. The Iteration columns will contain a "Capacity" and a "Load" sub-column.
    - The "Capacity" sub-column will display the number of points allocated to the associated member for that iteration
    - The "Load" sub-column will display the number of points currently assigned to that member in the GitLab backlog for that iteration
- Each successive row will represent an object from the Tree view. The specific rows displayed will vary as follows:
    - When a Team Member is selected in the Tree View, the first column title will be re-named to "Member". The table will only contain one row for the selected Team Member containing the capacity data for that member.
    - When a Product Team is selected in the Tree View, the first column title will be re-named to "Team Members" and multiple rows will be displayed for each child of the Product Team. Each row will contain the capacity data for the corresponding member.
    - When a Product is selected in the Tree View, the first column title will be re-named to "Product Teams" and each row will contain the roll-ed up data of the Product Team's members.

#### The Capacity Planning Modification Section
This section will provide the ability to modify the following values to drive the capacity calculations in the Capacity Planning Spreadsheet:
- PTO: The number of days a member is taking for the iteration. This field will enforce that the number value entered is in the range [0, num_sprint_days] where num_sprint_days is the number of buisness days in the sprint.
- Allocation %: The percentage of the members time that is allocated to that team. This field will enforce that the value entered is in the range[0% to 100%]. The user should not have to enter the % sign. That should be appended automatically.
- Velocity Factor: A modifier to allow the Product Owner to tune the capacity for a specific member. This field will enforce that the value entered is in the range[0% to 100%]. The user should not have to enter the % sign. That should be appended automatically.
- Utilization Factor: A global modifier to allow the Product Manager to tune the capacity for the overall Product. This field will enforce that the value entered is in the range[0% to 100%]. The user should not have to enter the % sign. That should be appended automatically.

The Utilization Factor is global and thus is set for all views.

The PTO, Allocation % and Velocity Factors should only be enabled when viewing either a Product Team, or an Member. They should be dispabled when viewing a Product. These values are unique to a specific cell within the table. When either a capacity or load cell is selected within the table, the PTO, Allocation % and Velocity Factors should be set to the values contained within the model for that iteration/member combination. These values are used to calculate the value displayed within the Capacity.

The formula for calculating an individual capacity cell value is: (DaysInSprint - PTO) * Allocation % * Velocity Factor * Utilization Factor.
