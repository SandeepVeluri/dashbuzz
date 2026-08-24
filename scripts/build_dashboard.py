#!/usr/bin/env python3
"""
build_dashboard.py -- regenerates index.html from data/*.csv + templates/dashboard_template.html.

Runs in GitHub Actions on every push that touches data/**, and can be run
locally the same way. It is the only place the raw CSV tables get turned into
the JSON blob the dashboard's JS reads, and the only place the offer/type
<select> options get regenerated to match real active projects.

No network calls, no LLM calls -- pure, deterministic, and safe to run in CI.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "templates" / "dashboard_template.html"
# Only this directory gets published to GitHub Pages (see .github/workflows/deploy.yml) --
# keeping the build output separate from data/ and scripts/ means the source CSVs and
# tooling never end up served on the public Pages URL.
OUTPUT_PATH = REPO_ROOT / "site" / "index.html"

HEALTH_BADGE_ORDER = {"Blocked": 0, "Over SLA": 1, "At Risk": 2, "On Track": 3, "Not Started": 3, "Not Applicable": 4}
TITLE_BY_TYPE = {"New NPI": "Initial onboarding", "Sustaining Change": "Sustaining update"}


def build_payload(today: dt.date) -> dict:
    stages = derive.load_stages()
    projects = [p for p in derive.load_projects() if p.project_status == "Active"]
    events = derive.load_events()
    child_tasks_raw = derive.load_child_tasks()
    stage_by_id = {s.stage_id: s for s in stages}

    rollups = [derive.rollup_project(p, stages, events, today) for p in projects]

    portfolio = []
    milestones = []
    pocs = []
    for r in rollups:
        p: derive.Project = r["project"]
        portfolio.append(dict(
            Offer=p.offer, Vendor=p.vendor, Workstream=p.project_id, Type=p.project_type,
            Title=TITLE_BY_TYPE.get(p.project_type, "Onboarding"), Owner=p.poc["bu_ops"] or "Not assigned",
            Health=r["health"], Status=r["status"], Progress=round(r["progress"], 4),
            TargetDate=p.target_orderability_date or None, LastUpdated=r["last_updated"] or None,
        ))
        pocs.append(dict(
            Offer=p.offer, Vendor=p.vendor, BUOperations=p.poc["bu_ops"] or "Not assigned",
            BUPM=p.poc["bupm"] or "Not assigned", BUC=p.poc["buc"] or "Not assigned",
            CE=p.poc["ce"] or "Not assigned", SPlus=p.poc["s_plus"] or "Not assigned",
            RevRec=p.poc["revrec"] or "Not assigned", Export=p.poc["export"] or "Not assigned",
            Tax=p.poc["tax"] or "Not assigned", Renewals=p.poc["renewals"] or "Not assigned",
        ))
        for stage in r["applicable_stages"]:
            st = r["stage_states"][stage.stage_id]
            blocker = ""
            if st["status"] == "Blocked":
                blocker = st["blocker_reason"] or st["comment"] or "Blocked -- reason not categorised"
            next_action = ""
            if st["status"] == "Blocked":
                next_action = f"Resolve: {st['blocker_reason'] or 'uncategorised blocker'}"
            elif st["status"] == "In Progress" and st["planned_end_date"]:
                next_action = f"Target {st['planned_end_date']}"
            milestones.append(dict(
                Offer=p.offer, Workstream=p.project_id, Order=stage.stage_no, Milestone=stage.display_name,
                Owner=st["owner"] or p.poc["bu_ops"] or "Not assigned", Status=st["status"],
                Progress=1 if st["status"] == "Complete" else 0,
                TargetDate=st["planned_end_date"] or p.target_orderability_date or None,
                ActualDate=st["actual_date"] if st["status"] == "Complete" else None,
                Blocker=blocker, NextAction=next_action,
            ))

    active_ids = {p.project_id for p in projects}
    child_tasks = []
    for t in child_tasks_raw:
        if t["project_id"] not in active_ids:
            continue
        stage = stage_by_id.get(t["stage_id"])
        if not stage:
            continue
        progress = t["progress"]
        child_tasks.append(dict(
            Workstream=t["project_id"], ParentMilestone=stage.display_name,
            TaskGroup=t["task_group"] or "", ChildTask=t["activity_name"],
            Owner=t["owner"] or "Not assigned", OwnerSource=t["owner_source"] or "",
            Status=t["status"] or "", Progress=(float(progress) if progress not in ("", None) else None),
            TargetDate=t["target_date"] or None, ActualDate=t["actual_date"] or None,
            SourceDetail=t["source_detail"] or "",
        ))

    last_refreshed = max((p["LastUpdated"] for p in portfolio if p["LastUpdated"]), default=None)
    compliance = derive.update_compliance_pct(projects, events, today)

    meta = dict(
        generatedAt=today.isoformat(),
        lastRefreshed=last_refreshed,
        updateCompliancePct=compliance,
        activeOfferCount=len(projects),
    )

    return dict(portfolio=portfolio, milestones=milestones, childTasks=child_tasks, pocs=pocs, meta=meta)


def worst_health_project(payload: dict) -> dict:
    return sorted(
        payload["portfolio"],
        key=lambda p: (HEALTH_BADGE_ORDER.get(p["Health"], 9), p["Offer"]),
    )[0]


def render_offer_options(payload: dict, default: dict) -> str:
    opts = []
    for p in sorted(payload["portfolio"], key=lambda p: p["Offer"]):
        sel = " selected" if p["Offer"] == default["Offer"] else ""
        opts.append(f'<option value="{p["Offer"]}"{sel}>{p["Offer"]}</option>')
    return "<select id=\"psd-offer-select\">" + "".join(opts) + "</select>"


def render_type_options(default: dict) -> str:
    npi_sel = " selected" if default["Type"] == "New NPI" else ""
    sus_sel = " selected" if default["Type"] == "Sustaining Change" else ""
    return (
        '<select id="psd-type-select">'
        f'<option value="New NPI"{npi_sel}>New NPI</option>'
        f'<option value="Sustaining Change"{sus_sel}>Sustaining change</option>'
        '</select>'
    )


def main() -> int:
    today = dt.datetime.now(dt.timezone.utc).date()
    payload = build_payload(today)

    if not payload["portfolio"]:
        print("warning: no active projects -- dashboard will render empty", file=sys.stderr)
        default = None
    else:
        default = worst_health_project(payload)

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = html.replace("__DASHBOARD_DATA_JSON__", json.dumps(payload, separators=(",", ":")))

    if default:
        html = re.sub(r'<select id="psd-offer-select">.*?</select>', render_offer_options(payload, default), html, count=1, flags=re.S)
        html = re.sub(r'<select id="psd-type-select">.*?</select>', render_type_options(default), html, count=1, flags=re.S)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH} ({len(html)} chars) with {len(payload['portfolio'])} active offers, "
          f"{len(payload['milestones'])} milestone rows, update compliance {payload['meta']['updateCompliancePct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
