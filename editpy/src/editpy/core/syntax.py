"""
Syntax highlighting module for the editor using Pygments.
"""

import re
import curses
from typing import List, Tuple, Dict, Optional, Any, Final
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.python import PythonLexer
from pygments.lexers.javascript import JavascriptLexer
from pygments.lexers.html import HtmlLexer
from pygments.lexers.css import CssLexer
from pygments.lexers.c_cpp import CLexer, CppLexer
from pygments.lexers.jvm import JavaLexer
from pygments.lexers.perl import PerlLexer
from pygments.lexers.php import PhpLexer
from pygments.lexers.ruby import RubyLexer
from pygments.lexers.shell import BashLexer
from pygments.lexers.rust import RustLexer
from pygments.lexers.dotnet import CSharpLexer
from pygments.token import Token
from pygments.util import ClassNotFound

SYNTAX_COLORS: Final[Dict[str, int]] = {
    'keyword': 1,      # Cyan
    'string': 2,       # Yellow
    'comment': 3,      # Green
    'function': 4,     # Cyan
    'class': 5,        # Magenta
    'number': 6,       # Red
    'operator': 7,     # White
    'variable': 8,     # Blue
    'default': 0,      # Default
}

C_PATTERN: Final[str] = r'^\s*(#include|int\s+main|void\s+main|struct\s+\w+\s*{)'
CPP_PATTERN: Final[str] = r'^\s*(class\s+\w+|namespace\s+\w+|template\s*<)'

LANGUAGE_PATTERNS: Final[Dict[str, Tuple[Any, str]]] = {
    r'^\s*(def|class|import|from|if __name__ == [\'"]__main__[\'"])': 
        (PythonLexer(), 'Python'),
    r'^\s*(function|const|let|var|document\.|window\.|=>)':
        (JavascriptLexer(), 'JavaScript'), 
    r'<html|<!DOCTYPE html|<body|<script|<div':
        (HtmlLexer(), 'HTML'),
    r'^\s*(\.|#|@media|body\s*{|html\s*{)':
        (CssLexer(), 'CSS'),
    r'^\s*(package|import\s+java|public\s+class)':
        (JavaLexer(), 'Java'),
    r'^\s*(module|use\s+strict|package)':
        (PerlLexer(), 'Perl'),
    r'^\s*(<?php|namespace|use\s+[\w\\]+;)':
        (PhpLexer(), 'PHP'),
    r'^\s*(require|module|def\s+\w+\s*\(|class\s+\w+\s*<)':
        (RubyLexer(), 'Ruby'),
    r'^\s*(#!\s*/bin/bash|function\s+\w+\s*\(\))':
        (BashLexer(), 'Bash'),
    r'^\s*(module|fn\s+\w+|pub\s+struct)':
        (RustLexer(), 'Rust'),
    r'^\s*(using\s+System|namespace\s+\w+|public\s+class)':
        (CSharpLexer(), 'C#'),
}

TOKEN_COLOR_MAP: Final[Dict[Any, int]] = {
    Token.Keyword: SYNTAX_COLORS['keyword'],
    Token.Keyword.Constant: SYNTAX_COLORS['keyword'],
    Token.Keyword.Declaration: SYNTAX_COLORS['keyword'],
    Token.Keyword.Namespace: SYNTAX_COLORS['keyword'],
    Token.Keyword.Pseudo: SYNTAX_COLORS['keyword'],
    Token.Keyword.Reserved: SYNTAX_COLORS['keyword'],
    Token.Keyword.Type: SYNTAX_COLORS['keyword'],
    
    Token.Name.Class: SYNTAX_COLORS['class'],
    Token.Name.Function: SYNTAX_COLORS['function'],
    Token.Name.Decorator: SYNTAX_COLORS['function'],
    
    Token.String: SYNTAX_COLORS['string'],
    Token.String.Char: SYNTAX_COLORS['string'],
    Token.String.Doc: SYNTAX_COLORS['string'],
    Token.String.Double: SYNTAX_COLORS['string'],
    Token.String.Escape: SYNTAX_COLORS['string'],
    Token.String.Heredoc: SYNTAX_COLORS['string'],
    Token.String.Interpol: SYNTAX_COLORS['string'],
    Token.String.Other: SYNTAX_COLORS['string'],
    Token.String.Regex: SYNTAX_COLORS['string'],
    Token.String.Single: SYNTAX_COLORS['string'],
    Token.String.Symbol: SYNTAX_COLORS['string'],
    
    Token.Comment: SYNTAX_COLORS['comment'],
    Token.Comment.Hashbang: SYNTAX_COLORS['comment'],
    Token.Comment.Multiline: SYNTAX_COLORS['comment'],
    Token.Comment.Preproc: SYNTAX_COLORS['comment'],
    Token.Comment.Single: SYNTAX_COLORS['comment'],
    Token.Comment.Special: SYNTAX_COLORS['comment'],
    
    Token.Number: SYNTAX_COLORS['number'],
    Token.Number.Bin: SYNTAX_COLORS['number'],
    Token.Number.Float: SYNTAX_COLORS['number'],
    Token.Number.Hex: SYNTAX_COLORS['number'],
    Token.Number.Integer: SYNTAX_COLORS['number'],
    Token.Number.Integer.Long: SYNTAX_COLORS['number'],
    Token.Number.Oct: SYNTAX_COLORS['number'],
    
    Token.Operator: SYNTAX_COLORS['operator'],
    Token.Operator.Word: SYNTAX_COLORS['operator'],
    
    Token.Name.Variable: SYNTAX_COLORS['variable'],
    Token.Name.Variable.Class: SYNTAX_COLORS['variable'],
    Token.Name.Variable.Global: SYNTAX_COLORS['variable'],
    Token.Name.Variable.Instance: SYNTAX_COLORS['variable'],
    Token.Name.Variable.Magic: SYNTAX_COLORS['variable'],
    
    Token.Text: SYNTAX_COLORS['default'],
    Token.Text.Whitespace: SYNTAX_COLORS['default'],
}

class SyntaxHighlighter:
    """Handles syntax highlighting for code files using Pygments."""

    def __init__(self) -> None:
        self.lexer = None
        self.language = None
        self.color_pairs_initialized = False

    def init_colors(self) -> None:
        """Initialize color pairs for syntax highlighting."""

        if self.color_pairs_initialized:
            return

        curses.init_pair(SYNTAX_COLORS['keyword'], curses.COLOR_CYAN, -1)
        curses.init_pair(SYNTAX_COLORS['string'], curses.COLOR_YELLOW, -1)
        curses.init_pair(SYNTAX_COLORS['comment'], curses.COLOR_GREEN, -1)
        curses.init_pair(SYNTAX_COLORS['function'], curses.COLOR_CYAN, -1)
        curses.init_pair(SYNTAX_COLORS['class'], curses.COLOR_MAGENTA, -1)
        curses.init_pair(SYNTAX_COLORS['number'], curses.COLOR_RED, -1)
        curses.init_pair(SYNTAX_COLORS['operator'], curses.COLOR_WHITE, -1)
        curses.init_pair(SYNTAX_COLORS['variable'], curses.COLOR_WHITE, -1)

        self.color_pairs_initialized = True

    def detect_language(self, filename: str, content: str) -> Optional[str]:
        """
        Detect the programming language of a file based on its extension and content.

        Args:
            filename: The name of the file
            content: The content of the file

        Returns:
            The detected language or None if not detected
        """

        try:
            self.lexer = get_lexer_for_filename(filename)
            self.language = self.lexer.name
            return self.language
        except ClassNotFound:
            pass

        for pattern, (lexer_class, lang_name) in LANGUAGE_PATTERNS.items():
            if re.search(pattern, content, re.MULTILINE):
                self.lexer = lexer_class
                self.language = lang_name
                return self.language

        if re.search(C_PATTERN, content, re.MULTILINE):
            if re.search(CPP_PATTERN, content, re.MULTILINE):
                self.lexer = CppLexer()
                self.language = 'C++'

                return self.language

            self.lexer = CLexer() 
            self.language = 'C'

            return self.language

        return None

    def highlight_line(self, line: str) -> List[Tuple[str, int]]:
        """
        Highlight a line of code using the detected lexer.

        Args:
            line: The line of code to highlight

        Returns:
            A list of (text, color_attr) tuples
        """

        if not self.lexer or not line:
            return [(line, curses.color_pair(0))]

        result = []

        tokens = list(self.lexer.get_tokens(line))

        for token_type, text in tokens:
            color_attr = self._get_token_color(token_type)

            color_attr = color_attr & ~curses.A_COLOR
            color_attr |= curses.color_pair(TOKEN_COLOR_MAP.get(token_type, 0))

            result.append((text, color_attr))

        return result

    def _get_token_color(self, token_type: Any) -> int:
        """
        Get the color attribute for a token type.

        Args:
            token_type: The Pygments token type

        Returns:
            The curses color attribute
        """

        if token_type in TOKEN_COLOR_MAP:
            return curses.color_pair(TOKEN_COLOR_MAP[token_type])

        while token_type.parent:
            token_type = token_type.parent
            if token_type in TOKEN_COLOR_MAP:
                return curses.color_pair(TOKEN_COLOR_MAP[token_type])

        return curses.color_pair(0)
    
    def get_language_name(self) -> Optional[str]:
        """Get the name of the currently detected language."""

        if self.language:
            return self.language

        return None
