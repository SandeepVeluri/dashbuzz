"""
Shared derivation logic for the offer portfolio pipeline.

This module is the single place where "what does this data mean" gets decided:
SLA/health colour, dependency consistency, per-project progress %, and the
blocked register. Both `log_update.py` (the intake tool an AI assistant calls)
and `build_dashboard.py` (the GitHub Actions build) import this module, so a
number on the dashboard and a number an assistant reads back to an analyst are
always computed the same way.

Nothing in here talks to an LLM. It is plain, testable Python over the four
CSV tables in data/. Keep it that way -- derivation logic belongs in code that
can be unit tested, not in a prompt.
"""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

EVENT_TYPES = ["Started", "Completed", "Blocked", "Unblocked", "Not Applicable", "No Change", "Backfill Snapshot"]
BLOCKER_REASONS = ["Vendor response", "Cisco approval", "Legal/contract", "System/tool",
                    "Resource capacity", "Dependency not met", "Other"]


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def _read_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _to_bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


@dataclass
class Stage:
    stage_id: str
    stage_no: int
    stage_name: str
    display_name: str
    track: str
    predecessor_ids: list[str]
    sla_days: int
    applicable: dict  # project_type -> bool
    notes: str


@dataclass
class Project:
    project_id: str
    offer: str
    vendor: str
    project_type: str
    portfolio: str
    entry_date: str
    target_orderability_date: str
    project_status: str
    poc: dict
    notes: str


TYPE_TO_APPLICABILITY_COL = {
    "New NPI": "applicable_new_npi",
    "Sustaining Change": "applicable_sustaining",
    "Sustaining NPI": "applicable_sustaining",
    "Price Change": "applicable_price_change",
    "EOL": "applicable_eol_eos",
    "EOS": "applicable_eol_eos",
}


def load_stages() -> list[Stage]:
    stages = []
    for r in _read_csv("dim_stage.csv"):
        stages.append(Stage(
            stage_id=r["stage_id"],
            stage_no=int(r["stage_no"]),
            stage_name=r["stage_name"],
            display_name=r["display_name"],
            track=r["track"],
            predecessor_ids=[p for p in r["predecessor_ids"].split(";") if p],
            sla_days=int(r["sla_days"]),
            applicable={
                "New NPI": _to_bool(r["applicable_new_npi"]),
                "Sustaining Change": _to_bool(r["applicable_sustaining"]),
                "Price Change": _to_bool(r["applicable_price_change"]),
                "EOL": _to_bool(r["applicable_eol_eos"]),
                "EOS": _to_bool(r["applicable_eol_eos"]),
            },
            notes=r["notes"],
        ))
    return sorted(stages, key=lambda s: s.stage_no)


def load_projects() -> list[Project]:
    out = []
    for r in _read_csv("dim_project.csv"):
        out.append(Project(
            project_id=r["project_id"], offer=r["offer"], vendor=r["vendor"],
            project_type=r["project_type"], portfolio=r["portfolio"],
            entry_date=r["entry_date"], target_orderability_date=r["target_orderability_date"],
            project_status=r["project_status"],
            poc=dict(bu_ops=r["bu_ops"], bupm=r["bupm"], buc=r["buc"], ce=r["ce"],
                      s_plus=r["s_plus"], revrec=r["revrec"], export=r["export"],
                      tax=r["tax"], renewals=r["renewals"]),
            notes=r["notes"],
        ))
    return out


def load_events() -> list[dict]:
    return _read_csv("events.csv")


def load_child_tasks() -> list[dict]:
    return _read_csv("child_tasks_seed.csv")


def load_activities() -> list[dict]:
    return _read_csv("dim_activity.csv")


def is_applicable(stage: Stage, project_type: str) -> bool:
    return stage.applicable.get(project_type, False)


# --------------------------------------------------------------------------- #
# Event-log -> current state per (project, stage)
# --------------------------------------------------------------------------- #

def latest_event_per_stage(events: list[dict], project_id: str) -> dict:
    """Return {stage_id: latest_event_row} for one project, latest by timestamp
    then by event_id (append order) as tiebreak."""
    rows = [e for e in events if e["project_id"] == project_id]
    rows.sort(key=lambda e: (e["timestamp"], e["event_id"]))
    latest = {}
    for e in rows:
        latest[e["stage_id"]] = e
    return latest


def stage_state(stage: Stage, project_type: str, latest_event: dict | None, today: dt.date) -> dict:
    """Compute {status, health, days_elapsed, sla_days, actual_date, planned_end_date,
    owner, blocked, blocker_reason} for one project-stage, from its latest event only.
    This is intentionally the *only* place SLA/health arithmetic happens.
    """
    if not is_applicable(stage, project_type):
        return dict(status="Not Applicable", health="Not Applicable", days_elapsed=None,
                    sla_days=stage.sla_days, actual_date=None, planned_end_date=None,
                    owner="", blocked=False, blocker_reason="", comment="")

    if latest_event is None:
        return dict(status="Not Started", health="Not Started", days_elapsed=None,
                    sla_days=stage.sla_days, actual_date=None, planned_end_date=None,
                    owner="", blocked=False, blocker_reason="", comment="")

    e = latest_event
    event_type = e["event_type"]
    blocked = event_type == "Blocked" or _to_bool(e.get("blocker_flag", "false"))

    if event_type == "Completed":
        status, health = "Complete", "On Track"
    elif blocked:
        status, health = "Blocked", "Blocked"
    elif event_type in ("Started", "Backfill Snapshot", "No Change"):
        status = "In Progress" if float(e.get("pct_complete") or 0) > 0 else "Not Started"
        health = "On Track"  # refined below using SLA math
    elif event_type == "Not Applicable":
        status, health = "Not Applicable", "Not Applicable"
    else:
        status, health = "Not Started", "Not Started"

    days_elapsed = None
    if status == "In Progress" and e.get("actual_date"):
        try:
            start = dt.date.fromisoformat(e["actual_date"])
            days_elapsed = (today - start).days
            ratio = days_elapsed / stage.sla_days if stage.sla_days else 0
            if ratio >= 1.0:
                health = "Over SLA"
            elif ratio >= 0.8:
                health = "At Risk"
            else:
                health = "On Track"
        except ValueError:
            pass

    return dict(
        status=status, health=health, days_elapsed=days_elapsed, sla_days=stage.sla_days,
        actual_date=e.get("actual_date") or None, planned_end_date=e.get("planned_end_date") or None,
        owner=e.get("stage_owner") or "", blocked=blocked,
        blocker_reason=e.get("blocker_reason") or "", comment=e.get("comment") or "",
    )


HEALTH_RANK = {"Blocked": 3, "Over SLA": 2, "At Risk": 1, "On Track": 0, "Not Started": 0, "Not Applicable": -1}


def rollup_project(project: Project, stages: list[Stage], events: list[dict], today: dt.date) -> dict:
    """Compute the project-level row: per-stage state, overall health/status/progress,
    and last-updated timestamp. This is the derivation the intake assistant relies on
    to answer 'is this consistent, and what does it mean' without doing its own math.
    """
    latest = latest_event_per_stage(events, project.project_id)
    applicable_stages = [s for s in stages if is_applicable(s, project.project_type)]
    stage_states = {}
    for s in applicable_stages:
        stage_states[s.stage_id] = stage_state(s, project.project_type, latest.get(s.stage_id), today)

    complete_count = sum(1 for st in stage_states.values() if st["status"] == "Complete")
    total = len(applicable_stages) or 1
    progress = complete_count / total

    non_complete_healths = [st["health"] for st in stage_states.values() if st["status"] not in ("Complete", "Not Applicable")]
    if not non_complete_healths:
        overall_health = "On Track"
    else:
        worst = max(non_complete_healths, key=lambda h: HEALTH_RANK.get(h, 0))
        overall_health = worst

    if progress >= 1.0:
        overall_status = "Complete"
    elif any(st["status"] == "Blocked" for st in stage_states.values()):
        overall_status = "Blocked"
    elif complete_count > 0 or any(st["status"] == "In Progress" for st in stage_states.values()):
        overall_status = "In Progress"
    else:
        overall_status = "Not Started"

    last_updated = ""
    proj_events = [e for e in events if e["project_id"] == project.project_id]
    if proj_events:
        last_updated = max(e["actual_date"] for e in proj_events if e.get("actual_date"))

    return dict(
        project=project, applicable_stages=applicable_stages, stage_states=stage_states,
        progress=progress, health=overall_health, status=overall_status, last_updated=last_updated,
    )


def dependency_warnings(project: Project, stages: list[Stage], stage_states: dict) -> list[str]:
    """Flag project-stages that are In Progress/Complete while a declared
    predecessor stage is not yet Complete. Returned as human-readable strings
    for an assistant to surface back to the analyst -- never auto-corrected."""
    by_id = {s.stage_id: s for s in stages}
    warnings = []
    for s in stages:
        st = stage_states.get(s.stage_id)
        if not st or st["status"] not in ("In Progress", "Complete", "Blocked"):
            continue
        for pred_id in s.predecessor_ids:
            pred = stage_states.get(pred_id)
            if pred and pred["status"] not in ("Complete", "Not Applicable"):
                pred_name = by_id[pred_id].display_name if pred_id in by_id else pred_id
                warnings.append(
                    f"{s.display_name} is {st['status']} but its predecessor "
                    f"{pred_name} is only {pred['status']}."
                )
    return warnings


def blocked_register(projects_rollup: list[dict], today: dt.date) -> list[dict]:
    """Every currently-blocked project-stage, sorted by days blocked descending."""
    out = []
    for r in projects_rollup:
        for stage_id, st in r["stage_states"].items():
            if st["status"] != "Blocked":
                continue
            stage = next(s for s in r["applicable_stages"] if s.stage_id == stage_id)
            days_blocked = None
            if st["actual_date"]:
                try:
                    days_blocked = (today - dt.date.fromisoformat(st["actual_date"])).days
                except ValueError:
                    pass
            out.append(dict(
                offer=r["project"].offer, stage=stage.display_name,
                days_blocked=days_blocked if days_blocked is not None else 0,
                reason=st["blocker_reason"] or "Not categorised", owner=st["owner"],
                comment=st["comment"],
            ))
    out.sort(key=lambda x: -x["days_blocked"])
    return out


def update_compliance_pct(projects: list[Project], events: list[dict], today: dt.date, window_days: int = 7) -> int:
    """% of active projects with at least one event in the trailing window."""
    active = [p for p in projects if p.project_status == "Active"]
    if not active:
        return 0
    cutoff = today - dt.timedelta(days=window_days)
    fresh = 0
    for p in active:
        proj_events = [e for e in events if e["project_id"] == p.project_id and e.get("actual_date")]
        if any(dt.date.fromisoformat(e["actual_date"]) >= cutoff for e in proj_events
               if _is_date(e["actual_date"])):
            fresh += 1
    return round(fresh / len(active) * 100)


def _is_date(s: str) -> bool:
    try:
        dt.date.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


def next_event_id(events: list[dict]) -> str:
    n = len(events) + 1
    return f"EVT-{n:05d}"
