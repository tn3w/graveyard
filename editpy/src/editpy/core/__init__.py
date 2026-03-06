"""
Core package for code editor and hex viewer functionality.

This package implements the core functionality of the code editor. It includes
the Buffer class for code editing and hex data manipulation, as well as the
SyntaxHighlighter class for syntax highlighting support.
"""

from .buffer import Buffer

__all__ = ['Buffer']