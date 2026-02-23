import os
import json
from typing import Dict, Any

DATA_DIR=os.path.join(os.path.dirname(os.path.dirname(__file__)),"data")
DATA_FILE=os.path.join(DATA_DIR,"training_data.json")

def log_example(error)->None:
    os.makedirs(DATA_DIR,exist_ok=True)
    entry={
        "message":error.message,
        "category":error.category,
        "explanation":error.explanation,
        "suggestion":error.suggestion,
        "confidence":error.confidence,
        "context":error.context
    }

    data=[]
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,"r") as f:
                data=json.load(f)
        except Exception:
            data=[]

    for existing in data:
        if(
            existing.get("message")==entry["message"]
            and existing.get("category")==entry["category"]
        ):
            return

    data.append(entry)

    with open(DATA_FILE,"w") as f:
        json.dump(data,f,indent=2)