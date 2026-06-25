# LOCAL CONTEXT: PI PLANNING FEATURE

## Responsibility
Assisting Product Owners and Product Managers in estimating team capacity and verification of workloads during PI Planning.

## Layout & Components
1. **Tree View Column (`team_tree_pane.py`):**
   - Three-level hierarchy: **Product** -> **Product Team** -> **Member**.
   - Members cannot be direct children of Products.
   - Right-click actions: Add Product (always active), Add Product Team (active on Products only), Add Member (active on Product Teams only).
2. **Members List Box (`team_tree_pane.py`):**
   - Read-only list populated from GitLab users.
   - Supports drag-and-drop into Product Teams.
3. **Editing Pane (`pi_planning_view.py`, `spreadsheet_pane.py`, `metrics_editor_pane.py`):**
   - **Spreadsheet Title:** Title + Dropdown (initial selection: "Capacity").
   - **Spreadsheet Section:**
     - Row 1: Columns (Member/Team Members/Product Teams + GitLab Iterations).
     - Row 2: Sub-columns under Iteration ("Capacity" + "Load").
     - Rows dynamic based on selected tree item (Member: single member row, Product Team: all team members, Product: rolled up team data).
   - **Modification Section:**
     - Fields: PTO (PTO days in sprint business days range `[0, num_sprint_days]`), Allocation % (`[0, 100]`), Velocity Factor (`[0, 100]`), Utilization Factor (`[0, 100]`, global).
     - Modifiers only enabled when a Member or Product Team is selected (disabled when a Product is selected).

## Math & Formula
Individual capacity calculation:
`Capacity = (DaysInSprint - PTO) * (Allocation % / 100) * (Velocity Factor / 100) * (Utilization Factor / 100)`

## Local UI Rules
- Use only `tkinter` and `ttk` (no external UI libraries).
- Style overrides: Dropdowns must use high-contrast theme definitions for black-text readability.
