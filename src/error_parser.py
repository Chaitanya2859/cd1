import re
import os
from models import CompilerError


def get_source_context(file_path, line_no, context_lines=2):
    if not file_path or not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        s = max(0, line_no - 1 - context_lines)
        e = min(len(lines), line_no + context_lines)

        return {
            "start_line": s + 1,
            "lines": lines[s:e],
        }
    except Exception:
        return None


_error_re = re.compile(
    r"^(?P<file>.+?):"
    r"(?P<line>\d+)"
    r"(?::(?P<col>\d+))?"
    r":\s*"
    r"(?P<type>error|warning|note):"
    r"\s*(?P<message>.*)$"
)


def parse_errors(raw_output):
    errs = []
    if not raw_output:
        return errs

    lines = raw_output.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        cur = lines[i].strip()

        if "Undefined symbols for architecture" in cur:
            block = [cur]
            i += 1
            while i < n:
                t = lines[i].strip()
                block.append(t)
                if "ld: symbol(s) not found for architecture" in t:
                    break
                i += 1

            txt = "\n".join(block)
            errs.append(
                CompilerError(
                    file=None,
                    line=None,
                    column=None,
                    error_type="linker",
                    message=txt,
                    raw=txt,
                )
            )
            i += 1
            continue

        m = _error_re.match(cur)
        if m:
            g = m.groupdict()
            err = CompilerError(
                file=g["file"],
                line=int(g["line"]),
                column=int(g["col"]) if g.get("col") else None,
                error_type=g["type"],
                message=g["message"].strip(),
                raw=cur,
            )

            if err.file and err.line and os.path.exists(err.file):
                err.context = get_source_context(err.file, err.line)

            errs.append(err)

        i += 1

    return errs
