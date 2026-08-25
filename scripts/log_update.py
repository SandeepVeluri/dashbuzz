#!/usr/bin/env python3
"""
log_update.py -- the only way anything is ever written to data/events.csv.

This is the tool an AI chat assistant (Codex/ChatGPT, Claude, or anyone else
with shell + git access to this repo) calls after it has turned an analyst's
raw update -- an email, meeting notes, a one-line verbal status -- into
structured fields. The assistant's job is natural-language understanding
only: which offer, what happened, when, and why. Every number that ends up
on the dashboard (health colour, % complete, blocked-days, dependency
consistency) is computed here and in derive.py, never guessed by the model.

Typical assistant flow:
  1. python scripts/log_update.py --list-projects
     python scripts/log_update.py --list-stages --project <offer>
     (resolve the analyst's free text against these canonical lists yourself --
      this script will refuse an unresolved name rather than guess)
  2. python scripts/log_update.py --project "Quali" --stage "PID Setups" \
       --event-type Completed --date 2026-08-24 --owner Albert \
       --comment "Export review done" --submitted-by "<analyst name>" --dry-run
     -> review the printed consequence summary with the analyst
  3. re-run without --dry-run, then --commit --push

See docs/INTAKE_PROTOCOL.md for the full contract this script implements.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = REPO_ROOT / "data" / "events.csv"
EVENT_FIELDS = ["event_id", "timestamp", "project_id", "stage_id", "event_type", "status_after",
                 "pct_complete", "planned_end_date", "actual_date", "stage_owner", "blocker_flag",
                 "blocker_reason", "blocker_owner", "expected_unblock_date", "comment",
                 "submitted_by", "source"]


class ValidationError(Exception):
    pass


def _closest(name: str, candidates: dict[str, str], label: str, cutoff: float = 0.6,
             aliases: dict[str, list[str]] | None = None) -> str:
    """candidates: {canonical_id: display_text} used for the error message and as the
    default fuzzy-match target. aliases: optional {canonical_id: [alt names]} -- every
    alias is checked for an exact (case-insensitive) match before falling back to fuzzy
    matching on the display text, so a stage's short name matches even when the display
    text shown to the analyst is a longer "Full Name (Short Name)" combination.
    Returns canonical_id or raises.
    """
    name_l = name.strip().lower()
    for cid, text in candidates.items():
        alts = [text, cid, *aliases.get(cid, [])] if aliases else [text, cid]
        if name_l in {a.strip().lower() for a in alts}:
            return cid
    matches = difflib.get_close_matches(name_l, [t.lower() for t in candidates.values()], n=3, cutoff=cutoff)
    if len(matches) == 1:
        for cid, text in candidates.items():
            if text.lower() == matches[0]:
                return cid
    options = "\n".join(f"  - {text}" for text in candidates.values())
    raise ValidationError(
        f"Could not confidently resolve {label} '{name}'. Candidates:\n{options}\n"
        f"Re-run with the exact name from this list."
    )


def resolve_project(projects: list[derive.Project], name: str) -> derive.Project:
    active = [p for p in projects if p.project_status == "Active"]
    by_offer = {p.project_id: p.offer for p in active}
    pid = _closest(name, by_offer, "project/offer")
    return next(p for p in active if p.project_id == pid)


def resolve_stage(stages: list[derive.Stage], project_type: str, name: str) -> derive.Stage:
    applicable = [s for s in stages if derive.is_applicable(s, project_type)]
    by_id = {s.stage_id: f"{s.stage_name} ({s.display_name})" if s.stage_name != s.display_name else s.stage_name
             for s in applicable}
    aliases = {s.stage_id: [s.stage_name, s.display_name] for s in applicable}
    sid = _closest(name, by_id, "stage", aliases=aliases)
    return next(s for s in applicable if s.stage_id == sid)


def validate_event(args, stage: derive.Stage) -> dict:
    if args.event_type not in derive.EVENT_TYPES:
        raise ValidationError(f"--event-type must be one of {derive.EVENT_TYPES}")
    try:
        dt.date.fromisoformat(args.date)
    except ValueError:
        raise ValidationError("--date must be YYYY-MM-DD (the actual date it happened, not today's date)")
    if args.event_type == "Blocked":
        if not args.blocker_reason or args.blocker_reason not in derive.BLOCKER_REASONS:
            raise ValidationError(f"--blocker-reason is required for Blocked events, one of {derive.BLOCKER_REASONS}")
    if args.pct_complete is not None and not (0 <= args.pct_complete <= 100):
        raise ValidationError("--pct-complete must be 0-100")
    if args.planned_end:
        try:
            dt.date.fromisoformat(args.planned_end)
        except ValueError:
            raise ValidationError("--planned-end must be YYYY-MM-DD")
    return {}


def build_row(events: list[dict], project: derive.Project, stage: derive.Stage, args) -> dict:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status_after = {
        "Started": "In Progress", "Completed": "Complete", "Blocked": "Blocked",
        "Unblocked": "In Progress", "Not Applicable": "Not Applicable", "No Change": "In Progress",
    }.get(args.event_type, "In Progress")
    pct = args.pct_complete
    if pct is None:
        pct = 100 if args.event_type == "Completed" else (0 if args.event_type == "Started" else "")
    return dict(
        event_id=derive.next_event_id(events),
        timestamp=now,
        project_id=project.project_id,
        stage_id=stage.stage_id,
        event_type=args.event_type,
        status_after=status_after,
        pct_complete=pct,
        planned_end_date=args.planned_end or "",
        actual_date=args.date,
        stage_owner=args.owner or "",
        blocker_flag="true" if args.event_type == "Blocked" else "false",
        blocker_reason=args.blocker_reason or "",
        blocker_owner=args.blocker_owner or "",
        expected_unblock_date=args.expected_unblock or "",
        comment=(args.comment or "")[:200],
        submitted_by=args.submitted_by,
        source=f"Logged via log_update.py by {args.submitted_by} on {now}.",
    )


def append_events(rows: list[dict]) -> None:
    with open(EVENTS_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        for r in rows:
            w.writerow(r)


def print_consequences(project: derive.Project, stages: list[derive.Stage], events: list[dict]) -> None:
    today = dt.date.today()
    rollup = derive.rollup_project(project, stages, events, today)
    warnings = derive.dependency_warnings(project, rollup["applicable_stages"], rollup["stage_states"])
    print(f"\n--- {project.offer} ({project.project_type}) after this update ---")
    print(f"Overall status: {rollup['status']}  |  Health: {rollup['health']}  |  "
          f"Progress: {round(rollup['progress'] * 100)}%")
    for s in rollup["applicable_stages"]:
        st = rollup["stage_states"][s.stage_id]
        print(f"  [{st['status']:<14}] {s.display_name:<45} health={st['health']}")
    if warnings:
        print("\nDependency check -- please confirm these with the analyst before trusting the dashboard:")
        for w in warnings:
            print(f"  ! {w}")
    print()


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO_ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-projects", action="store_true")
    ap.add_argument("--list-stages", action="store_true", help="requires --project")
    ap.add_argument("--project", help="offer/project name (fuzzy-matched against dim_project.csv)")
    ap.add_argument("--stage", help="stage name (fuzzy-matched against dim_stage.csv)")
    ap.add_argument("--event-type", choices=derive.EVENT_TYPES)
    ap.add_argument("--date", help="actual date it happened, YYYY-MM-DD")
    ap.add_argument("--owner", help="who owns this stage right now")
    ap.add_argument("--pct-complete", type=float, default=None)
    ap.add_argument("--planned-end", help="planned/target date for this stage, YYYY-MM-DD")
    ap.add_argument("--blocker-reason", choices=derive.BLOCKER_REASONS)
    ap.add_argument("--blocker-owner")
    ap.add_argument("--expected-unblock", help="YYYY-MM-DD")
    ap.add_argument("--comment", default="")
    ap.add_argument("--submitted-by", help="name of the analyst relaying this update")
    ap.add_argument("--batch-json", help="path to a JSON file: a list of objects with the same "
                                          "keys as the CLI flags above, for logging several events "
                                          "from one conversation in a single commit")
    ap.add_argument("--dry-run", action="store_true", help="validate and print consequences, do not write")
    ap.add_argument("--commit", action="store_true", help="git commit the change")
    ap.add_argument("--push", action="store_true", help="git push after commit (implies --commit)")
    args = ap.parse_args()

    projects = derive.load_projects()
    stages = derive.load_stages()

    if args.list_projects:
        for p in projects:
            if p.project_status == "Active":
                print(f"{p.offer}  [{p.project_type}, {p.portfolio}]  id={p.project_id}")
        return 0

    if args.list_stages:
        if not args.project:
            print("error: --list-stages requires --project", file=sys.stderr)
            return 2
        project = resolve_project(projects, args.project)
        for s in stages:
            if derive.is_applicable(s, project.project_type):
                print(f"{s.display_name}  (sla={s.sla_days}d)  id={s.stage_id}")
        return 0

    batch = []
    if args.batch_json:
        batch = json.loads(Path(args.batch_json).read_text())
    else:
        required = ["project", "stage", "event_type", "date", "submitted_by"]
        missing = [r for r in required if not getattr(args, r)]
        if missing:
            print(f"error: missing required flags: {', '.join('--' + m.replace('_', '-') for m in missing)}",
                  file=sys.stderr)
            return 2
        batch = [vars(args)]

    events = derive.load_events()
    new_rows = []
    touched_projects: dict[str, derive.Project] = {}

    for item in batch:
        ns = argparse.Namespace(**{**vars(args), **item})
        try:
            project = resolve_project(projects, ns.project)
            stage = resolve_stage(stages, project.project_type, ns.stage)
            validate_event(ns, stage)
        except ValidationError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        row = build_row(events + new_rows, project, stage, ns)
        new_rows.append(row)
        touched_projects[project.project_id] = project

    print(f"{len(new_rows)} event(s) to log:")
    for r in new_rows:
        stage = next(s for s in stages if s.stage_id == r["stage_id"])
        print(f"  {r['project_id']} / {stage.display_name} / {r['event_type']} / {r['actual_date']}"
              + (f"  (blocked: {r['blocker_reason']})" if r["blocker_flag"] == "true" else ""))

    combined = events + new_rows
    for project in touched_projects.values():
        print_consequences(project, stages, combined)

    if args.dry_run:
        print("(dry run -- nothing written)")
        return 0

    append_events(new_rows)
    print(f"Appended {len(new_rows)} row(s) to {EVENTS_PATH.relative_to(REPO_ROOT)}")

    if args.push:
        args.commit = True
    if args.commit:
        git("add", "data/events.csv")
        summary = "; ".join(f"{r['project_id']}/{r['stage_id']}={r['event_type']}" for r in new_rows)
        git("commit", "-m", f"Log update: {summary}\n\nSubmitted by {new_rows[0]['submitted_by']}.")
        print("Committed.")
    if args.push:
        git("push")
        print("Pushed -- the dashboard will rebuild via GitHub Actions in a minute or two.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
