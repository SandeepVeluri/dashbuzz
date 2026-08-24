# Offer Portfolio Status Dashboard

A live dashboard for Cisco Compute BU's third-party software vendor
onboarding pipeline, hosted on GitHub Pages -- no server, no database.
Analysts report updates in plain language to an AI chat assistant; the
dashboard rebuilds itself automatically within a minute or two of any
update landing in this repo.

```
Analyst has a conversation      AI assistant (Codex/ChatGPT,       GitHub Actions        GitHub Pages
(email / meeting / verbal) ──►  or Claude) reads               ──►  rebuilds        ──►  serves the
                                 docs/INTAKE_PROTOCOL.md,             site/index.html         static dashboard
                                 resolves the update against          from data/*.csv
                                 data/dim_project.csv +
                                 data/dim_stage.csv, shows a
                                 one-line draft, and on
                                 confirmation calls
                                 scripts/log_update.py, which
                                 validates + derives + commits
                                 to data/events.csv
```

## Repo layout

```
data/
  dim_project.csv        one row per offer -- vendor, type, portfolio, POCs, target date
  dim_stage.csv           the 12 pipeline stages -- SLA days, dependencies, applicability by project type
  dim_activity.csv        reference list of sub-activities per stage, used for fuzzy matching only
  events.csv               the event log -- the only table anyone (human or AI) appends to
  child_tasks_seed.csv     phase-1 backfill of sub-activity status (see "What's deliberately deferred" below)
scripts/
  derive.py                shared derivation logic: health/SLA, dependency checks, progress, blocked register
  log_update.py             the intake CLI an AI assistant calls to append a validated event
  build_dashboard.py        regenerates site/index.html from data/*.csv
templates/
  dashboard_template.html   the dashboard shell (visual design), with a data placeholder the build fills in
docs/
  INTAKE_PROTOCOL.md         the instructions doc an AI assistant loads to become "the form"
.github/workflows/deploy.yml  builds + deploys to GitHub Pages on every push to data/**
design-handoff/               the original Claude Design export this dashboard's look was built from
```

## How an update actually gets in

There is no web form. An analyst opens a chat with whatever AI assistant
they have access to (Codex/ChatGPT is what this was built for; Claude works
identically) in a project that has `docs/INTAKE_PROTOCOL.md` loaded as
instructions and shell access to a clone of this repo, and just talks:

> "Legal signed off on Rafay yesterday, and Quali's PID setups is
> basically done, just waiting on export review."

The assistant resolves that against the real offer/stage lists, shows a
one-line draft per event, and -- once the analyst confirms -- runs:

```
python scripts/log_update.py --batch-json updates.json --commit --push
```

`log_update.py` validates the input, computes what it implies (health,
dependency consistency, progress), and is the *only* thing that ever writes
to `data/events.csv`. See `docs/INTAKE_PROTOCOL.md` for the full contract.

Pushing to `main` triggers `.github/workflows/deploy.yml`, which runs
`scripts/build_dashboard.py` and deploys the result to GitHub Pages. Nothing
in that path needs a server, a database, or IT-provisioned infrastructure --
GitHub Actions is the backend.

## Running the build locally

```
python3 scripts/build_dashboard.py    # writes site/index.html
python3 -m http.server --directory site 8000
```

## One-time repo setup

1. Settings -> Pages -> Build and deployment source: **GitHub Actions**.
2. Restrict write access to the 2-3 Sales Ops analysts who submit updates
   (and whatever token/account their AI assistant sessions push with);
   everyone else gets read/Pages access only.
3. Confirm with your GitHub admin that Pages is enabled for private/internal
   repos on this Cisco GitHub Enterprise account -- it's an org-level
   setting on some plans.
4. `data/dim_project.csv` and `data/dim_stage.csv` are edited by hand, rarely
   (a new offer onboarded, an SLA renegotiated) -- never by the intake
   assistant.

## Why an event log instead of an editable status sheet

The dashboard used to be backed by a wide tracker: one column per vendor,
values overwritten in place on every update. That shape can answer "where is
Rafay today" but not "how long does Legal usually take" or "how many
projects entered last quarter," because **history is destroyed on every
edit**. `data/events.csv` is append-only -- one row every time a stage
starts, completes, or gets blocked -- so cycle time, throughput, and
bottlenecks all fall out of the same table for free, and nothing a person
typed six weeks ago silently disappears.

## What's deliberately deferred

- **Sub-activity (child task) tracking** stays a periodic snapshot
  (`data/child_tasks_seed.csv`), not a second event log. Instrumenting ~50
  activities per stage before stage-level compliance is solid would cost more
  analyst time than it returns. Revisit once stage-level updates are reliably
  >90% current.
- **A second "bottleneck" view** (chokepoint bubble chart, cycle-time vs SLA,
  cumulative flow) becomes cheap once a few months of real event history
  exist, but isn't built here -- the dashboard shipped in this repo is the
  Gantt/milestone view the design was actually signed off on. `derive.py`
  already computes everything that view would need (`blocked_register`,
  per-stage health) if and when it's wanted.
- **Stage dependencies and SLA days in `data/dim_stage.csv` are proposals**,
  not confirmed process. Validate them with the BU Ops leads before treating
  the health colours as gospel -- see the blueprint in
  `design-handoff/project/uploads/Cisco_SW_Vendor_Onboarding_Dashboard_Blueprint.md`
  section 8 for the full list of assumptions.
