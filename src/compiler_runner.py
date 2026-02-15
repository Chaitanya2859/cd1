import subprocess

def run_cpp_compiler(filename):

    try:
        result = subprocess.run(
            ["g++", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stderr
    except FileNotFoundError:
        return "error: g++ compiler not found."