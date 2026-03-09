import re
from typing import Dict, Any, Optional
from error_classifier import get_default_classifier, predict_error_category

CATEGORY_TEMPLATES = {
    "Syntax":{
        "explanation":"The compiler is reporting a syntax error.",
        "suggestion":"Check for missing semicolons, mismatched parentheses/braces, and misplaced tokens near the reported location.",
    },
    "Name Resolution":{
        "explanation":"The compiler cannot resolve an identifier (name) in the current scope.",
        "suggestion":"Check spelling, ensure the symbol is declared before use, and include the right headers/namespaces.",
    },
    "Type":{
        "explanation":"The compiler detected a type-related issue.",
        "suggestion":"Check the types involved, implicit/explicit conversions, and that function overloads match the argument types.",
    },
    "Linker":{
        "explanation":"The linker could not find a required symbol definition.",
        "suggestion":"Ensure the function/variable is defined, and that you are linking the correct object files/libraries.",
    },
    "Control Flow":{
        "explanation":"The compiler detected an issue with control flow usage.",
        "suggestion":"Verify statements like break/continue/return are used in valid contexts.",
    },
    "Warning":{
        "explanation":"The compiler emitted a warning.",
        "suggestion":"Review the warning and adjust code to avoid potential bugs (or explicitly silence if intended).",
    },
    "Access Control":{
        "explanation":"The compiler detected an access control violation.",
        "suggestion":"Check member visibility (private/protected/public) and access through appropriate methods.",
    },
    "Const Correctness":{
        "explanation":"The compiler detected a const-correctness issue.",
        "suggestion":"Ensure const objects only call const methods, and avoid modifying const-qualified data.",
    },
    "Template":{
        "explanation":"The compiler detected a template usage issue.",
        "suggestion":"Check template arguments and ensure templates are instantiated with the correct parameters.",
    },
    "Undefined Behavior":{
        "explanation":"The compiler warned about a potential undefined behavior issue.",
        "suggestion":"Initialize variables, avoid division by zero, and ensure operations are safe for all inputs.",
    },
    "AST-Based Analysis":{
        "explanation":"The compiler found a problem near this line, but it doesn’t match a known pattern.",
        "suggestion":"Inspect the highlighted line and surrounding code. Verify syntax, types, and required declarations.",
    },
}


def format_error(what:str, why:str, how:str) -> str:
    return (
        f"What happened:\n"
        f" {what}\n\n"
        f"Why it happened:\n"
        f" {why}\n\n"
        f"How to fix it:\n"
        f" {how}"
    )


def extract_tokens(message:str)->Dict[str,Optional[str]]:
    tokens:Dict[str, Optional[str]]={
        "identifier":None,
        "function":None,
        "expected_token":None,
        "from_type":None,
        "to_type":None,
        "arg_expected":None,
        "arg_provided":None,
    }

    if not message:
        return tokens

    m = re.search(r"expected\s+(.+?)(?:\s+before|\s+after|\s+at|$)", message, re.IGNORECASE)
    if m:
        tokens["expected_token"] = m.group(1).strip().strip("`\"'")

    m = re.search(r"'([^']+)'\s+was not declared in this scope", message, re.IGNORECASE)
    if m:
        tokens["identifier"] = m.group(1)
    m = re.search(r"use of undeclared identifier\s+'([^']+)'", message, re.IGNORECASE)
    if m:
        tokens["identifier"] = m.group(1)

    m = re.search(r"no matching function for call to\s+'([^']+)'", message, re.IGNORECASE)
    if m:
        tokens["function"] = m.group(1)

    m = re.search(r"cannot convert\s+'([^']+)'\s+to\s+'([^']+)'", message, re.IGNORECASE)
    if m:
        tokens["from_type"] = m.group(1)
        tokens["to_type"] = m.group(2)

    m = re.search(r"conversion from\s+'([^']+)'\s+to\s+'([^']+)'", message, re.IGNORECASE)
    if m and not tokens["from_type"] and not tokens["to_type"]:
        tokens["from_type"] = m.group(1)
        tokens["to_type"] = m.group(2)

    m = re.search(
        r"requires\s+(\d+)\s+argument[s]?,\s+but\s+(\d+)\s+were provided",
        message,
        re.IGNORECASE,
    )
    if m:
        tokens["arg_expected"] = m.group(1)
        tokens["arg_provided"] = m.group(2)

    return tokens


def explain_category(category:str, message:str) -> Optional[Dict[str, str]]:
    t = extract_tokens(message)

    if category=="missing_semicolon":
        expected=t.get("expected_token") or ";"
        what=f"The compiler expected a statement terminator ({expected}), but it wasn’t found where it needed one."
        why="In C/C++, most statements must end with a semicolon. If it’s missing, the parser gets out of sync and reports an error at the next token."
        how="Add the missing semicolon at the end of the statement (often the line just before the reported location)."
        return {
            "explanation":format_error(what, why, how),
            "suggestion":"Add the missing ';' and recompile.",
        }
    
    if "break" in message and "not in loop" in message:
        what = "You used a 'break' statement outside of a loop or switch block."
        why = "In C++, 'break' can only appear inside loops (for, while, do-while) or switch statements."
        how = "Move the 'break' inside a valid loop/switch, or remove it if unnecessary."

        return {
            "explanation":format_error(what, why, how),
            "suggestion":"Ensure 'break' is inside a loop or switch block.",
        }

    if category == "unused_expression":
        what = "An expression was evaluated, but its result wasn’t used for anything."
        why = "This often happens when you write something like `a + b;` intending to assign or return the value, but you never store it."
        how = "Assign the result (e.g., `x = a + b;`), return it (`return a + b;`), or remove the expression if it’s not needed."
        return {
            "explanation":format_error(what, why, how),
            "suggestion":"Use the expression result (assign/return) or remove it.",
        }

    if category == "undeclared_variable":
        name = t.get("identifier")
        quoted = f"'{name}'" if name else "the identifier"
        what = f"You used {quoted}, but the compiler doesn’t know what it refers to in this scope."
        why = "This happens when a variable/function isn’t declared yet, is declared in a different scope, or a header/namespace is missing."
        how = "Declare it before use, include the correct header, and verify spelling and namespace qualifiers."
        return {
            "explanation":format_error(what, why, how),
            "suggestion":"Declare the identifier before use (or include the right header) and recompile.",
        }

    if category == "type_mismatch":
        ft = t.get("from_type")
        tt = t.get("to_type")
        if ft and tt:
            what = f"A value of type '{ft}' is being used where a '{tt}' is required."
        else:
            what = "Two parts of an expression have incompatible types."
        why = "C++ only allows implicit conversions in some cases. When there’s no safe conversion, the compiler rejects the operation."
        how = "Change the variable types to match, adjust the expression, or use an explicit cast only if it’s logically safe."
        return {
            "explanation":format_error(what, why, how),
            "suggestion":"Make the operand/variable types compatible (or add a safe explicit cast).",
        }

    if category=="function_mismatch":
        fn=t.get("function")
        exp=t.get("arg_expected")
        got=t.get("arg_provided")
        target=f"'{fn}'" if fn else "the function"
        if exp and got:
            what=f"You called {target} with {got} argument(s), but the available overload expects {exp}."
        else:
            what=f"No available overload of {target} matches the arguments you provided."
        why="Function overload resolution depends on the number and types of arguments. If none match, the compiler can’t choose a function to call."
        how="Check the function signature, pass the correct number/type of arguments, or add/adjust an overload that matches your call."
        return {
            "explanation":format_error(what,why,how),
            "suggestion":"Fix the call to match an existing signature (or implement an overload).",
        }

    return None

SECURITY_RULES=[
    {
        "pattern":r"may be used uninitialized",
        "risk":"High",
        "reason":"Uninitialized variables may cause undefined behavior or memory corruption."
    },
    {
        "pattern":r"division by zero",
        "risk":"High",
        "reason":"Division by zero can crash the program or cause undefined behavior."
    },
    {
        "pattern":r"invalid conversion",
        "risk":"Medium",
        "reason":"Incorrect type conversion may lead to memory or logic errors."
    },
    {
        "pattern":r"assignment of read-only location",
        "risk":"Medium",
        "reason":"Modifying const-qualified data may indicate unsafe design."
    },
    {
        "pattern":r"undefined reference",
        "risk":"Low",
        "reason":"Linker errors typically do not introduce runtime vulnerabilities."
    }
]

def explain_error(error)->Dict[str, Any]:
    if not error or not error.message:
        return {
            "explanation":"No error message provided.",
            "suggestion":"Check the compilation command and input files.",
            "category":"Unknown",
            "confidence":0.0
        }

    classifier = get_default_classifier()
    category, confidence = classifier.predict(error.message)

    # Secondary regex fallbacks for definitive patterns if ML confidence is low
    if confidence < 0.45:
        if re.search(r"expression result unused", error.message, re.IGNORECASE):
            category = "unused_expression"
            confidence = 0.95
        elif re.search(r"expected\s+';" , error.message, re.IGNORECASE) or re.search(r"expected\s*';'", error.message, re.IGNORECASE):
            category = "missing_semicolon"
            confidence = 0.95
        elif re.search(r"was not declared in this scope", error.message, re.IGNORECASE) or re.search(r"use of undeclared identifier", error.message, re.IGNORECASE):
            category = "undeclared_variable"
            confidence = 0.95
        elif re.search(r"cannot convert", error.message, re.IGNORECASE) or re.search(r"invalid conversion", error.message, re.IGNORECASE) or re.search(r"narrowing conversion", error.message, re.IGNORECASE):
            category = "type_mismatch"
            confidence = 0.9
        elif re.search(r"no matching function for call to", error.message, re.IGNORECASE) or re.search(r"candidate function not viable", error.message, re.IGNORECASE) or re.search(r"requires\s+\d+\s+argument", error.message, re.IGNORECASE):
            category = "function_mismatch"
            confidence = 0.9

    # Map fine-grained ML categories to high-level template categories
    category_map = {
        "missing_semicolon": "Syntax",
        "undeclared_variable": "Name Resolution",
        "type_mismatch": "Type",
        "function_mismatch": "Type",
        "unused_expression": "Warning",
        "scope_error": "Name Resolution",
    }
    
    template_category = category_map.get(category, category)
    min_confidence = 0.35

    fine = explain_category(category, error.message)
    if fine :
        explanation = fine["explanation"]
        suggestion = fine["suggestion"]
        node = getattr(error, "ast_node", None)
        if node:
            explanation += f" This error occurred inside a {node}."
            confidence = min(1.0, confidence + 0.05)
        return {
            "explanation":explanation,
            "suggestion":suggestion,
            "category":category,
            "confidence":confidence,
        }

    if template_category and confidence>=min_confidence:
        template = CATEGORY_TEMPLATES.get(template_category)
        if template:
            explanation = template.get("explanation")
            suggestion = template.get("suggestion")
        else:
            explanation = "The compiler reported an error in this category."
            suggestion = "Inspect the highlighted line and surrounding code to resolve the issue."

        node = getattr(error, "ast_node", None)
        if node:
            explanation += f" This error occurred inside a {node}."
            confidence = min(1.0, confidence + 0.05)

        return {
            "explanation":explanation,
            "suggestion":suggestion,
            "category":template_category,
            "confidence":confidence,
        }

    node=getattr(error, "ast_node", None)

    if node=="DeclStmt":
        explanation=(
        format_error(
            "A declaration statement (like declaring a variable) contains something the compiler can’t parse.",
            "Declarations have a strict grammar:a type, a name, and sometimes an initializer. Missing tokens (like ';') or invalid types commonly trigger this.",
            "Re-check the declaration for missing semicolons, typos in the type name, and correct initializer syntax."
        )
        )
    elif node == "BinaryOperator":
        explanation=(
        format_error(
            "An operator (like +, -, =, ==) is being applied in a way the compiler can’t type-check.",
            "Operators require operands of compatible types and sometimes require user-defined overloads.",
            "Verify both operand types and the operator. If needed, convert types or implement the appropriate overload."
        )
        )
    elif node == "CallExpr":
        explanation=(
        format_error(
            "A function call could not be matched to a valid function signature.",
            "This usually means the function name is wrong, the argument count is wrong, or argument types don’t match any overload.",
            "Check the function declaration and update the call to match the expected signature."
        )
        )
    elif node == "IfStmt":
        explanation=(
        format_error(
            "There is an error inside an if-statement condition or body.",
            "If conditions must be valid expressions, and the body must be syntactically correct. A missing ')' or ';' earlier can also surface here.",
            "Ensure the condition is a valid expression and braces/parentheses are balanced."
        )
    )
    elif node == "ReturnStmt":
        explanation=(
        format_error(
            "A return statement doesn’t match what the function promises to return.",
            "If a function has a non-void return type, every path must return a compatible value.",
            "Return a value of the correct type (or adjust the function’s return type)."
        )
        )
    else:
        explanation=(
        format_error(
            "The compiler rejected something in this statement.",
            "This usually happens because the code violates C++ syntax rules or uses a name/type that isn’t valid in this context.",
            "Read the compiler message carefully, identify the referenced token/name, and correct the statement accordingly."
        )
    )

    return {
        "explanation":explanation,
        "suggestion":(
            "Use the compiler message as a clue:fix the referenced token/name/type, then recompile to confirm the next issue (if any)."
        ),
        "category":"AST-Based Analysis",
        "confidence":0.5 if node else 0.3
    }

def analyze_security_risk(error):
    if not error or not error.message:
        return "None", None

    for rule in SECURITY_RULES:
        if re.search(rule["pattern"], error.message, re.IGNORECASE):
            return rule["risk"], rule["reason"]
    return "Low", "No immediate security risk detected."


def enrich_error(error:'CompilerError') -> None:
    if not error:
        return
    result=explain_error(error)

    error.explanation=result["explanation"]
    error.suggestion=result["suggestion"]
    error.category=result["category"]
    error.confidence=result["confidence"]

    risk,reason=analyze_security_risk(error)
    error.security_risk=risk
    error.risk_reason=reason

    if error.file and error.line and not error.context:
        from error_parser import get_source_context
        error.context=get_source_context(error.file, error.line)