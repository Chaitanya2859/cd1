import subprocess
import re
import os

def extract_ast(file_path):
    try:
        result = subprocess.run(
            ["clang++", "-Xclang", "-ast-dump", "-fsyntax-only", file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # Strip colors and use systematic line filtering
        clean_out = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', result.stdout)
        filtered = [line for line in clean_out.splitlines() 
                    if any(x in line for x in [file_path, "<line:", "<col:"])]
        return "\n".join(filtered)
    except Exception: return None

def parse_ast_to_tree(ast_text, file_path=None):
    if not ast_text: return []
    
    MAX_DEPTH = 6
    KEY_NODES = [
        "FunctionDecl","CXXMethodDecl","VarDecl","ParmVarDecl",
        "IfStmt","ForStmt","WhileStmt",
        "BinaryOperator","UnaryOperator",
        "CallExpr","ReturnStmt","DeclRefExpr",
        "CXXRecordDecl" # Keeping this to ensure classes are visible
    ]
    
    lines = ast_text.splitlines()
    root_nodes, stack = [], []
    
    for line in lines:
        if not line.strip(): continue
        
        # Precise depth detection based on tree markers
        depth = line.count('|') + line.count('`')
        if depth > MAX_DEPTH: continue
            
        match = re.search(r'[a-zA-Z]', line)
        if not match: continue
            
        parts = line[match.start():].strip().split(' ', 1)
        node_type = parts[0]
        details = parts[1] if len(parts) > 1 else ""
        
        # Architectural Filter
        if not any(k == node_type for k in KEY_NODES):
            continue

        node = {"type": node_type, "details": details, "children": []}
        while stack and stack[-1][0] >= depth: stack.pop()
            
        if stack:
            stack[-1][1]["children"].append(node)
        else:
            root_nodes.append(node)
                
        stack.append((depth, node))

    return root_nodes

def extract_node_near_line(ast_text, line_number):
    if not ast_text: return None
    match = re.search(rf":{line_number}:\d+.*?\s+([a-zA-Z]+)", ast_text)
    return match.group(1) if match else None