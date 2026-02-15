import re

def parse_error(error_output):
    #Parses GCC error output and extracts the main error message.
    lines = error_output.split("\n")
    
    for line in lines:
        if "error:" in line:
            # Extract text after 'error:'
            return line.split("error:", 1)[1].strip()
    return "Unknown compilation error"
