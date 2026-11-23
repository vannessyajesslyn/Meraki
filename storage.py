"""Tiny JSON helpers used by every Meraki module.

If your project already has a storage.py with the same two functions,
keep yours - the signatures below match how assignment_tracker.py and
project_manager.py call them.
"""
import json
import os


def load_json(path, default=None):
    """Return the data stored in `path`, or `default` if the file is
    missing or unreadable."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    """Write `data` to `path` (written to a temp file first so a crash
    can't leave a half-written save file)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
