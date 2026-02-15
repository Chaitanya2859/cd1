import json
import os

def load_error_data():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base_dir, "data", "errors.json")

    with open(json_path, "r") as f:
        return json.load(f)["errors"]

def explain_error(parsed_error, error_data):
    #Matches parsed compiler error with known errors.

    for err in error_data:
        if err["raw_message"] in parsed_error:
            return {
                "explanation": err["explanation"],
                "fix": err["common_fix"]
            }

    return {
        "explanation": "This compiler error is not yet in the knowledge base.",
        "fix": "Check the syntax, variable declarations, and types."
    }
