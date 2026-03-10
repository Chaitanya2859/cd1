import sys
import os
import subprocess
import json
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QSplitter, QPlainTextEdit, QTextEdit,
                             QPushButton, QFileDialog, QMessageBox, QLabel, QFrame,
                             QCheckBox, QDialog, QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import Qt, QRect, QSize, QThread, pyqtSignal, QTimer, QVariantAnimation
from PyQt6.QtGui import QFont, QColor, QPainter, QTextFormat, QTextCharFormat, QSyntaxHighlighter, QTextCursor
import platform

from ast_extractor import extract_ast, extract_node_near_line, parse_ast_to_tree

BG_COLOR = "#222131"          
PANE_BG = "#212030"           
HEADER_BG = "#29273c"         
BORDER_COLOR = "#474360"      
PINK = "#d38dba"  
TEXT_MAIN = "#b0adca"         
TEXT_DIM = "#777492"          
KEYWORD_COLOR = "#cf86af"     
ERROR_LINE_COLOR = "#3c2a39" 
RED = "#ff5555"
YELLOW = "#f1fa8c"
GREEN = "#50fa7b"

FONT_FAMILY = "Menlo" if platform.system() == "Darwin" else "Consolas"

class StyledButton(QPushButton):
    def __init__(self, text, style_type="outline_dim", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
        
        self.style_type = style_type
        self._update_style(0)
        
        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(150)
        self.hover_anim.valueChanged.connect(self._update_style)

    def enterEvent(self, event):
        self.hover_anim.setStartValue(0)
        self.hover_anim.setEndValue(1)
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.setStartValue(1)
        self.hover_anim.setEndValue(0)
        self.hover_anim.start()
        super().leaveEvent(event)

    def _update_style(self, progress):
        if self.style_type == "outline_dim":
            c = QColor(BORDER_COLOR)
            h = QColor(HEADER_BG)
            r = int(c.red() + (h.red() - c.red()) * progress)
            g = int(c.green() + (h.green() - c.green()) * progress)
            b = int(c.blue() + (h.blue() - c.blue()) * progress)
            bg = f"rgb({r}, {g}, {b})"
            
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {BORDER_COLOR};
                    background-color: transparent;
                    color: {PINK};
                    padding: 8px 15px;
                }}
                QPushButton:hover {{
                    background-color: {bg};
                }}
                QPushButton:pressed {{
                    background-color: {BORDER_COLOR};
                    color: {TEXT_MAIN};
                }}
            """)
        elif self.style_type == "solid_pink":
            c = QColor(PINK)
            h = QColor("#df9cc6")
            r = int(c.red() + (h.red() - c.red()) * progress)
            g = int(c.green() + (h.green() - c.green()) * progress)
            b = int(c.blue() + (h.blue() - c.blue()) * progress)
            bg = f"rgb({r}, {g}, {b})"
            
            self.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {PINK};
                    background-color: {PINK};
                    color: {BG_COLOR};
                    padding: 8px 15px;
                }}
                QPushButton:hover {{
                    background-color: {bg};
                }}
                QPushButton:pressed {{
                    background-color: {KEYWORD_COLOR};
                }}
            """)


class StyledCheckBox(QCheckBox):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        self.setStyleSheet(f"color: {PINK};")

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.error_line = None

        self.update_line_number_area_width(0)
        self.highlight_current_line()
        
        self.setFont(QFont(FONT_FAMILY, 13))
        self.setStyleSheet(f"QPlainTextEdit {{ background-color: {PANE_BG}; color: {TEXT_MAIN}; border: none; }}")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def set_error_line(self, line):
        self.error_line = line
        self.highlight_current_line()
        self.viewport().update()

    def line_number_area_width(self):
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks /= 10
            digits += 1
        return 5 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(PANE_BG))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                
                if self.error_line and block_number + 1 == self.error_line:
                    painter.setPen(QColor(PINK))
                    painter.setFont(QFont(FONT_FAMILY, 13, QFont.Weight.Bold))
                else:
                    painter.setPen(QColor(TEXT_DIM))
                    painter.setFont(QFont(FONT_FAMILY, 13))
                    
                painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extraSelections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(HEADER_BG)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)

        if self.error_line is not None and self.error_line > 0:
            error_selection = QTextEdit.ExtraSelection()
            error_selection.format.setBackground(QColor(ERROR_LINE_COLOR))
            error_selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            
            cursor = QTextCursor(self.document())
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, n=self.error_line - 1)
            error_selection.cursor = cursor
            error_selection.cursor.clearSelection()
            extraSelections.append(error_selection)

        self.setExtraSelections(extraSelections)


class CppSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(KEYWORD_COLOR))
        keywords = ["int", "return", "if", "else", "for", "while", "class", "public", "private", "protected", "void", "namespace", "using", "auto"]
        for word in keywords:
            pattern = r"\b" + word + r"\b"
            self.highlightingRules.append((pattern, keywordFormat))

        stdFormat = QTextCharFormat()
        stdFormat.setForeground(QColor(TEXT_MAIN))
        self.highlightingRules.append((r"\bstd::\w+\b", stdFormat))

        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor(PINK))
        self.highlightingRules.append((r'".*"', stringFormat))
        self.highlightingRules.append((r"\b[0-9]+\b", stringFormat))

        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor(TEXT_DIM))
        self.highlightingRules.append((r"//[^\n]*", commentFormat))

        includeFormat = QTextCharFormat()
        includeFormat.setForeground(QColor(TEXT_DIM))
        self.highlightingRules.append((r"#\w+", includeFormat))

        bracketFormat = QTextCharFormat()
        bracketFormat.setForeground(QColor(TEXT_MAIN))
        self.highlightingRules.append((r"[\{\}\(\)\[\]]", bracketFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), format)


class CustomFrame(QFrame):
    def __init__(self, title, left_padding=False):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ border: 1px solid {BORDER_COLOR}; background-color: {PANE_BG}; }}")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.header = QLabel(f" {title} ")
        self.header.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        self.header.setStyleSheet(f"QLabel {{ background-color: {HEADER_BG}; color: {PINK}; border: none; border-bottom: 1px solid {BORDER_COLOR}; padding: 5px; }}")
        self.layout.addWidget(self.header)
            
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        pad = 20 if left_padding else 0
        self.content_layout.setContentsMargins(pad, pad, pad, pad)
        self.content_widget.setStyleSheet(f"QWidget {{ border: none; background-color: transparent; }}")
        self.layout.addWidget(self.content_widget)

    def set_title(self, title):
        self.header.setText(f" {title} ")

class CompilerWorker(QThread):
    finished = pyqtSignal(str, str, int)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            result = subprocess.run(self.cmd, capture_output=True, text=True)
            self.finished.emit(result.stdout, result.stderr, result.returncode)
        except Exception as e:
            self.finished.emit("", str(e), -1)

class RunnerWorker(QThread):
    finished = pyqtSignal(str, str, int)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            result = subprocess.run(self.cmd, capture_output=True, text=True, timeout=5)
            self.finished.emit(result.stdout, result.stderr, result.returncode)
        except subprocess.TimeoutExpired as e:
            self.finished.emit(e.stdout.decode() if e.stdout else "", "Timeout expired after 5s", -1)
        except Exception as e:
            self.finished.emit("", str(e), -1)


class ASTViewerDialog(QDialog):
    def __init__(self, ast_tree, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AST EXPLORER :: ARCHITECTURE VIEW")
        self.resize(1000, 700)
        self.setStyleSheet(f"QDialog {{ background-color: {BG_COLOR}; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        label = QLabel("ABSTRACT SYNTAX TREE")
        label.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {PINK}; margin-bottom: 10px;")
        layout.addWidget(label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["NODE TYPE", "DETAILS / SOURCE"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {PANE_BG};
                color: {TEXT_MAIN};
                border: 1px solid {BORDER_COLOR};
                font-family: {FONT_FAMILY};
                font-size: 12px;
                alternate-background-color: {BG_COLOR};
            }}
            QHeaderView::section {{
                background-color: {HEADER_BG};
                color: {PINK};
                border: 1px solid {BORDER_COLOR};
                padding: 10px;
                font-weight: bold;
            }}
            QTreeWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {HEADER_BG};
            }}
            QTreeWidget::item:selected {{
                background-color: {BORDER_COLOR};
                color: {PINK};
            }}
        """)
        
        self._populate(ast_tree, self.tree.invisibleRootItem())
        
        layout.addWidget(self.tree)
        
        btn_close = StyledButton(" CLOSE VIEWER ", "solid_pink")
        btn_close.clicked.connect(self.close)
        btn_close.setFixedWidth(150)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignCenter)

    def _populate(self, nodes, parent_item):
        for n in nodes:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, n["type"])
            item.setText(1, n["details"])
            
            if "Decl" in n["type"]:
                item.setForeground(0, QColor(PINK))
            elif "Stmt" in n["type"]:
                item.setForeground(0, QColor(KEYWORD_COLOR))
            elif "Expr" in n["type"]:
                item.setForeground(0, QColor(TEXT_MAIN))
            else:
                item.setForeground(0, QColor(TEXT_DIM))
                
            item.setForeground(1, QColor(TEXT_DIM))
            
            if n["children"]:
                self._populate(n["children"], item)


class AppGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CppCheck Error Explainer")
        self.resize(1400, 850)
        
        self.file_name = "file.cpp"
        self.file_path = os.path.join(os.getcwd(), self.file_name)
        self.errors_count = 0
        self.warnings_count = 0
        
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_COLOR}; }}")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        logo = QLabel("CppCheck Error Explainer")
        logo.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {PINK}; letter-spacing:1px;")
        header_layout.addWidget(logo)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        btn_load = StyledButton(" LOAD C++ FILE", "outline_dim")
        btn_load.clicked.connect(self.load_file)
        toolbar_layout.addWidget(btn_load)

        btn_compile = StyledButton(" COMPILE", "solid_pink")
        btn_compile.clicked.connect(self.analyze)
        toolbar_layout.addWidget(btn_compile)

        btn_run = StyledButton(" RUN CODE", "outline_dim")
        btn_run.clicked.connect(self.run_code)
        toolbar_layout.addWidget(btn_run)

        btn_ast = StyledButton(" AST VIEWER", "outline_dim")
        btn_ast.clicked.connect(self.view_ast)
        toolbar_layout.addWidget(btn_ast)

        self.cb_output_toggle = StyledCheckBox("Compile Output")
        self.cb_output_toggle.setChecked(True)
        self.cb_output_toggle.stateChanged.connect(self.toggle_output_pane)
        toolbar_layout.addWidget(self.cb_output_toggle)

        self.cb_dataset_toggle = StyledCheckBox("Dataset Collector")
        toolbar_layout.addWidget(self.cb_dataset_toggle)
        
        toolbar_layout.addSpacing(10)
        self.status_label = QLabel("STATUS: ● READY TO ANALYZE")
        self.status_label.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        self.status_label.setStyleSheet(f"color: {PINK};")
        toolbar_layout.addWidget(self.status_label)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {BG_COLOR}; }}")
        main_layout.addWidget(self.splitter, 1)

        self.pane_left = CustomFrame("<> " + self.file_name.upper())
        self.editor = CodeEditor()
        self.highlighter = CppSyntaxHighlighter(self.editor.document())
        self.pane_left.content_layout.addWidget(self.editor)
        self.splitter.addWidget(self.pane_left)

        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {BG_COLOR}; }}")
        self.splitter.addWidget(self.v_splitter)

        self.pane_right_top = CustomFrame("MESSAGE LOG :: FIX SUGGESTION", left_padding=True)
        self.ai_log = QTextEdit()
        self.ai_log.setReadOnly(True)
        self.ai_log.setFont(QFont(FONT_FAMILY, 12))
        self.ai_log.setStyleSheet(f"QTextEdit {{ background-color: transparent; border: none; color: {TEXT_MAIN}; }}")
        self.pane_right_top.content_layout.addWidget(self.ai_log)
        
        self.v_splitter.addWidget(self.pane_right_top)

        self.pane_right_bottom = CustomFrame("COMPILER OUTPUT :: SYSTEM TERMINAL", left_padding=True)
        self.compiler_log = QTextEdit()
        self.compiler_log.setReadOnly(True)
        self.compiler_log.setFont(QFont(FONT_FAMILY, 11))
        self.compiler_log.setStyleSheet(f"QTextEdit {{ background-color: transparent; border: none; color: {TEXT_MAIN}; line-height: 1.5; }}")
        self.pane_right_bottom.content_layout.addWidget(self.compiler_log)
        self.v_splitter.addWidget(self.pane_right_bottom)

        self.splitter.setSizes([700, 650])
        self.v_splitter.setSizes([500, 250])

        footer_layout = QHBoxLayout()
        self.status_bar_left = QLabel("Compiler: GCC 11.4 | Language: C++17 | Errors: 1 | Warnings: 0 | File Name: file.cpp")
        self.status_bar_left.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        self.status_bar_left.setStyleSheet(f"color: {TEXT_DIM};")
        footer_layout.addWidget(self.status_bar_left)
        
        footer_layout.addStretch()
        
        t2 = QLabel("● REC    ")
        t2.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        t2.setStyleSheet(f"color: {TEXT_DIM};")
        footer_layout.addWidget(t2)
        main_layout.addLayout(footer_layout)

        init_code = """// Enter your C++ code here\n"""
        self.editor.setPlainText(init_code)
        self.editor.set_error_line(None)
        self._update_footer()

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._animate_loading)
        self.loading_dots = 0
        self.is_loading = False
        self.loading_prefix = ""

    def _update_footer(self):
        text = f"Compiler: GCC 11.4 | Language: C++17 | Errors: {self.errors_count} | Warnings: {self.warnings_count} | File Name: {self.file_name}"
        self.status_bar_left.setText(text)

    def _animate_loading(self):
        frames = ["🍓      ", " 🍓     ", "  🍓    ", "   🍓   ", "    🍓  ", "     🍓 ", "      🍓", "     🍓 ", "    🍓  ", "   🍓   ", "  🍓    ", " 🍓     "]
        self.loading_dots = (self.loading_dots + 1) % len(frames)
        frame = frames[self.loading_dots]
        
        self.status_label.setText(f"{self.loading_prefix} {frame}")
        self.compiler_log.setHtml(f"<div style='color:{TEXT_MAIN}; font-family:{FONT_FAMILY}; font-size: 14px;'>{self.loading_prefix.strip()} {frame}</div>")

    def toggle_output_pane(self, state):
        should_show = (state == Qt.CheckState.Checked.value)
        self.pane_right_bottom.setVisible(should_show)

    def run_code(self):
        if not os.path.exists("./a.out"):
             self.compiler_log.setHtml(f"<span style='color:{PINK}'>File 'a.out' not found. Please compile first.</span>")
             return
             
        self.is_loading = True
        self.loading_prefix = "STATUS: ● EXECUTING BINARY "
        self.loading_timer.start(300)

        self.runner_thread = RunnerWorker(["./a.out"])
        self.runner_thread.finished.connect(self._on_run_finished)
        self.runner_thread.start()

    def _on_run_finished(self, stdout_text, stderr_text, returncode):
        self.loading_timer.stop()
        self.is_loading = False
        self.status_label.setText("STATUS: ● EXECUTION COMPLETE")
        
        output_html = ""
        if stdout_text:
            output_html += f"<pre style='font-family:{FONT_FAMILY}; color:{TEXT_MAIN};'>{stdout_text}</pre>"
        if stderr_text:
            output_html += f"<pre style='font-family:{FONT_FAMILY}; color:{RED};'>{stderr_text}</pre>"
            
        if not stdout_text and not stderr_text:
             output_html = f"<div style='color:{TEXT_DIM};'>Program executed successfully with no output. Return code: {returncode}</div>"
             
        self.compiler_log.setHtml(output_html)

    def view_ast(self):
        # Save first
        if not self.save_file():
            return
            
        self.status_label.setText("STATUS: ● EXTRACTING AST...")
        self.loading_prefix = "STATUS: ● PARSING AST "
        self.loading_timer.start(300)
        
        ast_text = extract_ast(self.file_path)
        self.loading_timer.stop()
        
        if not ast_text:
            self.ai_log.setHtml(f"<div style='color:{PINK}'>Failed to extract AST. Make sure clang++ is installed and code is syntactically valid.</div>")
            self.status_label.setText("STATUS: ● AST FAILED")
            return
            
        self.status_label.setText("STATUS: ● READY")
        tree_data = parse_ast_to_tree(ast_text, self.file_path)
        
        dialog = ASTViewerDialog(tree_data, self)
        dialog.exec()

    def load_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open C++ Source File", "", "C/C++ Files (*.cpp *.cc *.c *.h *.hpp);;All Files (*)")
        if filename:
            self.file_path = filename
            self.file_name = os.path.basename(filename)
            self.pane_left.set_title(f"<> {self.file_name.upper()}")
            self._update_footer()
            
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.setPlainText(content)
                self.editor.set_error_line(None) 
            except Exception:
                pass 

    def save_file(self):
        if not self.file_path:
            self.file_path = os.path.join(os.getcwd(), self.file_name)
        try:
            content = self.editor.toPlainText()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def analyze(self):
        if not self.save_file():
            self.compiler_log.setHtml(f"<div style='color:{PINK};'>ERROR: Could not save file before compiling.</div>")
            return

        self.ai_log.clear()
        self.compiler_log.clear()
        
        self.is_loading = True
        self.loading_prefix = "STATUS: ● ANALYZING "
        self.loading_timer.start(300)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(script_dir, "main.py")
        cmd = [sys.executable, main_script, self.file_path, "-j", "-v"]

        self.compiler_thread = CompilerWorker(cmd)
        self.compiler_thread.finished.connect(self._on_analysis_finished)
        self.compiler_thread.start()

    def _on_analysis_finished(self, stdout, stderr, returncode):
        self.loading_timer.stop()
        self.is_loading = False
        
        try:
            data = json.loads(stdout)
            self.render_json(data, stderr)
        except json.JSONDecodeError:
            err_block = f"<span style='color:{PINK};'>COMPILE ERRORS OR JSON DECODE ERROR:</span><br>{stdout}<br>{stderr}"
            self.compiler_log.setHtml(f"<div style='white-space:pre-wrap; font-family:{FONT_FAMILY};'>{err_block}</div>")
            self.status_label.setText("STATUS: ● ERROR")

    def render_json(self, data, raw_stderr):
        self.ai_log.clear()
        self.compiler_log.clear()

        status = data.get("status", "")
        if status == "success":
            self.status_label.setText("STATUS: ● SUCCESSFUL")
            self.ai_log.setHtml(f"<div style='color:{PINK}; font-weight:bold;'>NO ISSUES DETECTED.</div>")
            self.compiler_log.setHtml(f"<span style='color:{TEXT_MAIN};'>Compilation finished successfully.</span>")
            self.editor.set_error_line(None)
            self.errors_count = 0
            self.warnings_count = 0
            self._update_footer()
            return
            
        self.errors_count = data.get('error_count', 0)
        self.warnings_count = data.get('warning_count', 0)
        self.status_label.setText(f"STATUS: ● {self.errors_count} ERRORS FOUND")
        self._update_footer()

        errors = data.get("errors", [])
        ai_html = ""
        compiler_html = ""
        first_err_line = None
        
        for idx, e in enumerate(errors):
            etype = e.get("error_type", "error").lower()
            tag_color = RED if etype == "error" else YELLOW
            msg = e.get('message', 'Unknown Issue')
            file_name = e.get("file", "unknown")
            line = e.get("line", "?")
            col = e.get("column", "?")
            
            category = e.get('category', 'Syntax / Parser Error')
            confidence = e.get('confidence', 0.92)

            if first_err_line is None and line != "?":
                first_err_line = int(line)

            ai_html += f"""
            <div style="margin-bottom: 25px;">
                <span style="color:{tag_color}; font-weight:bold;">ISSUE DETECTED: {msg.upper()}</span><br>
                <span style="display:inline-block; border:1px solid {tag_color}; padding:2px 6px; border-radius:3px; font-size:10px; color:{tag_color}; margin-top:5px; margin-right:10px;">CAT: {category.upper()}</span>
                <span style="font-size:10px; color:{TEXT_DIM};">CONFIDENCE: {confidence*100:.1f}%</span><br><br>
                Found {etype} in <span style="color:{tag_color};">{os.path.basename(file_name)}</span> at line {line}.<br><br>
            """
            
            expl = e.get("explanation", "").replace('\n', '<br>')
            sugg = e.get("suggestion", "").replace('\n', '<br>')

            # Show the context line in the AI log too
            context = e.get("context", {})
            lines = context.get("lines", [])
            start = context.get("start_line", 1)
            
            error_snippet = ""
            if line != "?" and lines and type(lines) == list:
                idx = int(line) - start
                if 0 <= idx < len(lines):
                    error_snippet = lines[idx].strip()

            if error_snippet:
                ai_html += f"""
                <div style="background-color:{BG_COLOR}; border: 1px solid {BORDER_COLOR}; border-left: 4px solid {tag_color}; padding:10px; font-family:'{FONT_FAMILY}'; font-size:13px; margin-bottom:10px;">
                    <span style="color:{TEXT_DIM}">{line} | </span><span style="color:{TEXT_MAIN}">{error_snippet.replace('<','&lt;').replace('>','&gt;')}</span>
                </div>
                """

            if expl:
                ai_html += f"""
                <div style="background-color:{BG_COLOR}; border:1px solid {BORDER_COLOR}; padding:15px; margin: 10px 0px; font-family:'{FONT_FAMILY}';">
                    <span style="color:{TEXT_MAIN};">{expl}</span>
                </div><br>
                """

            if sugg:
                ai_html += f"<div style='color:{GREEN}; font-weight:bold; margin-bottom:5px;'>SUGGESTION:</div>"
                ai_html += f"<span style='color:{TEXT_MAIN}'>{sugg}</span><br>"
            if e.get("security_risk"):
                ai_html += f"<br><span style='color:{TEXT_DIM}'>SECURITY RISK: {e.get('security_risk')}</span>"
            ai_html += "</div>"
            
            compiler_html += f"<span style='color:{tag_color};'>[{etype.upper()}]</span> {os.path.basename(file_name)}:{line}:{col}: <span style='color:{tag_color};'>{etype}:</span> {msg}<br>"
            
            if lines and type(lines) == list:
                for i, lt in enumerate(lines, start=start):
                    txt = lt.replace('<','&lt;').replace('>','&gt;').rstrip()
                    if i == int(line) if line != "?" else False:
                        compiler_html += f" <span style='color:{tag_color};'>&gt;</span> {i:3} | <b style='color:{TEXT_MAIN}'>{txt}</b><br>"
                        if col != "?":
                            compiler_html += f"       {' ' * (len(str(i)) + 2 + int(col))}<span style='color:{tag_color}'>^</span><br>"
                    else:
                        compiler_html += f"   {i:3} | <span style='color:{TEXT_DIM}'>{txt}</span><br>"
            compiler_html += "<br>"

        self.editor.set_error_line(first_err_line)

        compiler_html += f"<br>C++_ANALYZER_V2.0.1_READY > _"
        self.ai_log.setHtml(ai_html)
        self.compiler_log.setHtml(f"<div style='white-space:pre-wrap; font-family:{FONT_FAMILY};'>{compiler_html}</div>")

def main():
    app = QApplication(sys.argv)
    window = AppGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()