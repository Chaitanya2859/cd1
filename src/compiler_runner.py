import subprocess

def run_cpp_compiler(file_path):
    try:
        res = subprocess.run(
            ["g++", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return res.stdout + res.stderr
    except FileNotFoundError:
        return "error: g++ compiler not found."
