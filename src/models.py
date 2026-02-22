class CompilerError:
    def __init__(self, file, line, column, error_type, message, raw):
        self.file=file
        self.line=line
        self.column=column
        self.error_type=error_type.lower()
        self.message=message
        self.raw=raw

        self.explanation=None
        self.suggestion =None
        self.context=None
        self.category=None
        self.confidence=0.0

    def to_dict(self):
        return {
            "file":self.file,
            "line":self.line,
            "column":self.column,
            "type":self.error_type,
            "message":self.message,
            "explanation":self.explanation,
            "suggestion":self.suggestion,
            "context":self.context,
            "category":self.category,
            "confidence":self.confidence,
        }

    def __str__(self):
        out=[]

        if self.file:
            out.append(f"{self.file}:")
        if self.line:
            out.append(f"{self.line}:")
            if self.column:
                out.append(f"{self.column}:")

        if out:
            out[-1] += " "

        out.append(f"{self.error_type.upper()}:{self.message}")

        if self.explanation:
            out.append(f"\nExplanation:{self.explanation}")
        if self.suggestion:
            out.append(f"\nSuggestion:{self.suggestion}")
        if self.category:
            out.append(f"\nCategory:{self.category} (confidence:{self.confidence:.2f})")

        if self.context:
            out.append("\nContext:")
            start=self.context["start_line"]
            for i, line in enumerate(self.context["lines"], start=start):
                mark="→" if i == self.line else " "
                out.append(f"{i:4} {mark} {line.rstrip()}")
                if i == self.line and self.column:
                    pad=" " * (self.column + 6)
                    out.append(pad + "^")

        return "".join(out)
