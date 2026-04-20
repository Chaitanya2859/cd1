# 🌿 Green Self-Healing Compiler

A C++ analysis and repair tool that combines compiler diagnostics, AST exploration, ML-powered error classification, automated code healing, and energy telemetry — all in one workflow.

---

## Features

- **Compile & Analyze** — Runs `g++ -std=c++17`, parses diagnostics into structured records, and enriches each with explanations, suggestions, and security risk labels
- **ML Error Classification** — Classifies errors using a trained model with regex fallbacks for low-confidence cases
- **Auto-Heal Loop** — Attempts bounded automated repair (up to 3 passes) with patch generation and recompilation
- **AST Explorer** — Extracts and visualizes a filtered Clang AST, stripping standard-library noise to focus on user code
- **Energy Dashboard** — Tracks power usage, carbon intensity, and execution time via CodeCarbon; uses graceful fallbacks on macOS
- **Function Call Graph** — Draws a lightweight static relationship graph of function definitions, internal calls, and included headers
- **Desktop GUI** — Full PyQt6 interface with code editor, diagnostics panel, diffs, and terminal output

---

## Project Structure

```
├── src/
│   ├── main.py              # CLI entry point
│   ├── gui.py               # PyQt6 desktop application
│   ├── compiler_runner.py   # g++ invocation and diagnostic capture
│   ├── error_parser.py      # Compiler diagnostic parsing
│   ├── error_explainer.py   # Explanation, suggestion, and security enrichment
│   ├── error_classifier.py  # ML-backed error classification
│   ├── ast_extractor.py     # Filtered Clang AST extraction
│   ├── heal_loop.py         # Auto-heal orchestration loop
│   ├── auto_healer.py       # Patch-generation logic
│   ├── diff_viewer.py       # Diff generation and HTML formatting
│   └── common_errors.py     # Curated compiler error glossary
├── data/                    # Training data and classifier artifacts
├── test_cases/              # Sample C++ error cases
├── file.cpp                 # Working example source file
└── requirements.txt
```

---

## Requirements

**Python dependencies:**

```
PyQt6>=6.4.0
scikit-learn>=1.2.0
joblib>=1.2.0
codecarbon>=2.3.0
```

**System tools:**

- `g++`
- `clang++`

---

## Installation

```bash
# Install Python dependencies
python3 -m pip install -r requirements.txt

# Verify system tools
g++ --version
clang++ --version
```

---

## Usage

### CLI

```bash
# Analyze a source file
python3 src/main.py file.cpp

# With JSON output and verbose context
python3 src/main.py file.cpp -j -v
```

| Flag | Description |
|---|---|
| `-j`, `--json` | Emit structured JSON output |
| `-v`, `--verbose` | Include code context lines |
| `-c`, `--context` | Number of context lines to show |

### GUI

```bash
python3 src/gui.py
```

The GUI provides four sidebar pages:

| Page | Description |
|---|---|
| **Editor & Analysis** | Code editor with diagnostics, diffs, and terminal output |
| **AST Explorer** | Filtered Clang AST tree view for the loaded source |
| **Energy Dashboard** | Power, carbon intensity, and execution time telemetry |
| **Call Graph** | Static function/module relationship graph |

---

## How the Auto-Heal Loop Works

1. Compile the current file
2. Parse and classify errors
3. Select the first fixable error
4. Generate a patch via `auto_healer.py`
5. Write the patched file and recompile
6. Repeat up to **3 attempts**

If repair fails, the GUI offers options to edit manually, skip the error, or provide a hint and retry.

---

## Energy Telemetry Notes

- Uses **CodeCarbon** for CPU/RAM/emissions tracking
- macOS `powermetrics` is disabled to avoid password prompts
- Displays `mW` and `mgCO2/Wh` so small workloads remain visible
- Shows animated placeholder telemetry until CodeCarbon produces a meaningful sample
- RAPL hardware counters are available on Linux via `/sys/class/powercap`; shown as unavailable on macOS

---

## Troubleshooting

**`g++ compiler not found`**
Install a C++ toolchain and ensure `g++` is on your `PATH`.

**AST extraction fails**
Ensure `clang++` is installed and available on your `PATH`.

**Model version warnings on startup**
The serialized classifier was built with an older `scikit-learn` version. The app will still run, but predictions may differ slightly from the original training environment.

**Energy page looks static**
The app shows placeholder telemetry until CodeCarbon emits a real sample. Restart the GUI and confirm CodeCarbon is installed in the same Python environment.

---

## Limitations

- Single-file compilation only (no multi-file project support yet)
- The call graph is heuristic-based, not a full semantic analysis
- Auto-heal only fixes error categories supported by `auto_healer.py`
- Energy telemetry on macOS is estimated, not hardware-precise
- GUI requires a local desktop environment (no web app mode)

---

## Roadmap

- [ ] Multi-file / project-level compilation and healing
- [ ] Stronger semantic and logical bug detection
- [ ] More accurate energy measurement on supported platforms
- [ ] Persistent repair history and learning from prior successful fixes
- [ ] Sandboxed execution for untrusted binaries
- [ ] Richer AST and call-graph interactions across files

---

## Typical Workflow

1. Launch the GUI: `python3 src/gui.py`
2. Load or paste a C++ file
3. Click **Compile** to inspect errors and suggestions
4. Review the **AST** on page 2 for structural context
5. Check **Energy** telemetry on page 3
6. Explore source relationships on page 4 (**Call Graph**)
7. Click **Auto-Heal** for fixable issues
8. **Run** the compiled binary and validate behavior
