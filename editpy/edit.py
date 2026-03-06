#!/usr/bin/python3

"""
Entry point script for EditPy.
"""

import sys
import curses
import argparse
import os

from src.editpy.core.buffer import Buffer
from src.editpy.ui.window import WindowManager
from src.editpy.ui.input_handler import InputHandler
from src.editpy.core.syntax import SyntaxHighlighter


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="EditPy - Advanced Terminal Text Editor and Hex Viewer"
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=str,
        help="Files to open"
    )
    return parser.parse_args()


def main_with_args(stdscr: 'curses.window') -> None:
    """Main function with command line arguments."""

    curses.use_default_colors()
    curses.curs_set(0)
    stdscr.timeout(100)

    window_manager = WindowManager(stdscr)
    input_handler = InputHandler(window_manager)

    args = parse_args()
    for filename in args.files:
        try:
            buf = Buffer()
            if not os.path.exists(filename):
                buf.code_lines = ['']
                buf.filename = filename
                buf.is_code_file = True
                buf.edit_mode = True

                highlighter = SyntaxHighlighter()
                buf.language = highlighter.detect_language(filename, '')

                window_manager.add_buffer(buf)
                window_manager.status_message = f"Created new file: {filename}"
            else:
                buf.load_file(filename)
                window_manager.add_buffer(buf)
        except Exception as e:
            curses.endwin()
            print(f"Error loading {filename}: {e}", file=sys.stderr)
            sys.exit(1)

    if not window_manager.buffers:
        window_manager.add_buffer(Buffer())

    try:
        while True:
            current_height, current_width = stdscr.getmaxyx()
            if (current_height, current_width) != (window_manager.height, window_manager.width):
                window_manager.resize()

            window_manager.refresh_all()

            try:
                ch = stdscr.getch()
                if ch != -1:
                    if not input_handler.handle_input(ch):
                        break
            except KeyboardInterrupt:
                break
            except curses.error:
                continue

    except Exception as e:
        curses.endwin()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Entry point for the application."""
    curses.wrapper(main_with_args)


if __name__ == "__main__":
    main()
