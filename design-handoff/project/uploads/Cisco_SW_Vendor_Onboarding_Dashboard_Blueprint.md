# Cisco Software Center — 3rd Party Vendor Onboarding
## Pipeline Visibility Blueprint

**Prepared for:** Business VP, Head of Sales Operations
**Scope:** Dashboard design · Data architecture · Field data-collection template
**Source material:** `Riya_job_extracted.numbers` — `stages` worksheet (12 stages / ~50 activities) and `sample status` worksheet (22 live projects)

---

## 1. Executive summary

- **The problem is not reporting, it is the data shape.** The current tracker is a *wide* sheet — one column per vendor, one row per activity, values overwritten in place. It answers "where is Rafay today?" It cannot answer "how long does Legal usually take?" or "how many vendors entered last quarter?", because **history is destroyed on every update**.
- **The single highest-value change** is to move from a status *snapshot* to a status *event log*: one row every time a stage starts, completes, or gets blocked. Cycle time, WIP, throughput and chokepoints then all fall out of the same table for free.
- **Recommended stack:** Microsoft Forms → Excel/SharePoint List → Power BI. No code, no server, no IT ticket. Maintained by one Sales Ops analyst in ~2 hrs/month. (Smartsheet is the equally valid alternative — see §5.)
- **Recommended cadence:** event-driven updates (submit when something changes) plus a mandatory Friday "no change" confirmation. This is lighter than weekly full-status reporting *and* produces better data.
- **Dashboard = 3 tabs:** Executive (VP), Bottleneck (Sales Ops Head), Project Detail (working team). Deliberately no more.

---

## 2. Modelling the pipeline

### 2.1 The 12 stages

Extracted verbatim from the `stages` worksheet, with SLA and dependency assumptions layered on. **Everything in the "SLA" and "Depends on" columns is a proposal to be validated — see §8.**

| # | Stage | Track | Depends on | Proposed SLA (calendar days) |
|---|---|---|---|---|
| 1 | Legal | Commercial | — (entry) | 20 |
| 2 | Documentation | Product | — (entry, parallel) | 15 |
| 3 | PID Preparations | Product | — (entry, parallel) | 10 |
| 4 | NPI Kickoff | Governance | 1, 2, 3 | 5 |
| 5 | PID Creation | Product | 4 | 12 |
| 6 | PID Setups | Product | 5 | 15 |
| 7 | Supply Chain Setup | Supply Chain | 5 | 12 |
| 8 | CCW Config & Testing | Systems | 6, 7 | 12 |
| 9 | Fulfillment | Systems | 6 | 15 |
| 10 | ORR (Orderability Readiness Review) | Gate | 8, 9 | 7 |
| 11 | Orderable in Production CCW | Gate | 10 | 5 |
| 12 | Post Orderable | Closeout | 11 | 10 |

- **Three parallel entry stages** (Legal, Documentation, PID Preparations) converge on **NPI Kickoff**, which is the first true gate.
- **Two parallel mid-pipeline tracks** (CCW Config & Testing / Fulfillment) converge on **ORR**, the second true gate.
- **Critical path length ≈ 89 days (~13 weeks)** for a New NPI under the SLAs above. Use this as the baseline commitment to the business until real data replaces it.
- **Gates are where queues form.** NPI Kickoff and ORR are the two places to instrument most carefully — a project blocked here is blocking *two or three upstream tracks* at once.

### 2.2 Stage applicability by project type

The tracker carries five project types (`New NPI`, `Sustaining NPI`, `EOL`, `EOS`, `Price Change`). They do **not** all run all 12 stages, so a single "% complete" across all projects is misleading. Proposed applicability matrix:

| Stage | New NPI | Sustaining NPI | Price Change | EOL / EOS |
|---|---|---|---|---|
| Legal | ✓ (S+ only) | ○ | ○ | ○ |
| Documentation | ✓ | ✓ | ○ | ✓ |
| PID Preparations | ✓ | ✓ | ○ | ○ |
| NPI Kickoff | ✓ | ✓ | ○ | ○ |
| PID Creation | ✓ | ✓ | ○ | ○ |
| PID Setups | ✓ | ✓ | ✓ | ○ |
| Supply Chain Setup | ✓ | ✓ | ○ | ✓ |
| CCW Config & Testing | ✓ | ✓ | ✓ | ✓ |
| Fulfillment | ✓ | ✓ | ○ | ○ |
| ORR | ✓ | ✓ | ○ | ○ |
| Orderable in Production CCW | ✓ | ✓ | ✓ | ✓ |
| Post Orderable | ✓ | ✓ | ✓ | ✓ |

✓ = required · ○ = typically Not Applicable

- **Implication for the dashboard:** progress % must be calculated against *applicable* stages for that project type, never against a fixed 12.
- Note the `stages` worksheet already flags Legal as *"mostly applicable for S+ offers"* — the S+ / Not-S+ / EA / Special Projects grouping in the tracker header should become a first-class **Portfolio** dimension.

### 2.3 Pipeline entry and exit — define these once, in writing

- **Entry (pipeline "in"):** date the project record is created in the tracker — i.e. first stage moves to In Progress.
- **Exit — success:** date Stage 11 *Orderable in Production CCW* completes. This is the commercially meaningful exit; Post Orderable is administrative tail.
- **Exit — attrition:** project set to `Cancelled` or `On Hold >90 days`. **Today there is no way to record this**, so the pipeline looks like it has no leakage. Add a project-level status field (§6).
- **WIP:** projects with ≥1 stage In Progress and not yet exited.

---

## 3. Dashboard design

### Tab 1 — Executive View (Business VP)
Answers: *how many in, how many out, how many stuck, are we on time?*

- **KPI strip (5 tiles):** Active projects in pipeline · Entered this quarter · Went orderable this quarter · Median days to orderable (last 90 days) · % projects past target orderability date
- **Pipeline funnel / stage bar** — count of projects currently sitting in each of the 12 stages, left to right. Bar colour = health (green on-track, amber at-risk, red over-SLA). *This is the "how many are in process and which stage" answer in one object.*
- **Entries vs. exits by month** — clustered column (entered / exited) with a line for net WIP. Shows whether the pipeline is filling faster than it drains.
- **Portfolio mix donut** — S+ / Not S+ / EA / Special Projects.
- **Slicers:** quarter, project type, portfolio, BU Ops POC.

### Tab 2 — Bottleneck / Flow View (Sales Ops Head)
Answers: *where is the pipeline choking and why?*

- **Chokepoint bubble chart (the centrepiece).** X = median days in stage · Y = number of projects currently in that stage · bubble size = number of projects over SLA in that stage. **Top-right = the chokepoint.** One glance, no interpretation needed.
- **Stage cycle-time bar** — median days per stage, with the SLA drawn as a reference marker so overruns are visible without arithmetic. Use median, not mean; a single 200-day legal negotiation will wreck a mean.
- **Aging WIP heatmap** — rows = stages, columns = age buckets (0–7 / 8–14 / 15–30 / 30+ days). Red cells in the 30+ column are the escalation list.
- **Blocker register** — table of every currently-blocked stage: project, stage, owner, days blocked, blocker reason, blocker owner. Sorted by days blocked descending. This is the VP's meeting agenda.
- **Cumulative flow diagram** (optional, analyst-facing) — stacked area of WIP by stage over time. Widening bands = growing queues.

### Tab 3 — Project Detail (working team)
Answers: *what exactly is happening on this vendor?*

- **Gantt / swimlane per project** — 12 stage bars, planned vs. actual, dependency arrows, today-line.
- **Target vs. actual variance** — slip in days per stage. The current tracker already captures *Target Date* and *Current Date*; this is the payoff for that discipline.
- **Activity checklist** — the ~50 sub-activities with owner and status, collapsed by stage.
- **Owner load view** — projects × stages by POC role (BU Ops, BUPM, BUC, CE, S+, Rev Rec, Export, Tax, Renewals) to spot person-level capacity constraints. In the sample data one BU Ops POC appears against 18 of 22 projects — that is itself a chokepoint.

### Design principles to hold the line on
- **One question per visual.** If a chart needs a paragraph of explanation it does not belong on Tab 1.
- **Colour means health, nothing else.** Never use colour for category and status in the same chart.
- **Every number is clickable through to the project list.** VPs ask "which ones?" within 10 seconds.
- **Show data freshness.** A "last updated" timestamp and an update-compliance % (projects updated in the last 7 days) on every tab. A stale dashboard that looks fresh is worse than no dashboard.

---

## 4. Metric definitions (agree these before building)

| Metric | Definition | Notes |
|---|---|---|
| Stage cycle time | `actual_end − actual_start` per project-stage | Median. Exclude Not Applicable stages. |
| Stage wait time | `actual_start − (max actual_end of predecessors)` | The queue, distinct from the work. Often the real chokepoint. |
| Time to orderable | Stage 11 end − project entry date | The headline VP number. |
| WIP | Projects with ≥1 In Progress stage, not exited | Point-in-time. |
| Throughput | Projects reaching Stage 11 per month | |
| On-time % | Projects hitting target orderability date | Requires target date at intake — mandatory field. |
| Blocked days | Cumulative days in `Blocked` status | Distinguish from In Progress or averages lie. |
| Update compliance | % of active projects with an event in last 7 days | Data-quality guardrail. |

**Critical distinction:** *cycle time* (how long the work takes) vs. *wait time* (how long it sits in a queue before anyone touches it). Most pipelines of this kind are 60–80% wait. If the dashboard only shows cycle time it will point at the wrong fix — hiring more people, when the answer is removing an approval queue.

---

## 5. Architecture

### 5.1 Recommended: Microsoft 365 (no-code)

```
   MS Form                 Excel workbook on            Power BI               Power BI /
"Stage Update"   ───────►  SharePoint (auto-fed)  ───►  Desktop (build)  ───►  SharePoint page
   (field entry)           = single source of truth     scheduled refresh       (VP consumption)
                                    ▲
   MS Form                          │
"New Project Intake" ───────────────┘
```

**Why this shape:**
- Forms created *from* an Excel workbook stored in SharePoint write responses straight into that workbook. **No Power Automate flow, no connector, no glue code to maintain.**
- Power BI connects to that workbook and refreshes on a schedule (daily 7am is plenty).
- Everything sits inside licences Cisco already owns. No new procurement, no security review for a new SaaS vendor.

**Build effort:** ~3 days for a competent analyst. **Ongoing maintenance:** adding a stage or a dropdown value = editing a reference tab in Excel. Genuinely non-technical.

**Guardrails so it does not rot:**
- The workbook lives in **one** SharePoint document library with edit rights for 2–3 named Sales Ops people. Everyone else is read-only. Uncontrolled copies are how these die.
- **Never delete or reorder columns** in the response tab — it breaks the form link and the Power BI query silently.
- Reference tabs (Stages, Project Types, Owners) drive the dropdowns; edit there, never in the log.
- One named **data steward** owns the weekly chase for missing updates. This role is non-optional — the dashboard is only as good as Friday afternoon compliance.

### 5.2 Alternative: Smartsheet

Worth choosing if Sales Ops is already a Smartsheet shop, since form, sheet, automated reminders and dashboards are one product with no integration seam at all.
- **Pros:** built-in automated reminder workflows ("nudge the owner if a stage has no update in 7 days"), native Gantt with dependencies, dashboards included, genuinely non-technical.
- **Cons:** per-licence cost; weaker analytics than Power BI for cycle-time distributions; harder to blend with other Cisco data later.

### 5.3 Alternative: Google Workspace
Google Forms → Sheets → Looker Studio. Fastest to stand up (half a day) and free, but least likely to satisfy Cisco IT for anything containing vendor commercial terms. Fine for a 4-week pilot to prove the metrics matter before investing in 5.1.

### 5.4 What to deliberately avoid
- **A custom web app or database.** The brief requires non-technical maintenance; the moment it needs a developer it becomes a dependency and then a liability.
- **Rebuilding the wide tracker in a nicer tool.** The shape is the problem, not the tool.
- **Boiling the ocean on sub-activities in phase 1.** Start at the 12-stage level. Add the ~50 sub-activities only once stage-level compliance is >90%.

---

## 6. Data model

Four tables. Only the third is written to regularly.

**`dim_project`** — one row per vendor project (created once at intake)
`project_id` · `vendor_name` · `project_type` · `portfolio` · `entry_date` · `target_orderability_date` · `project_status` (Active / On Hold / Cancelled / Orderable / Closed) · `bu_ops_poc` · `bupm` · `buc` · `ce` · `s_plus_poc` · `revrec_poc` · `export_poc` · `tax_poc` · `renewals_poc` · `notes`

**`dim_stage`** — reference, 12 rows, edited almost never
`stage_id` · `stage_no` · `stage_name` · `track` · `predecessor_ids` · `sla_days` · `applicable_new_npi` · `applicable_sustaining` · `applicable_price_change` · `applicable_eol_eos`

**`fact_stage_event`** — the event log. **This is the whole system.** One row per change.
`event_id` · `timestamp` · `project_id` · `stage_id` · `event_type` (Started / Completed / Blocked / Unblocked / Marked N/A / No Change) · `status_after` · `pct_complete` · `planned_end_date` · `actual_date` · `stage_owner` · `blocker_flag` · `blocker_reason` · `blocker_owner` · `expected_unblock_date` · `comment` · `submitted_by`

**`fact_activity_status`** (phase 2, optional) — sub-activity granularity
`project_id` · `stage_id` · `activity_name` · `owner_role` · `status` · `date` · `reference_id`

- Cycle time = `Completed.actual_date − Started.actual_date`, derived, never entered by hand. **Never ask a human to type a duration** — they will estimate, and the number becomes fiction.
- Keep every event row forever. Storage is free; history is not recoverable once lost.

---

## 7. Field data-collection: the report form

### 7.1 Form A — New Project Intake
Submitted once, when a vendor enters the pipeline. ~2 minutes.

| Field | Type | Required | Notes |
|---|---|---|---|
| Vendor / project name | Text | ✓ | |
| Project type | Dropdown: New NPI / Sustaining NPI / Price Change / EOL / EOS | ✓ | Drives stage applicability |
| Portfolio | Dropdown: S+ / Not S+ / EA – 3rd Party SW / Special Project | ✓ | |
| Entry date | Date | ✓ | Defaults to today |
| Target orderability date | Date | ✓ | **The single most important field on the form.** No target = no on-time metric. |
| BU Ops POC | Dropdown | ✓ | |
| BUPM / BUC / CE / S+ POC | Dropdown | | |
| Rev Rec / Export / Tax / Renewals POC | Dropdown | | Mostly standing assignments |
| Expected revenue band | Dropdown | | Lets the VP see the pipeline weighted by value, not just count |
| Notes | Long text | | |

### 7.2 Form B — Stage Update *(the workhorse)*
Submitted **whenever a stage changes state**, not on a calendar. ~30 seconds. Branching keeps it short.

| Field | Type | Required | Notes |
|---|---|---|---|
| Project | Dropdown (active projects) | ✓ | |
| Stage | Dropdown (12 stages) | ✓ | |
| What happened? | Started / Completed / Blocked / Unblocked / Not Applicable / No change | ✓ | Drives everything downstream |
| Date it happened | Date | ✓ | **Actual date, not submission date** — allows honest back-dating |
| Stage owner | Dropdown | ✓ | |
| % complete | 0 / 25 / 50 / 75 / 100 | | Only shown if "Started" |
| Blocker reason | Dropdown: Vendor response · Cisco approval · Legal/contract · System/tool · Resource capacity · Dependency not met · Other | *if Blocked* | **Categorised, not free text.** Free-text blockers cannot be counted, and counting them is the point. |
| Blocker owner | Dropdown | *if Blocked* | |
| Expected unblock date | Date | *if Blocked* | |
| Comment | Short text | | 200 char cap — forces brevity |
| Submitted by | Auto (SSO) | ✓ | |

### 7.3 Form C — Friday confirmation
- Every Friday, each BU Ops POC confirms their active projects: either they have already logged events this week, or they submit "No change" for each. Takes under a minute.
- This exists purely to distinguish **"nothing happened"** from **"nobody updated it."** Without it, a stalled project and an unreported project look identical, and the dashboard quietly lies about your chokepoints.

### 7.4 Making the field team actually use it
- **Under 60 seconds or it will not happen.** Ruthlessly cut fields; every extra one costs compliance.
- **Only ask for what cannot be derived.** Never ask for duration, % of overall project, or "days delayed" — all computable.
- **Pre-fill everything possible** — SSO for submitter, today's date as default, project dropdown filtered to active only.
- **Give the team back something they want.** Put a "my projects, my overdue stages" view on the dashboard. Reporting that only feeds upward gets filled in badly.
- **Publish the compliance %** by POC on Tab 1. Visibility does more than reminder emails.
- **Automate the nudge** — Power Automate or Smartsheet reminder when a stage has had no event for 7 days.

---

## 8. Assumptions requiring client validation

1. **Stage dependencies (§2.1).** Derived from the ordering of the `stages` worksheet, not from documented process. The sample data for Rafay shows PID Preparations completing *before* Legal, so the real process may be more parallel than modelled.
2. **SLA days (§2.1).** Placeholders only. Best practice: run 8 weeks of real event data, set SLAs at the observed 75th percentile, then tighten.
3. **Stage applicability by project type (§2.2).** Inferred from the `EOS` / `Price Change` column headers in the `stages` worksheet.
4. **Exit = Stage 11 complete.** Post Orderable (RCE RRM confirmation) treated as administrative tail.
5. **No cancellation data exists today.** Attrition rate is currently unknowable; the tracker has no cancelled or on-hold state.
6. **~22 concurrent projects** at present. If volume were to exceed ~100 the SharePoint/Excel approach should be revisited.

---

## 9. Phased rollout

| Phase | Duration | Deliverable | Success test |
|---|---|---|---|
| 0 — Align | Week 1 | Sign off stage dependencies, SLAs, applicability matrix, exit definition | Sales Ops Head and BU Ops leads agree in one workshop |
| 1 — Instrument | Weeks 2–3 | Forms + workbook live; backfill current 22 projects to their current stage | 100% of active projects have a record |
| 2 — Baseline | Weeks 4–8 | Collect events; Tab 1 and Tab 3 live | >90% weekly update compliance |
| 3 — Optimise | Weeks 9–12 | Tab 2 live with real cycle times; reset SLAs from observed data | Chokepoint identified and one process fix agreed |
| 4 — Deepen | Quarter 2 | Sub-activity tracking; revenue weighting; vendor-facing SLA view | Median time-to-orderable trending down |

**The honest caveat:** the dashboard does not fix the pipeline. It makes the chokepoint undeniable, which is what unlocks the fix. Expect the first real insight around week 6, once there is enough event history for medians to mean anything.

---

## 10. Claude Design prompt

*Copy the block below into Claude Design as a single prompt. It uses illustrative data consistent with the sample tracker so the layout can be reviewed before real data exists.*

---

**PROMPT — Cisco Software Center: 3rd Party Vendor Onboarding Pipeline Dashboard**

Design an interactive executive dashboard for Cisco's Software Center, which onboards third-party software vendors so their products can be sold through Cisco and bundled with Cisco hardware. The audience is a Business VP and the Head of Sales Operations — senior, time-poor, non-technical. They want a top-level view of pipeline flow and, critically, to see where the pipeline is choking.

**Structure: three tabs.**

**TAB 1 — EXECUTIVE VIEW**

Top row, five KPI tiles with large numerals, a small label and a trend arrow with prior-period comparison:
- Active Projects in Pipeline — 22 (▲ 3 vs last quarter)
- Entered This Quarter — 7
- Went Orderable This Quarter — 4
- Median Days to Orderable — 96 (▲ 11, worsening)
- Past Target Date — 27% (6 of 22)

Below, a full-width horizontal stage-flow chart — 12 stages left to right, each a vertical bar whose height is the count of projects currently sitting in that stage. Colour each bar by health: green = all within SLA, amber = at least one project approaching SLA, red = at least one project over SLA. Label each bar with the count. Use this data:
Legal 2 (green) · Documentation 3 (amber) · PID Preparations 1 (green) · NPI Kickoff 4 (red) · PID Creation 2 (green) · PID Setups 3 (amber) · Supply Chain Setup 1 (green) · CCW Config & Testing 2 (green) · Fulfillment 1 (green) · ORR 2 (red) · Orderable in Production CCW 1 (green) · Post Orderable 0 (grey)

Bottom row, two panels side by side:
- Left, "Pipeline Flow by Month": clustered columns for Entered and Exited, plus a line for Active WIP. Mar: 5 in / 3 out / 18 WIP · Apr: 4 / 5 / 17 · May: 6 / 2 / 21 · Jun: 3 / 4 / 20 · Jul: 7 / 4 / 23 · Aug: 2 / 3 / 22
- Right, "Portfolio Mix": donut — S+ Projects 9, EA 3rd Party SW 6, Not S+ 4, Special Projects 3

Filter bar across the top: Quarter, Project Type (New NPI / Sustaining NPI / Price Change / EOL / EOS), Portfolio, BU Ops POC.

**TAB 2 — BOTTLENECK VIEW**

Hero visual, top half, full width — "Where the Pipeline is Choking": a bubble chart. X axis = median days spent in stage (0–45). Y axis = number of projects currently in that stage (0–5). Bubble size = number of projects over SLA. Annotate the top-right quadrant "CHOKEPOINTS" with a subtle tinted background. Label each bubble with its stage name. Data as (stage, median days, current count, over-SLA count):
NPI Kickoff 24, 4, 3 · ORR 19, 2, 2 · Documentation 21, 3, 1 · PID Setups 17, 3, 1 · Legal 28, 2, 1 · PID Creation 11, 2, 0 · CCW Config & Testing 13, 2, 0 · Supply Chain Setup 10, 1, 0 · Fulfillment 14, 1, 0 · PID Preparations 8, 1, 0 · Orderable in Production CCW 4, 1, 0 · Post Orderable 9, 0, 0

Bottom left, "Cycle Time vs SLA": horizontal bars of median days per stage with a vertical tick marking the SLA; bar turns red where it overruns. SLAs: Legal 20, Documentation 15, PID Preparations 10, NPI Kickoff 5, PID Creation 12, PID Setups 15, Supply Chain 12, CCW 12, Fulfillment 15, ORR 7, Orderable 5, Post Orderable 10.

Bottom right, "Blocked Projects": a compact table, red left-edge accent, sorted by days blocked descending:
Nutanix Upgrade / NPI Kickoff / 31 days / Vendor response · Rubrik / ORR / 22 days / Cisco approval · SLES / Documentation / 18 days / Vendor response · DDN / NPI Kickoff / 14 days / Dependency not met · EA: Qumulo / PID Setups / 9 days / System/tool

**TAB 3 — PROJECT DETAIL**

A project selector at top (default: Rafay — New NPI — S+ — Target orderability 2026-07-25).
A horizontal Gantt: 12 stage rows, planned bar in light grey behind actual bar in solid colour, dependency arrows between stages, a vertical "today" line, and a green tick or red flag at each row end for on-time or slipped. Complete stages solid, in-progress hatched, not-applicable greyed with a diagonal fill.
Beneath, a "Target vs Actual" variance bar chart per stage — bars right of zero in red for slip, left in green for early.
Right rail: project metadata card (type, portfolio, entry date, target date, POCs by role) and a collapsible activity checklist grouped by stage.

**VISUAL DIRECTION**

Clean, dense, executive — closer to a financial terminal than a marketing page. Light background. One restrained accent colour for interactive elements. Semantic colour used *only* for health: green on-track, amber at-risk, red over-SLA, grey not-applicable. Never use colour for category and status in the same chart. A clear typographic hierarchy — KPI numerals large, chart labels small and quiet. Generous whitespace between panels, tight within them. Every visual carries a plain-English title that states the question it answers. Show "Data last refreshed" and "Update compliance: 91%" discreetly in the header. Responsive down to laptop width. No decorative illustration, no gradients, no drop shadows.

---

*End of prompt.*
