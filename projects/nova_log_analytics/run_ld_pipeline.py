"""
LD Pipeline: raw_labelit__ld.csv
  -> stg_labelit__ld__events.csv
  -> stg_labelit__ld__event_changes.csv
  -> int_labelit__ld__effective_changes.csv
"""

import csv
import json
import os

RAW_PATH       = "D:/Nova_log_data_validation/tables/raw_labelit__ld.csv"
OUT_DIR        = "D:/Nova_log_data_validation/tables/"
STG_EVENTS_OUT = os.path.join(OUT_DIR, "stg_labelit__ld__events.csv")
STG_CHANGES_OUT= os.path.join(OUT_DIR, "stg_labelit__ld__event_changes.csv")
INT_EFF_OUT    = os.path.join(OUT_DIR, "int_labelit__ld__effective_changes.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_tz(ts: str) -> str:
    """Convert '2026-03-24T13:42:34.921Z' -> '2026-03-24 13:42:34.921'."""
    if not ts:
        return ts
    return ts.replace("T", " ").rstrip("Z")


def feature_gen(feature: str) -> str:
    """Map feature code to generation label."""
    if feature == "od":
        return "Gen1"
    elif feature == "od2":
        return "Gen2"
    else:
        return "unknown"


def event_category(event_type: str) -> str:
    """Derive event_category from event_type."""
    if event_type == "annotation.object.select":
        return "select"
    elif event_type == "annotation.bbox3d.transform":
        return "transform"
    elif event_type in (
        "annotation.lane.create",
        "annotation.topology.create",
        "annotation.line.create",
    ):
        return "create"
    else:
        return "other"


def parse_new_val(new_val_str: str):
    """Try to parse new_val JSON string; return parsed object or raw string."""
    if new_val_str in ("null", "", None):
        return None
    try:
        return json.loads(new_val_str)
    except (json.JSONDecodeError, TypeError):
        return new_val_str


# ---------------------------------------------------------------------------
# 1. Read raw data
# ---------------------------------------------------------------------------

raw_rows = []
with open(RAW_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        raw_rows.append(row)

print(f"Raw rows read: {len(raw_rows)}")


# ---------------------------------------------------------------------------
# 2. Build stg_labelit__ld__events.csv
#    One row per unique event_id.
#    changes_raw: JSON array reconstructed from the change rows for that event.
# ---------------------------------------------------------------------------

# Group rows by event_id, preserving all change rows.
from collections import OrderedDict

events_map: dict = {}   # event_id -> dict with event fields + list of change rows
for row in raw_rows:
    eid = row["event_id"]
    if eid not in events_map:
        events_map[eid] = {
            "event_id":    eid,
            "event_type":  row["event_type"],
            "event_time":  strip_tz(row["event_time"]),
            "event_date":  row["event_date"],
            "occurred_at": strip_tz(row["occurred_at"]),
            "session_id":  row["session_id"],
            "user_id":     row["user_id"],
            "task_id":     row["task_id"],
            "feature":     row["feature"],
            "_changes":    [],   # accumulate change sub-rows
        }
    # Collect the change row for later changes_raw construction.
    events_map[eid]["_changes"].append({
        "change_idx":   int(row["change_idx"]),
        "object_id":    int(row["object_id"]) if row["object_id"] else None,
        "object_type":  row["object_type"],
        "change_action":row["change_action"],
        "old_val":      row["old_val"],
        "new_val":      row["new_val"],
    })

# Sort events by event_time for output.
sorted_events = sorted(events_map.values(), key=lambda e: e["event_time"])

STG_EVENTS_COLS = [
    "event_id", "event_type", "event_time", "event_date", "occurred_at",
    "session_id", "subject", "dataschema", "user_id", "user_name",
    "dataset_id", "task_id", "feature", "feature_gen", "action",
    "input_type", "targets", "params", "changes_raw", "event_category",
]

with open(STG_EVENTS_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=STG_EVENTS_COLS)
    writer.writeheader()
    for ev in sorted_events:
        # Build changes_raw JSON array, sorted by change_idx.
        changes_sorted = sorted(ev["_changes"], key=lambda c: c["change_idx"])
        changes_raw_list = []
        for ch in changes_sorted:
            element = {
                "object_id":   ch["object_id"],
                "object_type": ch["object_type"],
                "action":      ch["change_action"],
                "old":         None,
                "new":         parse_new_val(ch["new_val"]),
            }
            changes_raw_list.append(element)
        changes_raw_str = json.dumps(changes_raw_list, ensure_ascii=False)

        writer.writerow({
            "event_id":     ev["event_id"],
            "event_type":   ev["event_type"],
            "event_time":   ev["event_time"],
            "event_date":   ev["event_date"],
            "occurred_at":  ev["occurred_at"],
            "session_id":   ev["session_id"],
            "subject":      "",
            "dataschema":   "",
            "user_id":      ev["user_id"],
            "user_name":    "",
            "dataset_id":   "",
            "task_id":      ev["task_id"],
            "feature":      ev["feature"],
            "feature_gen":  feature_gen(ev["feature"]),
            "action":       "",
            "input_type":   "",
            "targets":      "",
            "params":       "",
            "changes_raw":  changes_raw_str,
            "event_category": event_category(ev["event_type"]),
        })

stg_events_count = len(sorted_events)
print(f"stg_labelit__ld__events.csv rows written: {stg_events_count}")


# ---------------------------------------------------------------------------
# 3. Build stg_labelit__ld__event_changes.csv
#    One row per raw change row (already exploded), sorted by (event_time, change_idx).
# ---------------------------------------------------------------------------

STG_CHANGES_COLS = [
    "event_id", "event_type", "event_time", "event_date", "occurred_at",
    "session_id", "user_id", "task_id", "feature", "feature_gen",
    "change_idx", "object_id", "object_type", "change_action",
    "old_val", "new_val", "move_distance",
]

# Build enriched change rows with event-level fields attached.
stg_change_rows = []
for row in raw_rows:
    stg_change_rows.append({
        "event_id":     row["event_id"],
        "event_type":   row["event_type"],
        "event_time":   strip_tz(row["event_time"]),
        "event_date":   row["event_date"],
        "occurred_at":  strip_tz(row["occurred_at"]),
        "session_id":   row["session_id"],
        "user_id":      row["user_id"],
        "task_id":      row["task_id"],
        "feature":      row["feature"],
        "feature_gen":  "unknown",          # feature='ld' -> unknown
        "change_idx":   int(row["change_idx"]),
        "object_id":    row["object_id"],
        "object_type":  row["object_type"],
        "change_action":row["change_action"],
        "old_val":      row["old_val"],     # keep "null" as-is
        "new_val":      row["new_val"],
        "move_distance":"",                 # create actions, no old position
    })

# Sort by (event_time, change_idx).
stg_change_rows.sort(key=lambda r: (r["event_time"], r["change_idx"]))

with open(STG_CHANGES_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=STG_CHANGES_COLS)
    writer.writeheader()
    for r in stg_change_rows:
        writer.writerow(r)

stg_changes_count = len(stg_change_rows)
print(f"stg_labelit__ld__event_changes.csv rows written: {stg_changes_count}")


# ---------------------------------------------------------------------------
# 4. Build int_labelit__ld__effective_changes.csv
#    Columns: event_id, event_time, session_id, event_type, change_idx,
#             object_id, object_type, change_action, old_val, new_val,
#             move_distance, is_reverted
#    is_reverted = 'FALSE' for all (no undo/redo in ld data)
# ---------------------------------------------------------------------------

INT_EFF_COLS = [
    "event_id", "event_time", "session_id", "event_type", "change_idx",
    "object_id", "object_type", "change_action", "old_val", "new_val",
    "move_distance", "is_reverted",
]

with open(INT_EFF_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=INT_EFF_COLS)
    writer.writeheader()
    for r in stg_change_rows:   # already sorted by (event_time, change_idx)
        writer.writerow({
            "event_id":     r["event_id"],
            "event_time":   r["event_time"],
            "session_id":   r["session_id"],
            "event_type":   r["event_type"],
            "change_idx":   r["change_idx"],
            "object_id":    r["object_id"],
            "object_type":  r["object_type"],
            "change_action":r["change_action"],
            "old_val":      r["old_val"],
            "new_val":      r["new_val"],
            "move_distance":r["move_distance"],
            "is_reverted":  "FALSE",
        })

int_eff_count = len(stg_change_rows)
print(f"int_labelit__ld__effective_changes.csv rows written: {int_eff_count}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("=" * 55)
print("Pipeline summary")
print("=" * 55)
print(f"  Raw input rows                 : {len(raw_rows)}")
print(f"  Unique events (stg_events)     : {stg_events_count}")
print(f"  Change rows  (stg_changes)     : {stg_changes_count}")
print(f"  Effective changes (int_eff)    : {int_eff_count}")
print()
print("Output files:")
print(f"  {STG_EVENTS_OUT}")
print(f"  {STG_CHANGES_OUT}")
print(f"  {INT_EFF_OUT}")
print("=" * 55)
