import re
from typing import Dict, Any, Optional, List

class PatternRule:
    def __init__(self, name: str, regexes: List[str], category: str, handler):
        self.name = name
        self.regexes = regexes
        self.category = category
        self.handler = handler
        
    def match(self, message: str):
        for pattern in self.regexes:
            m = re.search(pattern, message, re.IGNORECASE)
            if m:
                return m
        return None

def _get_current_line(error, source_lines: List[str]) -> str:
    if not source_lines or not error.line or error.line < 1 or error.line > len(source_lines):
        return ""
    return source_lines[error.line - 1]

def _handle_missing_semicolon(error, source_lines, ast_node, match):
    current_line = _get_current_line(error, source_lines)
    line_idx = (error.line - 1) if error.line else -1
    
    target_line = current_line
    if "before" in error.message.lower() or target_line.strip() in ["}", "{"] or target_line.strip().startswith("return"):
        if line_idx > 0 and not source_lines[line_idx - 1].strip().endswith(";"):
            target_line = source_lines[line_idx - 1]
            
    if target_line.strip().endswith(";") and line_idx > 0:
        target_line = source_lines[line_idx - 1]
        
    fix = target_line.rstrip() + ";" if target_line else ""
    return {
        "explanation": "A statement is missing a semicolon at the end.",
        "suggestion": "Add a semicolon to terminate the statement.",
        "possible_fix": {
             "description": "Added missing semicolon",
             "original": target_line,
             "fixed": fix
        } if fix else None
    }

def _handle_undeclared_variable(error, source_lines, ast_node, match):
    var_name = match.group(1) if len(match.groups()) > 0 else "unknown_var"
    current_line = _get_current_line(error, source_lines)
    return {
        "explanation": f"The compiler doesn't know about '{var_name}'. It needs to be declared before it is used.",
        "suggestion": f"Provide a variable declaration for '{var_name}' or include the required header.",
        "possible_fix": {
            "description": f"Declare '{var_name}'",
            "original": current_line,
            "fixed": f"auto {var_name} = 0; // Adjust type accordingly\n{current_line}"
        }
    }

def _handle_type_mismatch(error, source_lines, ast_node, match):
    current_line = _get_current_line(error, source_lines)
    target_type = match.group(1) if len(match.groups()) > 0 else "TargetType"
    
    explanation = f"Type mismatch: cannot convert to '{target_type}' natively."
    if ast_node == "BinaryOperator":
         explanation = f"Operator type mismatch: invalid operands for binary operator involving types like '{target_type}'."
         
    return {
        "explanation": explanation,
        "suggestion": f"Check the types or provide an explicit cast to '{target_type}'.",
        "possible_fix": {
             "description": f"Cast to {target_type}",
             "original": current_line,
             "fixed": f"static_cast<{target_type}>({current_line.strip()});"
        }
    }

def _handle_function_arguments(error, source_lines, ast_node, match):
    explanation = "Function call mismatch: The number or types of arguments provided do not match the function signature."
    if ast_node == "CallExpr":
        explanation = "Function call mismatch: The arguments in this function call do not match any known overload signatures."
    current_line = _get_current_line(error, source_lines)
    return {
        "explanation": explanation,
        "suggestion": "Check the function signature and correctly supply the requested parameters.",
        "possible_fix": {
            "description": "Verify function signature",
            "original": current_line,
            "fixed": f"/* Check exact arguments */ {current_line.strip()}"
        }
    }

def _handle_unused_expression(error, source_lines, ast_node, match):
    var_name = match.group(1) if len(match.groups()) > 0 else ""
    current_line = _get_current_line(error, source_lines)
    if var_name:
        return {
            "explanation": f"The variable '{var_name}' was declared but never used.",
            "suggestion": "Remove the unused variable or use it safely.",
            "possible_fix": {
                "description": f"Comment out unused variable '{var_name}'",
                "original": current_line,
                "fixed": f"// unused: {current_line.strip()}"
            }
        }
    return {
        "explanation": "A statement or value operation has no effect and its result is unused.",
        "suggestion": "Assign the computed expression to a variable or remove it.",
        "possible_fix": {
            "description": "Capture unused result",
            "original": current_line,
            "fixed": f"auto unused_result = {current_line.lstrip()}"
        }
    }

def _handle_redefinition(error, source_lines, ast_node, match):
    var_name = match.group(1) if len(match.groups()) > 0 else "variable"
    current_line = _get_current_line(error, source_lines)
    return {
        "explanation": f"The variable '{var_name}' is declared multiple times in the same scope.",
        "suggestion": "Remove the extra declaration or rename the variable.",
        "possible_fix": {
            "description": "Remove redefinition",
            "original": current_line,
            "fixed": f"// Remove this redefinition: {current_line.strip()}"
        }
    }

def _handle_conflicting_declaration(error, source_lines, ast_node, match):
    var_name = match.group(1) if len(match.groups()) > 0 else "variable"
    return {
         "explanation": f"A conflicting declaration was found for '{var_name}'. It was previously defined with a different type.",
         "suggestion": "Ensure the variable or function signature matches its previous declaration.",
         "possible_fix": None
    }

def _handle_invalid_pointer(error, source_lines, ast_node, match):
    return {
         "explanation": "Invalid pointer dereference or misuse. You are treating a non-pointer as a pointer or dereferencing an invalid memory address.",
         "suggestion": "Make sure you are operating on a valid pointer type.",
         "possible_fix": None
    }

def _handle_break_outside(error, source_lines, ast_node, match):
    current_line = _get_current_line(error, source_lines)
    return {
         "explanation": "A 'break' statement is used outside of a loop or switch case.",
         "suggestion": "Remove the 'break' statement or ensure it is inside a loop/switch block.",
         "possible_fix": {
            "description": "Remove invalid break",
            "original": current_line,
            "fixed": f"// break removed: {current_line.strip()}"
         }
    }

def _handle_continue_outside(error, source_lines, ast_node, match):
    current_line = _get_current_line(error, source_lines)
    return {
         "explanation": "A 'continue' statement is used outside of a loop.",
         "suggestion": "Remove the 'continue' statement or place it strictly inside a loop block.",
         "possible_fix": {
            "description": "Remove invalid continue",
            "original": current_line,
            "fixed": f"// continue removed: {current_line.strip()}"
         }
    }

def _handle_return_mismatch(error, source_lines, ast_node, match):
    return {
         "explanation": "The type of the returned value does not match the function's expected return type, or you are returning a value from a void function.",
         "suggestion": "Change the return expression so it matches the function signature, or fix the function's return type.",
         "possible_fix": None
    }

def _handle_template_mismatch(error, source_lines, ast_node, match):
    return {
         "explanation": "Template argument mismatch. The provided arguments fail to instantiate the template properly.",
         "suggestion": "Check the number of template arguments and their valid types.",
         "possible_fix": None
    }

def _handle_invalid_operator(error, source_lines, ast_node, match):
    return {
         "explanation": "Invalid operator usage. An operator was placed incorrectly.",
         "suggestion": "Ensure operators are placed between valid operands.",
         "possible_fix": None
    }

def _handle_missing_bracket(error, source_lines, ast_node, match):
    return {
         "explanation": "A closing bracket, brace or parenthesis may be missing.",
         "suggestion": "Check your code structure to ensure all opened scopes '{}', '()', '[]' are properly closed.",
         "possible_fix": None
    }

def _handle_unknown_type(error, source_lines, ast_node, match):
    type_name = match.group(1) if len(match.groups()) > 0 else "unknown"
    return {
         "explanation": f"The compiler does not recognize the type '{type_name}'.",
         "suggestion": "Include the missing header file containing this type declaration.",
         "possible_fix": {
            "description": f"Include <{type_name}> implicitly",
            "original": _get_current_line(error, source_lines),
            "fixed": f"#include <{type_name}> // (Add near top)\n" + _get_current_line(error, source_lines).lstrip()
         }
    }

def _handle_incompatible_operands(error, source_lines, ast_node, match):
    return {
         "explanation": "Incompatible operands to binary operator. You are manipulated types that do not mix natively.",
         "suggestion": "Cast one side of the operator or implement the corresponding operator overload.",
         "possible_fix": None
    }

def _handle_private_member(error, source_lines, ast_node, match):
    return {
         "explanation": "You are attempting to access a 'private' or 'protected' member from outside its given class/struct.",
         "suggestion": "Use an exposed public getter method instead.",
         "possible_fix": None
    }

def _handle_const_correctness(error, source_lines, ast_node, match):
    return {
         "explanation": "Assignment of read-only location. You are attempting to modify a variable marked as 'const'.",
         "suggestion": "Check if the variable should truly be const. If so, do not assign to it.",
         "possible_fix": None
    }

def _handle_invalid_conversion(error, source_lines, ast_node, match):
    return {
         "explanation": "Invalid type conversion requested. The standard casts don't support moving between these types natively.",
         "suggestion": "Make sure the cast is conceptually valid. You may need a specific constructor.",
         "possible_fix": None
    }

def _handle_linker_error(error, source_lines, ast_node, match):
    return {
         "explanation": "Linker error: undefined reference. The code compiles but the final assembly fails because a symbol has no implementation.",
         "suggestion": "Make sure you have provided a body for your functions and are linking the required object files.",
         "possible_fix": None
    }

RULES = [
    PatternRule("missing_semicolon", [r"expected ';'", r"expected\s*';'"], "Syntax", _handle_missing_semicolon),
    PatternRule("missing_bracket", [r"expected '\}'", r"expected '\)'", r"expected '\]'"], "Syntax", _handle_missing_bracket),
    PatternRule("undeclared_variable", [r"was not declared in this scope", r"use of undeclared identifier '([^']+)'", r"'([^']+)' was not declared"], "Name Resolution", _handle_undeclared_variable),
    PatternRule("unknown_type", [r"unknown type name '([^']+)'", r"does not name a type"], "Type", _handle_unknown_type),
    PatternRule("type_mismatch", [r"cannot convert '([^']+)' to '([^']+)'", r"cannot initialize a variable of type '([^']+)'", r"invalid conversion from"], "Type", _handle_type_mismatch),
    PatternRule("invalid_conversion", [r"reinterpret_cast from", r"cast to '([^']+)' from"], "Type", _handle_invalid_conversion),
    PatternRule("incompatible_operands", [r"invalid operands to binary expression", r"no match for 'operator"], "Type", _handle_incompatible_operands),
    PatternRule("wrong_function_arguments", [r"too few arguments to function", r"too many arguments to function", r"no matching function for call to", r"incorrect number of arguments"], "Function Call", _handle_function_arguments),
    PatternRule("unused_expression", [r"statement has no effect", r"unused variable '([^']+)'", r"value computed is not used", r"expression result unused"], "Warning", _handle_unused_expression),
    PatternRule("redefinition", [r"redefinition of '([^']+)'", r"previously declared here"], "Name Resolution", _handle_redefinition),
    PatternRule("conflicting_declaration", [r"conflicting declaration '([^']+)'"], "Name Resolution", _handle_conflicting_declaration),
    PatternRule("invalid_pointer_dereference", [r"invalid type argument of unary '\*'", r"indirection requires pointer operand"], "Type", _handle_invalid_pointer),
    PatternRule("break_outside_loop", [r"break statement not within loop", r"'break' is only allowed in loops"], "Control Flow", _handle_break_outside),
    PatternRule("continue_outside_loop", [r"continue statement not within a loop", r"'continue' is only allowed in loops"], "Control Flow", _handle_continue_outside),
    PatternRule("return_mismatch", [r"return-statement with a value, in function returning 'void'", r"void function '([^']+)' should not return a value"], "Type", _handle_return_mismatch),
    PatternRule("template_mismatch", [r"template argument deduction/substitution failed", r"no template named"], "Template", _handle_template_mismatch),
    PatternRule("invalid_operator", [r"expected primary-expression before '([^']+)'", r"expected expression"], "Syntax", _handle_invalid_operator),
    PatternRule("private_member_access", [r"is private within this context", r"is a private member of"], "Access Control", _handle_private_member),
    PatternRule("const_correctness", [r"assignment of read-only", r"cannot assign to variable .* with const-qualified type"], "Const Correctness", _handle_const_correctness),
    PatternRule("linker_error", [r"undefined reference to", r"unresolved external symbol"], "Linker", _handle_linker_error),
]

def solve_error(error, source_lines, ast_node) -> Dict[str, Any]:
    """
    Main entry point for smart error solver.
    """
    best_match = None
    best_rule = None
    
    msg = error.message if error.message else ""
    
    for rule in RULES:
        match = rule.match(msg)
        if match:
            best_match = match
            best_rule = rule
            break
            
    if best_rule:
        res = best_rule.handler(error, source_lines, ast_node, best_match)
        
        # AST context augmentation
        if ast_node:
            if ast_node == "BinaryOperator" and "operator" not in res["explanation"].lower():
                res["explanation"] += " (Operator context identified via AST)."
            elif ast_node == "CallExpr" and "function" not in res["explanation"].lower():
                res["explanation"] += " (Call expression context identified via AST)."
            elif "Decl" in ast_node and "declar" not in res["explanation"].lower():
                res["explanation"] += " (Declaration context identified via AST)."
        
        return {
            "category": best_rule.category,
            "explanation": res["explanation"],
            "suggestion": res["suggestion"],
            "possible_fix": res.get("possible_fix"),
            "confidence": 0.95
        }
    
    return {
        "category": "Unknown",
        "explanation": "A complex error occurred without a known smart pattern.",
        "suggestion": "Read the compiler output and trace the AST scope.",
        "possible_fix": None,
        "confidence": 0.3
    }
