"""
UI package for code editor and hex viewer interface components.

This package implements the user interface components for the code editor
and hex viewer, including the WindowManager for managing multiple windows
and the InputHandler for handling user input.
"""

from .window import WindowManager
from .input_handler import InputHandler

__all__ = ['WindowManager', 'InputHandler']
