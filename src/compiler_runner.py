import subprocess
import re

def run_cpp_compiler(file_path):
    try:
        res=subprocess.run(
            ["g++","-std=c++17",file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        errors=[]
        pattern=r"(.+):(\d+):(\d+):\s+(error|warning):\s+(.*)"

        for line in res.stderr.splitlines():
            match=re.match(pattern, line)
            if match:
                errors.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "type": match.group(4),
                    "message": match.group(5),
                    "raw": line
                })
        return errors

    except FileNotFoundError:
        return[{
            "file":None,
            "line":None,
            "column":None,
            "type":"error",
            "message":"g++ compiler not found.",
            "raw":"g++ compiler not found."
        }]