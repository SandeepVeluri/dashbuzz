# Dashboard Summary Cards

_Started 2026-08-24 13:13 UTC_

---

## User

Continuing from "Dashboard redesign with Gantt chart".

## Assistant

We were refining the "Offer Portfolio Status Dashboard" — an interactive timeline view for tracking software vendor onboarding offers through their delivery lifecycle. The goal: a usable, consistent executive dashboard focused on timeline visibility and filterable status at a glance.

Decisions made along the way:
- Replaced the top 5 KPI cards with a full-year Gantt chart (fiscal year Aug–Jul, quarter-marked) because KPIs were redundant with dropdown counts.
- Merged "Portfolio status" and "Selected offer" cards into one unified control panel to eliminate duplicate filtering.
- Applied Material UI 3 design language: Manrope font, neutral warm palette (no blue), 16–20px rounded cards, 24px spacing, subtle elevation shadows.
- Removed all em dashes; switched to "N/A" and plain language throughout.
- Gantt bars now encode status (green = completed, yellow = ongoing) and type (solid = New NPI, hashed = Sustaining change) with a legend.
- Added multi-select type filter to group New NPI projects first, then Sustaining change.
- Implemented hover tooltips showing exact start–end dates on Gantt bars.
- Added left/right scroll buttons on the task/milestone list to page through a 3-item window of actions.

Current state: Gantt renders 13 projects across FY 2026 (Aug–Jul), filterable by project type, with quarter markings on the x-axis and legend. Task detail panel below shows selected offer's milestones, health/status, and POC info. Responsive layout holds at laptop width. All styling is Material 3 compliant; no blue in the first fold.

Open next step: wire the task scroll buttons fully and test the scroll offset on milestone list rendering.

Project files: Offer Portfolio Status Dashboard.html, _tmp_data.json

## User

add these cards on top - 
( N is the count ) 
1. active offers - N in portfolio
2. active workstreams
3. New NPI - N workstreams
4. Sustaining changes - N active
5. Status freshness - Jul 2, 2026 ( dates can change ) 

use CISCO brand colors for the dashboard

## User

Found issues — fixing…

## User

Found issues — fixing…

## Assistant

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: ready_for_verification]_

## User

i need to see what is done and what comes next in scheule outlook, currently only 3 tasks are shown and the scroll doesn't work. read the excel, if you don't have it then wait for me to send the file and only then star thinking of a better ui and make the changes then.

## Assistant

I don't have the source Excel file in the project — please send it and I'll rework the Schedule outlook UI (done vs. upcoming tasks, working scroll) based on the real data.

## User

"sheet 1" is the stages , Project status is how we will capture data to feed to the dashboard. now read the worksheet and identify best way to present schedule outlook section

## Assistant

_[tool: run_script]_

_[tool: run_script]_

_[tool: run_script]_

Global state doesn't persist across run_script calls — redoing extraction and reading workbook + shared strings in one shot.

_[tool: run_script]_

_[tool: run_script]_

_[tool: run_script]_

_[tool: grep]_

_[tool: grep]_

_[tool: grep]_

_[tool: grep]_

_[tool: read_file]_

_[tool: read_file]_

_[tool: grep]_

Now applying the redesign: a scrollable done/upcoming timeline list replacing the fixed 3-slot layout.

_[tool: str_replace_edit]_

_[tool: read_file]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

Now updating the JS: rewriting `renderSchedule` and the button wiring.

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: ready_for_verification]_

## User

Found issues — fixing…

## Assistant

_[tool: str_replace_edit]_

_[tool: ready_for_verification]_

Fixed — scroll buttons now use `behavior:"auto"` so they move the list immediately.

## User

can you club child task details inside schedule outlook - collapse the child task details inside schedule outlook

## Assistant

_[tool: read_file]_

_[tool: grep]_

_[tool: read_file]_

_[tool: str_replace_edit]_

Now wiring the toggle behavior and collapsing it on milestone change:

_[tool: str_replace_edit]_

_[tool: ready_for_verification]_

## User

show the green tick boxes only when the task is 100% complete, otherwise show yellow for inprogress or blank circle for not started.

## Assistant

_[tool: grep]_

_[tool: read_file]_

_[tool: grep]_

_[tool: run_script]_

_[tool: run_script]_

_[tool: run_script]_

_[tool: run_script]_

_[tool: grep]_

_[tool: grep]_

_[tool: str_replace_edit]_

_[tool: grep]_

_[tool: run_script]_

Adding the three visual states for the check indicator.

_[tool: str_replace_edit]_

Removing the old duplicate `.psd-check-pending` rule that's now superseded:

_[tool: str_replace_edit]_

Also need to update the initial static HTML milestone buttons (pre-JS-render) to match the new class scheme, and fix the initial state so they're not all green checks before JS runs.

_[tool: run_script]_

_[tool: ready_for_verification]_

## User

Found issues — fixing…

## Assistant

_[tool: grep]_

`workstream.Progress` (0-1 fraction) is available. Replacing the heuristic to use progress fraction × milestone count vs Order.

_[tool: str_replace_edit]_

_[tool: ready_for_verification]_

## User

PID setups is not complete as per the mock. but i can stil see the green check box. check the underlyng code and make the changes everywhere

## Assistant

_[tool: run_script]_

_[tool: grep]_

_[tool: str_replace_edit]_

Now also fixing the KPI card "Overall progress" and health tag for this milestone to stay consistent with the mock (they already use `useIllustration`, so that's fine). Verifying:

_[tool: ready_for_verification]_

