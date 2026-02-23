import json
import os
import re
from typing import Dict, Any, Optional, List
from models import CompilerError

ERROR_PATTERNS=[
    {
        "pattern": r"expected ';' before",
        "explanation": "You likely forgot a semicolon at the end of a statement.",
        "suggestion": "Add a semicolon at the end of the line or the line before the error.",
        "category": "Syntax",
        "confidence": 0.9
    },
    {
        "pattern": r"expected ';' after expression",
        "explanation": "You forgot a semicolon at the end of an expression.",
        "suggestion": "Add a semicolon ';' at the end of the expression.",
        "category": "Syntax",
        "confidence": 0.9
    },
    {
        "pattern": r"was not declared in this scope",
        "explanation": "The variable or function name is not declared in the current scope.",
        "suggestion": "Check the spelling or declare the variable/function before using it.",
        "category": "Name Resolution",
        "confidence": 0.85
    },
    {
        "pattern": r"redeclaration of",
        "explanation": "The variable or function is being declared more than once.",
        "suggestion": "Remove the duplicate declaration or use a different name.",
        "category": "Name Resolution",
        "confidence": 0.9
    },
    {
        "pattern": r"does not name a type",
        "explanation": "The type name is not recognized.",
        "suggestion": "Check the spelling or include the appropriate header file.",
        "category": "Type",
        "confidence": 0.85
    },
    {
        "pattern": r"undefined reference to",
        "explanation": "The function or variable was declared but not defined.",
        "suggestion": "Make sure the function is implemented or the correct object file is linked.",
        "type": "linker",
        "category": "Linker",
        "confidence": 0.95
    },
    {
        "pattern": r"expected ',' or ';' before",
        "explanation": "A comma or semicolon is missing in the code.",
        "suggestion": "Add the missing comma or semicolon at the indicated location.",
        "category": "Syntax",
        "confidence": 0.88
    },
    {
        "pattern": r"no matching function for call to",
        "explanation": "The compiler could not find a function template specialization or overload that matches the provided arguments.",
        "suggestion": "Check the function name, parameter types, and template arguments.",
        "category": "Type",
        "confidence": 0.88
    },
    {
        "pattern": r"cannot convert",
        "explanation": "There's a type mismatch in the expression.",
        "suggestion": "Check the types of the variables and ensure they're compatible.",
        "category": "Type",
        "confidence": 0.87
    },
    {
        "pattern": r"expected ';' at end of member declaration",
        "explanation": "A semicolon is missing after a class/struct member declaration.",
        "suggestion": "Add a semicolon after the member declaration.",
        "category": "Syntax",
        "confidence": 0.9
    },
    {
        "pattern": r"expected unqualified-id before",
        "explanation": "The code has a syntax error where an identifier was expected.",
        "suggestion": "Check for missing or misplaced symbols in the code.",
        "category": "Syntax",
        "confidence": 0.8
    },
    {
        "pattern": r"'(.+)' was not declared in this scope",
        "explanation": "The variable or function '{}' was used but not declared.",
        "suggestion": "Declare '{}' before using it or include the appropriate header.",
        "capture_group": 1,
        "category": "Name Resolution",
        "confidence": 0.9
    },
    {
    "pattern": r"'?break'?\s+statement\s+not\s+(within|in)\s+loop\s+or\s+switch",
    "explanation": "The 'break' keyword can only be used inside loops or switch statements.",
    "suggestion": "Place the break statement inside a loop or remove it.",
    "category": "Control Flow",
    "confidence": 0.95
    },
    {
        "pattern": r"'(.+)' does not name a type",
        "explanation": "The type '{}' is not recognized.",
        "suggestion": "Check the spelling or include the appropriate header defining '{}'.",
        "capture_group": 1,
        "category": "Type",
        "confidence": 0.9
    },
    {
        "pattern": r"control reaches end of non-void function",
        "explanation": "A function declared with a non-void return type must return a value on all code paths.",
        "suggestion": "Add an appropriate return statement before the function ends.",
        "category": "Warning",
        "confidence": 0.75
    },
    {
        "pattern": r"'std::(.+)' has not been declared",
        "explanation": "The std namespace member '{}' is not recognized.",
        "suggestion": "Ensure the correct header (like <iostream>, <vector>, <string>) is included and '{}' is spelled correctly.",
        "capture_group": 1,
        "category": "Name Resolution",
        "confidence": 0.8
    },
    {
        "pattern": r"'cout' was not declared",
        "explanation": "The identifier 'cout' is defined in the <iostream> header.",
        "suggestion": "Add #include <iostream> at the top of your file.",
        "category": "Name Resolution",
        "confidence": 0.8
    },
    {
        "pattern": r"'vector' was not declared",
        "explanation": "The container 'vector' is defined in the <vector> header.",
        "suggestion": "Add #include <vector> at the top of your file.",
        "category": "Name Resolution",
        "confidence": 0.8
    },
    {
        "pattern": r"is private within this context",
        "explanation": "You are trying to access a private member of a class from outside the class.",
        "suggestion": "Make the member public or access it through a public member function.",
        "category": "Access Control",
        "confidence": 0.9
    },
    {
        "pattern": r"is protected within this context",
        "explanation": "You are trying to access a protected member from outside its allowed scope.",
        "suggestion": "Access it from a derived class or make it public if appropriate.",
        "category": "Access Control",
        "confidence": 0.9
    },
    {
        "pattern": r"passing 'const (.+)' as 'this' argument discards qualifiers",
        "explanation": "You are calling a non-const member function on a const object of type '{}'.",
        "suggestion": "Mark the member function as const or remove const from the object if appropriate.",
        "capture_group": 1,
        "category": "Const Correctness",
        "confidence": 0.85
    },
    {
        "pattern": r"assignment of read-only location",
        "explanation": "You are attempting to modify a const-qualified variable.",
        "suggestion": "Remove const from the variable if modification is intended.",
        "category": "Const Correctness",
        "confidence": 0.85
    },
    {
        "pattern": r"invalid use of template-name",
        "explanation": "You are using a template without providing the required template arguments.",
        "suggestion": "Provide template arguments inside angle brackets (<>).",
        "category": "Template",
        "confidence": 0.9
    },
    {
        "pattern": r"use of deleted function",
        "explanation": "You are trying to call a function that has been explicitly marked as deleted.",
        "suggestion": "Remove the call or provide a valid implementation.",
        "category": "Type",
        "confidence": 0.85
    },
    {
        "pattern": r"multiple definition of",
        "explanation": "The same function or global variable is defined in more than one translation unit.",
        "suggestion": "Ensure the definition appears in only one source file. Use 'extern' in headers.",
        "category": "Linker",
        "confidence": 0.9
    },
    {
        "pattern": r"invalid use of incomplete type",
        "explanation": "You are using a class or struct before its full definition is available.",
        "suggestion": "Include the appropriate header file or move the full definition before use.",
        "category": "Type",
        "confidence": 0.85
    },
    {
        "pattern": r"field has incomplete type",
        "explanation": "A class member is declared with a type that is forward-declared but not fully defined.",
        "suggestion": "Provide the full definition of the type before using it as a field.",
        "category": "Type",
        "confidence": 0.85
    },
    {
        "pattern": r"may be used uninitialized",
        "explanation": "A variable may be used before being initialized, leading to undefined behavior.",
        "suggestion": "Initialize the variable before using it.",
        "category": "Undefined Behavior",
        "confidence": 0.8
    },
    {
        "pattern": r"division by zero",
        "explanation": "The code performs a division where the denominator may be zero.",
        "suggestion": "Add a check to ensure the denominator is not zero before dividing.",
        "category": "Undefined Behavior",
        "confidence": 0.9
    },
    {
        "pattern": r"narrowing conversion",
        "explanation": "A value is being converted to a smaller type, which may lose data.",
        "suggestion": "Use static_cast<> explicitly or ensure the value fits in the target type.",
        "category": "Type",
        "confidence": 0.75
    },
    {
        "pattern": r"conversion from '(.+)' to '(.+)' may change value",
        "explanation": "Converting from '{}' to '{}' may result in data loss.",
        "suggestion": "Use explicit casting and verify that the conversion is safe.",
        "capture_group": 1,
        "category": "Type",
        "confidence": 0.75
    }
]

SECURITY_RULES=[
    {
        "pattern": r"may be used uninitialized",
        "risk": "High",
        "reason": "Uninitialized variables may cause undefined behavior or memory corruption."
    },
    {
        "pattern": r"division by zero",
        "risk": "High",
        "reason": "Division by zero can crash the program or cause undefined behavior."
    },
    {
        "pattern": r"invalid conversion",
        "risk": "Medium",
        "reason": "Incorrect type conversion may lead to memory or logic errors."
    },
    {
        "pattern": r"assignment of read-only location",
        "risk": "Medium",
        "reason": "Modifying const-qualified data may indicate unsafe design."
    },
    {
        "pattern": r"undefined reference",
        "risk": "Low",
        "reason": "Linker errors typically do not introduce runtime vulnerabilities."
    }
]

def explain_error(error) -> Dict[str, Any]:
    if not error or not error.message:
        return {
            "explanation": "No error message provided.",
            "suggestion": "Check the compilation command and input files.",
            "category": "Unknown",
            "confidence": 0.0
        }

    best=None
    maxi=0.0

    for pattern in ERROR_PATTERNS:
        if pattern.get("type") and pattern["type"]!=error.error_type:
            continue

        match=re.search(pattern["pattern"],error.message,re.IGNORECASE)
        if match:
            confidence=pattern.get("confidence",0.5)

            if confidence>maxi:
                explanation=pattern["explanation"]
                suggestion=pattern["suggestion"]

                if "capture_group" in pattern and match.groups():
                    idx=pattern["capture_group"] - 1
                    captured=match.group(idx + 1)
                    explanation=explanation.replace("{}", f"'{captured}'")
                    suggestion=suggestion.replace("{}", f"'{captured}'")

                best={
                    "explanation": explanation,
                    "suggestion": suggestion,
                    "category": pattern.get("category", "Unknown"),
                    "confidence": confidence
                }

                maxi=confidence

    if best:
        node=getattr(error, "ast_node", None)
        if node:
            best["explanation"] += f" This error occurred inside a {node}."
            best["confidence"]=min(1.0, best["confidence"] + 0.05)
        return best

    node=getattr(error, "ast_node", None)

    if node == "DeclStmt":
        explanation=(
        "This error happened while declaring a variable or object. "
        "It usually means something is missing or incorrectly written in the declaration, "
        "such as a missing semicolon or an invalid type."
        )
    elif node == "BinaryOperator":
        explanation=(
        "This error happened during an operation like assignment or comparison. "
        "It often means the types on both sides don’t match or the operator is being used incorrectly, "
        )
    elif node == "CallExpr":
        explanation=(
        "This error happened while calling a function. "
        "Check that the function name is correct and that you are passing the right number and type of arguments."
        )
    elif node == "IfStmt":
        explanation=(
        "This error occurred inside an if statement. "
        "Make sure the condition is written correctly and uses valid expressions."
    )
    elif node == "ReturnStmt":
        explanation=(
        "This error occurred in a return statement. "
        "Ensure the value you are returning matches the function’s declared return type."
        )
    else:
        explanation=(
        "The compiler found a problem near this line, but it doesn’t match a known pattern. "
        "Carefully review the syntax and logic around the highlighted line."
    )

    return {
        "explanation": explanation,
        "suggestion": (
            "Inspect the highlighted line and surrounding code. "
            "Verify syntax, types, and required declarations."
        ),
        "category": "AST-Based Analysis",
        "confidence": 0.5 if node else 0.3
    }

def analyze_security_risk(error):
    if not error or not error.message:
        return "None", None

    for rule in SECURITY_RULES:
        if re.search(rule["pattern"], error.message, re.IGNORECASE):
            return rule["risk"], rule["reason"]
    return "Low", "No immediate security risk detected."


def enrich_error(error: 'CompilerError') -> None:
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