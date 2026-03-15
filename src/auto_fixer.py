import re

def generate_fix(error, source_lines):
    """
    Generates an automatic code fix for common C++ compiler errors.
    
    Args:
        error: CompilerError object
        source_lines: list of strings (source code lines)
        
    Returns:
        A dictionary with "description", "original", and "fixed" or None if no fix is possible.
    """
    if not source_lines or not error.line or error.line > len(source_lines) or error.line < 1:
        return None
        
    msg = error.message.lower()
    line_idx = error.line - 1
    current_line = source_lines[line_idx]
    
    # missing_semicolon
    if "expected ';'" in msg:
        target_line = current_line
        
        # If the error points to the line after the missing semicolon (like GCC often does)
        if "before" in msg or target_line.strip() in ["}", "{"] or target_line.strip().startswith("return"):
            if line_idx > 0 and not source_lines[line_idx - 1].strip().endswith(";"):
                target_line = source_lines[line_idx - 1]
                
        # If it still ends with semicolon, fallback to previous line
        if target_line.strip().endswith(";") and line_idx > 0:
            target_line = source_lines[line_idx - 1]
            
        return {
            "description": "Added missing semicolon",
            "original": target_line,
            "fixed": target_line.rstrip() + ";"
        }
            
    # undeclared_variable
    if "was not declared in this scope" in msg or "undeclared identifier" in msg:
        match = re.search(r"'([^']+)'", error.message)
        var_name = match.group(1) if match else "undeclared_var"
        return {
            "description": f"Provide a variable declaration for '{var_name}'",
            "original": current_line,
            "fixed": f"auto {var_name} = 0; // Declare before use"
        }
        
    # type_mismatch
    if "cannot convert" in msg or "cannot initialize" in msg or "type mismatch" in msg:
        target_type = "TargetType"
        match_clang = re.search(r"of type '([^']+)'", error.message)
        match_gcc = re.search(r"to '([^']+)'", error.message)
        if match_clang:
            target_type = match_clang.group(1)
        elif match_gcc:
            target_type = match_gcc.group(1)
            
        return {
            "description": f"Use explicit casting to '{target_type}'",
            "original": current_line,
            "fixed": f"static_cast<{target_type}>({current_line.strip()});"
        }
        
    # function_mismatch
    if "too few arguments" in msg or "too many arguments" in msg or "no matching function for call" in msg or "incorrect number of arguments" in msg:
        return {
            "description": "Check the function signature for correct arguments",
            "original": current_line,
            "fixed": f"/* Check function signature */ {current_line.strip()}"
        }
        
    # unused_expression
    if "statement has no effect" in msg or "unused variable" in msg or "value computed is not used" in msg or "unused" in msg:
        match = re.search(r"'([^']+)'", error.message)
        if "unused variable" in msg and match:
            var_name = match.group(1)
            return {
                "description": f"Remove or use the unused variable '{var_name}'",
                "original": current_line,
                "fixed": f"// unused: {current_line.strip()}"
            }
        else:
            return {
                "description": "Assign the expression to a variable",
                "original": current_line,
                "fixed": f"auto unused_result = {current_line.lstrip()}"
            }

    return None
