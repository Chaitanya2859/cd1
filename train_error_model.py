import json
import os
from typing import List, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


PROJECT_ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
VECTORIZER_PATH = os.path.join(DATA_DIR, "error_tfidf_vectorizer.joblib")
MODEL_PATH = os.path.join(DATA_DIR, "error_logreg_model.joblib")


def _load_labeled_json_dataset(path: str) -> Tuple[List[str], List[str]]:
    if not os.path.exists(path):
        return [],[]
    try:
        with open(path,"r") as f:
            raw=json.load(f)
    except Exception:
        return [],[]

    if not isinstance(raw, list):
        return [],[]

    X: List[str]=[]
    y: List[str]=[]
    for row in raw:
        if not isinstance(row, dict):
            continue
        msg = row.get("message")
        cat = row.get("category")
        if not msg or not cat:
            continue
        X.append(str(msg))
        y.append(str(cat))
    return X, y


def get_small_labeled_dataset() -> Tuple[List[str], List[str]]:
    X = [
        "error: expected ';' after expression",
        "error: expected ';' before '}' token",
        "error: expected ';' before 'else'",
        "error: expected ';' at end of declaration",
        "error: expected ';' after class definition",
        "error: expected ';' after struct definition",
        "error: expected ';' before 'return'",
        "error: expected ';' before 'for'",
        "error: expected ';' before 'while'",
        "error: expected ';' before ')' token",
        "error: expected ';' before ',' token",
        "error: expected ';' before ':' token",
        "error: expected ';' before '}' token",
        "error: expected ';' after initializer",
        "error: expected ';' after top level declarator",
        "warning: expression result unused [-Wunused-value]",
        "warning: statement has no effect [-Wunused-value]",
        "warning: value computed is not used",
        "warning: unused value",
        "warning: left operand of comma operator has no effect [-Wunused-value]",
        "warning: right operand of comma operator has no effect [-Wunused-value]",
        "warning: expression result unused",
        "error: 'x' was not declared in this scope",
        "error: use of undeclared identifier 'count'",
        "error: 'cout' was not declared in this scope",
        "error: 'vector' was not declared in this scope",
        "error: 'printf' was not declared in this scope",
        "error: 'myFunc' was not declared in this scope",
        "error: 'Node' does not name a type",
        "error: identifier 'total' is undefined",
        "error: use of undeclared identifier 'i'",
        "error: 'size_t' was not declared in this scope",
        "error: undeclared identifier 'n'",
        "error: cannot convert 'int' to 'std::string'",
        "error: invalid conversion from 'int' to 'char*'",
        "error: invalid conversion from 'const char*' to 'int'",
        "error: cannot convert 'double' to 'int' in assignment",
        "error: cannot convert 'std::string' to 'int'",
        "error: narrowing conversion of 'x' from 'double' to 'int' [-Wnarrowing]",
        "error: invalid operands of types 'int' and 'std::string' to binary 'operator+'",
        "error: invalid operands to binary expression ('int' and 'const char *')",
        "error: no viable conversion from 'std::string' to 'const char *'",
        "error: conversion from 'long' to 'int' may change value [-Wconversion]",
        "error: cannot initialize a variable of type 'int' with an lvalue of type 'std::string'",
        "error: no matching function for call to 'foo(int, int)'",
        "error: candidate function not viable: requires 1 argument, but 2 were provided",
        "error: too many arguments to function call, expected 1, have 2",
        "error: too few arguments to function call, expected 2, have 1",
        "error: no matching function for call to 'push_back'",
        "error: no matching member function for call to 'insert'",
        "error: no instance of overloaded function matches the argument list",
        "error: invalid arguments to function 'max'",
        "error: cannot bind non-const lvalue reference of type 'int&' to an rvalue of type 'int'",
        "error: no matching constructor for initialization of 'Foo'",
        "error: redeclaration of 'int x'",
        "error: conflicting declaration 'double x'",
        "error: redefinition of 'x'",
        "error: multiple definition of 'main'",
        "error: duplicate symbol '_main'",
        "error: previous definition is here",
    ]

    y = [
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "missing_semicolon",
        "unused_expression",
        "unused_expression",
        "unused_expression",
        "unused_expression",
        "unused_expression",
        "unused_expression",
        "unused_expression",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "undeclared_variable",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "type_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "function_mismatch",
        "scope_error",
        "scope_error",
        "scope_error",
        "scope_error",
        "scope_error",
        "scope_error",
    ]

    return X, y


def train_and_save() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    X, y = get_small_labeled_dataset()
    extra_X, extra_y=_load_labeled_json_dataset(os.path.join(DATA_DIR, "training_data.json"))
    if extra_X and extra_y:
        X.extend(extra_X)
        y.extend(extra_y)

    vectorizer=TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
    )

    X_vec = vectorizer.fit_transform(X)

    model = LogisticRegression(
        max_iter=1000,
        n_jobs=None,
    )
    model.fit(X_vec, y)

    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(model, MODEL_PATH)

    print(f"Saved vectorizer to: {VECTORIZER_PATH}")
    print(f"Saved model to: {MODEL_PATH}")


if __name__ == "__main__":
    train_and_save()
