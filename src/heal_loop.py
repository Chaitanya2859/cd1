"""
heal_loop.py
------------
Orchestrates the auto-healing pipeline.

Flow:
  1. Compile  → parse errors
  2. Classify each error
  3. Call auto_healer.attempt_fix() for the first fixable error
  4. Write patched source  →  show diff
  5. Recompile  →  if clean, done ✅
  6. After MAX_ATTEMPTS failures  →  emit give_up signal

Signals emitted (for the GUI):
  - attempt_started(attempt_no: int, error: dict)
  - diff_ready(attempt_no: int, diff_html: str)
  - compile_clean()
  - give_up(history: list[dict])
  - error_signal(message: str)
"""

import json
import os
import sys
import subprocess
import re
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from auto_healer import attempt_fix, UNFIXABLE_CATEGORIES
from diff_viewer import compute_diff, format_diff_html, has_changes
from healing_suggester import suggest_failed_heal

MAX_ATTEMPTS = 10

# ── GCC error pattern ────────────────────────────────────────────────────────
_ERR_PATTERN = re.compile(
    r"^(.+?):(\d+):(\d+):\s*(error|warning):\s*(.*)$"
)


def _compile(file_path: str) -> tuple[list[dict], str]:
    """
    Run g++ and return (error_list, raw_stderr).
    Each error dict has: file, line, column, type, message, raw.
    """
    res = subprocess.run(
        ["g++", "-std=c++17", "-Wall", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    errors = []
    for line in res.stderr.splitlines():
        m = _ERR_PATTERN.match(line.strip())
        if m:
            errors.append({
                "file":    m.group(1),
                "line":    int(m.group(2)),
                "column":  int(m.group(3)),
                "type":    m.group(4),
                "message": m.group(5),
                "raw":     line,
            })
    return errors, res.stderr


def _pre_scan(source: str) -> list[dict]:
    """
    Catch a small set of obvious issues before compile diagnostics.
    Returns synthetic diagnostics in the same shape as compiler errors.
    """
    errors = []
    lines = source.splitlines()

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        if re.search(r"\bint\b.*=\s*2147483647\b", stripped):
            errors.append({
                "file": "source",
                "line": i,
                "column": 0,
                "type": "warning",
                "message": "integer overflow: value at INT_MAX, addition will overflow",
                "raw": line,
                "category": "integer_overflow",
                "confidence": 1.0,
            })

        if re.search(r"if\s*\([^=!<>]*(?<![=!<>])=(?!=)[^)]*\)", stripped):
            if not re.search(r"if\s*\(.*==.*\)", stripped):
                errors.append({
                    "file": "source",
                    "line": i,
                    "column": 0,
                    "type": "warning",
                    "message": "assignment used as truth value in if condition",
                    "raw": line,
                    "category": "syntax_error",
                    "confidence": 1.0,
                })

        if re.search(r"/\s*0\b", stripped):
            errors.append({
                "file": "source",
                "line": i,
                "column": 0,
                "type": "warning",
                "message": "division by zero: literal 0 used as divisor",
                "raw": line,
                "category": "division_by_zero",
                "confidence": 1.0,
            })

        zero_assign = re.search(r"\bint\s+([A-Za-z_]\w*)\s*=\s*0\s*;", stripped)
        if zero_assign:
            var = zero_assign.group(1)
            guard_pattern = re.compile(rf"if\s*\(\s*{re.escape(var)}\s*==\s*0\s*\)")
            if guard_pattern.search(source):
                continue
            for j, future_line in enumerate(lines[i:], start=i + 1):
                future_stripped = future_line.strip()
                if future_stripped.startswith("//"):
                    continue
                if re.search(rf"/\s*{re.escape(var)}\b", future_line):
                    errors.append({
                        "file": "source",
                        "line": j,
                        "column": 0,
                        "type": "warning",
                        "message": f"division by zero: '{var}' is 0",
                        "raw": future_line,
                        "category": "division_by_zero",
                        "confidence": 0.9,
                    })
                    break

    return errors


def _classify_errors(errors: list[dict], classifier) -> list[dict]:
    """Attach 'category' to each error using the ML classifier."""
    for e in errors:
        if e.get("category"):
            e["confidence"] = round(float(e.get("confidence", 1.0)), 3)
            continue
        cat, conf = classifier.predict(e["message"])
        e["category"] = cat or "other"
        e["confidence"] = round(conf, 3)
    return errors


def _pick_fix_target(issues: list[dict]) -> Optional[dict]:
    """
    Prefer real errors, but allow fixable warnings such as uninitialized
    variables when there are no patchable hard errors.
    """
    for issue_type in ("error", "warning"):
        for issue in issues:
            if issue["type"] != issue_type:
                continue
            if issue.get("category") in UNFIXABLE_CATEGORIES:
                continue
            return issue
    return None


class HealWorker(QThread):
    """
    QThread that runs the full heal loop asynchronously.
    Connect to its signals to receive live updates.
    """
    attempt_started = pyqtSignal(int, dict)          # (attempt_no, error)
    diff_ready      = pyqtSignal(int, str)            # (attempt_no, diff_html)
    compile_clean   = pyqtSignal()
    give_up         = pyqtSignal(list)                # history list
    error_signal    = pyqtSignal(str)                 # fatal/internal errors
    hint_required   = pyqtSignal(int, dict, list)     # (attempt_no, error, history)

    def __init__(self, file_path: str, classifier, hint: Optional[str] = None):
        super().__init__()
        self.file_path  = file_path
        self.classifier = classifier
        self.hint       = hint          # optional user guidance from previous round

    def run(self):
        try:
            self._heal()
        except Exception as exc:
            self.error_signal.emit(str(exc))

    def _attach_failure_suggestion(self, history: list[dict], error: dict, source: str) -> None:
        if not error:
            return
        error["suggestion"] = suggest_failed_heal(error, source, history)

    def _heal(self):
        history = []
        seen_errors = set()

        # Read current source
        with open(self.file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # If user supplied a hint, prepend it as a comment so the healer
        # can inspect it (future expansion).  For now we just record it.
        if self.hint:
            history.append({"type": "hint", "text": self.hint})

        for attempt in range(1, MAX_ATTEMPTS + 1):

            # 1. Compile
            errors, raw_stderr = _compile(self.file_path)
            pre_errors = _pre_scan(source)
            all_errors = pre_errors + errors

            # Clean!
            if not all_errors:
                self.compile_clean.emit()
                return

            # 2. Classify
            _classify_errors(all_errors, self.classifier)

            # 3. Pick first fixable issue, preferring hard errors.
            target = _pick_fix_target(all_errors)

            # Nothing actionable remains.
            if target is None:
                hard_errors = [e for e in all_errors if e["type"] == "error"]
                if not hard_errors:
                    self.compile_clean.emit()
                    return
                history.append({
                    "attempt": attempt,
                    "error": hard_errors[0],
                    "patch": None,
                    "reason": "unfixable_category",
                })
                self._attach_failure_suggestion(history, hard_errors[0], source)
                self.give_up.emit(history)
                return

            self.attempt_started.emit(attempt, target)

            error_key = target.get("message")
            if error_key in seen_errors:
                self._attach_failure_suggestion(history, target, source)
                self.give_up.emit(history)
                return
            seen_errors.add(error_key)

            # 4. Attempt fix
            patched = attempt_fix(source, target)

            if patched is None or patched == source:
                history.append({
                    "attempt": attempt,
                    "error": target,
                    "patch": None,
                    "reason": "no_patch_available",
                })
                # No diff — try next attempt only if more attempts remain
                if attempt == MAX_ATTEMPTS:
                    self._attach_failure_suggestion(history, target, source)
                    self.give_up.emit(history)
                    return
                continue

            # 5. Compute + emit diff
            diff = compute_diff(source, patched)
            diff_html = format_diff_html(diff) if has_changes(diff) else "<i>No visible changes.</i>"
            self.diff_ready.emit(attempt, diff_html)

            # Record history
            history.append({
                "attempt": attempt,
                "error": target,
                "patch": patched,
                "diff_html": diff_html,
            })

            # 6. Write patched file and loop
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(patched)
            source = patched

        # Exhausted all attempts
        last_error = next((item.get("error") for item in reversed(history) if item.get("error")), None)
        self._attach_failure_suggestion(history, last_error, source)
        self.give_up.emit(history)
