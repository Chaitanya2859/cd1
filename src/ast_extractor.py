import subprocess

def extract_ast(file_path):
    try:
        result=subprocess.run(
            ["clang++","-Xclang","-ast-dump","-fsyntax-only",file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout

    except Exception:
        return None
    
def extract_node_near_line(ast_text, line_number):
    if not ast_text or not line_number:
        return None

    lines=ast_text.splitlines()
    for line in lines:
        if f":{line_number}:" in line:
            clean=line.strip()
            clean=clean.lstrip("`|- ")
            parts=clean.split()

            if len(parts)>0:
                return parts[0]
    return None