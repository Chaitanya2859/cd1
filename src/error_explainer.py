import json
import os
import re
from typing import Dict, Any, Optional, List


ERROR_PATTERNS = [
    {
        "pattern": r"expected ';' before",
        "explanation": "You likely forgot a semicolon at the end of a statement.",
        "suggestion": "Add a semicolon at the end of the line or the line before the error.",
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
    "pattern": r"break statement not within loop or switch",
    "explanation": "The 'break' keyword can only be used inside loops or switch statements.",
    "suggestion": "Place the break statement inside a loop or remove it.",
    "category": "Control Flow",
    "confidence": 0.9
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

def load_error_data()->List[Dict[str,Any]]:

    base_dir=os.path.dirname(os.path.dirname(__file__))
    json_path=os.path.join(base_dir,"data","errors.json")

    if os.path.exists(json_path):
        try:
            with open(json_path,"r") as f:
                return json.load(f).get("errors",[])
        except (json.JSONDecodeError,IOError):
            pass

    return ERROR_PATTERNS


def explain_error(error)->Dict[str,Any]:

    if not error or not error.message:
        return {
            "explanation":"No error message provided.",
            "suggestion":"Check the compilation command and input files.",
            "category":"Unknown",
            "confidence":0.0
        }

    best=None
    highest=0.0

    for pattern in ERROR_PATTERNS:

        if pattern.get("type") and pattern["type"]!=error.error_type:
            continue

        match=re.search(pattern["pattern"],error.message)

        if match:
            confidence=pattern.get("confidence",0.5)

            if confidence>highest:

                explanation=pattern["explanation"]
                suggestion=pattern["suggestion"]

                if "capture_group" in pattern and len(match.groups())>=1:
                    idx=pattern["capture_group"]-1
                    captured=match.group(idx+1)
                    explanation=explanation.replace("{}",f"'{captured}'")
                    suggestion=suggestion.replace("{}",f"'{captured}'")

                best={
                    "explanation":explanation,
                    "suggestion":suggestion,
                    "category":pattern.get("category","Unknown"),
                    "confidence":confidence
                }

                highest=confidence

    if best:
        return best

    return {
        "explanation":"The specific error message is not recognized in our database.",
        "suggestion":"Check the code around the error line for common syntax mistakes.",
        "category":"Unknown",
        "confidence":0.3
    }


def enrich_error(error:'CompilerError')->None:

    if not error:
        return

    result=explain_error(error)

    error.explanation=result["explanation"]
    error.suggestion=result["suggestion"]
    error.category=result["category"]
    error.confidence=result["confidence"]

    if error.file and error.line and not error.context:
        from error_parser import get_source_context
        error.context=get_source_context(error.file,error.line)