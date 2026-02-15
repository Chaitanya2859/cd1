from compiler_runner import run_cpp_compiler
from error_parser import parse_error
from error_explainer import load_error_data, explain_error
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <file.cpp>")
        return
    cpp_file = sys.argv[1]

    print("Compiling:", cpp_file)
    error_output = run_cpp_compiler(cpp_file)

    if not error_output:
        print("Compilation successful")
        return

    parsed_error = parse_error(error_output)
    error_data = load_error_data()
    explanation = explain_error(parsed_error, error_data)

    print("Compiler Error")
    print(parsed_error)

    print("\n Explanation:")
    print(explanation["explanation"])

    print("\n Suggested Fix:")
    print(explanation["fix"])

if __name__ == "__main__":
    main()


