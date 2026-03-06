"""
Input handler module for processing keyboard events.
"""

import curses
import os
from typing import Optional, Callable, Dict, List, Final

from ..core.buffer import Buffer, UndoAction
from ..core.syntax import SyntaxHighlighter
from .window import WindowManager
from ..utils.search import SearchEngine, SearchResult

SEARCH_MESSAGES: Final[Dict[str, str]] = {
    "text": "Search: Text mode",
    "hex": "Search: Hex mode (space-separated hex values, e.g. 'FF 00 A3')",
    "regex": "Search: Regex mode", 
    "wildcard": "Search: Wildcard mode (? = one character, * = any number of characters)"
}

UNSAVED_CHANGES_STATUS_MESSAGE: Final[str] = "Buffer has unsaved changes. Press Ctrl+W to save or Ctrl+X again to discard changes."
UNSAVED_CHANGES_STATUS_MESSAGE_BUFFER: Final[str] = "Buffer has unsaved changes. Press Ctrl+W to save first."
SEARCH_STATUS_MESSAGE: Final[str] = "Search mode. Type search query, press Enter to search, Esc to cancel."
REPLACE_STATUS_MESSAGE: Final[str] = "Replace mode. Type replacement text. Enter: replace current, Ctrl+A: replace all, Esc: cancel"
ONE_REPLACE_STATUS_MESSAGE: Final[str] = "Replaced 1 occurrence. Press Ctrl+N to find next match."
OPEN_MODE_STATUS_MESSAGE: Final[str] = "Open mode. Enter file path, press Enter to open."

class InputHandler:
    """Handles keyboard input and executes corresponding actions."""

    def __init__(self, window_manager: WindowManager) -> None:
        self.window_manager = window_manager
        self.window_manager.input_handler = self
        self.insert_mode = False
        self.search_mode = False
        self.replace_mode = False
        self.open_mode = False
        self.open_query = ""
        self.search_query = ""
        self.replace_query = ""
        self.search_type = "text"
        self.case_sensitive = False
        self.search_results: List[SearchResult] = []
        self.current_result_index = -1
        self.current_hex_digit = None
        self.command_handlers: Dict[int, Callable[[], None]] = self._setup_handlers()
        self.search_engine = None

    def _setup_handlers(self) -> Dict[int, Callable[[], None]]:
        """Set up the keyboard command handlers."""

        return {
            curses.KEY_LEFT: self._move_left,
            curses.KEY_RIGHT: self._move_right,
            curses.KEY_UP: self._move_up,
            curses.KEY_DOWN: self._move_down,
            curses.KEY_HOME: self._move_line_start,
            curses.KEY_END: self._move_line_end,
            curses.KEY_PPAGE: self._page_up,
            curses.KEY_NPAGE: self._page_down,

            curses.KEY_DC: self._delete_char,
            curses.KEY_BACKSPACE: self._backspace,
            ord('\n'): self._handle_enter,
            ord('\t'): self._handle_tab,

            ord('x') & 0x1f: self._quit,  # Ctrl + X (quit key)
            ord('w') & 0x1f: self._save,  # Ctrl + W (save key)
            ord('o') & 0x1f: self._start_open,  # Ctrl + O (open key)
            ord('f') & 0x1f: self._start_search,  # Ctrl + F (find key)
            ord('r') & 0x1f: self._start_replace,  # Ctrl + R (replace key)
            ord('b') & 0x1f: self._undo,  # Ctrl + Z (undo key)
            ord('y') & 0x1f: self._redo,  # Ctrl + Y (redo key)
            ord('k') & 0x1f: self._cut_line,  # Ctrl + K (cut line key)
            ord('u') & 0x1f: self._paste_line,  # Ctrl + U (paste line key)
            ord('e') & 0x1f: self._toggle_edit_mode,  # Ctrl + E (toggle edit mode key)
            ord('n') & 0x1f: self._find_next,  # Ctrl + N (find next key)
            ord('p') & 0x1f: self._find_previous,  # Ctrl + P (find previous key)
        }

    def handle_input(self, ch: int) -> bool:
        """Handle a single keyboard input. Returns False if should quit."""

        if self.open_mode or self.search_mode or self.replace_mode:
            # Enter
            if ch == ord('\n'):
                if self.open_mode:
                    self._execute_open()
                elif self.search_mode:
                    self._execute_search()
                elif self.replace_mode:
                    self._execute_replace()

                return True

            # Escape
            if ch == 27:
                # Check for Alt+Number combinations
                try:
                    next_ch = self.window_manager.stdscr.getch()
                    if ord('1') <= next_ch <= ord('9') and not self.insert_mode:
                        index = next_ch - ord('1')
                        self.window_manager.switch_buffer(index)
                        return True
                    elif next_ch == ord('c'):  # Alt+C - toggle case sensitivity
                        self.case_sensitive = not self.case_sensitive
                        self.window_manager.status_message = f"Case sensitivity: {'On' if self.case_sensitive else 'Off'}"
                        return True
                except:
                    pass

                # Reset mode and query
                if self.open_mode:
                    self.open_mode = False
                    self.open_query = ""
                elif self.search_mode:
                    self.search_mode = False
                    self.search_query = ""
                elif self.replace_mode:
                    self.replace_mode = False
                    self.replace_query = ""

                return True

            # Tab
            if ch == 9 and self.search_mode:
                self._cycle_search_type()
                return True

            # Ctrl+A
            if ch == ord('a') & 0x1f and self.replace_mode:
                self._replace_all()
                return True

            # Backspace
            if ch == curses.KEY_BACKSPACE or ch == 127:
                if self.open_mode and self.open_query:
                    self.open_query = self.open_query[:-1]
                elif self.search_mode and self.search_query:
                    self.search_query = self.search_query[:-1]
                elif self.replace_mode and self.replace_query:
                    self.replace_query = self.replace_query[:-1]

                return True

            # Printable characters
            if 32 <= ch <= 126:
                if self.open_mode:
                    self.open_query += chr(ch)
                elif self.search_mode:
                    self.search_query += chr(ch)
                elif self.replace_mode:
                    self.replace_query += chr(ch)

                return True

            return True

        if ch == 27:
            try:
                next_ch = self.window_manager.stdscr.getch()
                if ord('1') <= next_ch <= ord('9') and not self.insert_mode:
                    index = next_ch - ord('1')
                    self.window_manager.switch_buffer(index)
                    return True
            except:
                pass
            return True

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return True

        if buf.is_code_file and buf.edit_mode:
            if 32 <= ch <= 126: # Printable characters
                self._handle_code_input(ch)
                return True

        if self.insert_mode and self._is_hex_char(ch):
            self._handle_hex_input(ch)
            return True

        if ch in self.command_handlers:
            self.command_handlers[ch]()
            return True

        return True

    def _is_hex_char(self, ch: int) -> bool:
        """Check if character is a valid hex digit."""
        return (0x30 <= ch <= 0x39) or (0x41 <= ch <= 0x46) or (0x61 <= ch <= 0x66)

    def _handle_hex_input(self, ch: int) -> None:
        """Handle hex digit input in insert mode."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        hex_value = int(chr(ch), 16)

        if self.current_hex_digit is None:
            self.current_hex_digit = hex_value << 4
            return

        value = self.current_hex_digit | hex_value
        buf.replace_byte(buf.cursor_pos, value)

        self.current_hex_digit = None
        self._move_right()

    def _handle_code_input(self, ch: int) -> None:
        """Handle text input in code editing mode."""

        buf = self.window_manager.get_active_buffer()
        if not buf or not buf.is_code_file:
            return

        char = chr(ch)

        if len(buf.code_lines) == 0:
            buf.code_lines.append('')
            buf.cursor_line = 0
            buf.cursor_column = 0
        
        current_line = buf.get_code_line(buf.cursor_line)

        new_line = current_line[:buf.cursor_column] + char + current_line[buf.cursor_column:]

        buf.code_lines[buf.cursor_line] = new_line
        buf.modified = True

        buf.cursor_column += 1

    def _move_left(self) -> None:
        """Move cursor left."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            if buf.cursor_column > 0:
                buf.cursor_column -= 1
                return

            if buf.cursor_line > 0:
                buf.cursor_line -= 1
                buf.cursor_column = len(buf.get_code_line(buf.cursor_line))

        else:
            if buf.cursor_pos > 0:
                buf.cursor_pos -= 1

    def _move_right(self) -> None:
        """Move cursor right."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            line = buf.get_code_line(buf.cursor_line)
            if buf.cursor_column < len(line):
                buf.cursor_column += 1
                return

            if buf.cursor_line < len(buf.code_lines) - 1:
                buf.cursor_line += 1
                buf.cursor_column = 0

        else:
            if buf.cursor_pos < buf.get_size() - 1:
                buf.cursor_pos += 1

    def _move_up(self) -> None:
        """Move cursor up one line."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            if buf.cursor_line > 0:
                buf.cursor_line -= 1

                line = buf.get_code_line(buf.cursor_line)
                if len(line) == 0:
                    buf.cursor_column = 0
                    return

                buf.cursor_column = min(buf.cursor_column, len(line))

        else:
            if buf and buf.cursor_pos >= buf.bytes_per_line:
                buf.cursor_pos -= buf.bytes_per_line

    def _move_down(self) -> None:
        """Move cursor down one line."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            if buf.cursor_line < len(buf.code_lines) - 1:
                buf.cursor_line += 1

                line = buf.get_code_line(buf.cursor_line)
                if len(line) == 0:
                    buf.cursor_column = 0
                    return

                buf.cursor_column = min(buf.cursor_column, len(line))

        else:
            if buf and buf.cursor_pos + buf.bytes_per_line < buf.get_size():
                buf.cursor_pos += buf.bytes_per_line

    def _move_line_start(self) -> None:
        """Move cursor to start of line."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            buf.cursor_column = 0
            return

        buf.cursor_pos = (buf.cursor_pos // buf.bytes_per_line) * buf.bytes_per_line

    def _move_line_end(self) -> None:
        """Move cursor to end of line."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            line = buf.get_code_line(buf.cursor_line)
            buf.cursor_column = len(line)
            return

        line_start = (buf.cursor_pos // buf.bytes_per_line) * buf.bytes_per_line
        line_end = min(line_start + buf.bytes_per_line - 1, buf.get_size() - 1)
        buf.cursor_pos = line_end

    def _page_up(self) -> None:
        """Move cursor up one page."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if not buf.is_code_file:
            page_size = (self.window_manager.height - 3) * buf.bytes_per_line
            buf.cursor_pos = max(0, buf.cursor_pos - page_size)
            return

        page_size = self.window_manager.height - 3
        buf.cursor_line = max(0, buf.cursor_line - page_size)

        line = buf.get_code_line(buf.cursor_line)
        if len(line) == 0:
            buf.cursor_column = 0
            return

        buf.cursor_column = min(buf.cursor_column, len(line))

    def _page_down(self) -> None:
        """Move cursor down one page."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if not buf.is_code_file:
            page_size = (self.window_manager.height - 3) * buf.bytes_per_line
            buf.cursor_pos = min(buf.get_size() - 1, buf.cursor_pos + page_size)
            return

        page_size = self.window_manager.height - 3
        buf.cursor_line = min(len(buf.code_lines) - 1, buf.cursor_line + page_size)

        line = buf.get_code_line(buf.cursor_line)
        if len(line) == 0:
            buf.cursor_column = 0
            return

        buf.cursor_column = min(buf.cursor_column, len(line))

    def _delete_char(self) -> None:
        """Delete character at cursor."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if not buf.is_code_file or not buf.edit_mode:
            buf.delete_byte(buf.cursor_pos)
            return

        line = buf.get_code_line(buf.cursor_line)
        if buf.cursor_column < len(line):
            new_line = line[:buf.cursor_column] + line[buf.cursor_column + 1:]
            buf.code_lines[buf.cursor_line] = new_line
            buf.modified = True
            return

        if buf.cursor_line < len(buf.code_lines) - 1:
            next_line = buf.get_code_line(buf.cursor_line + 1)

            current_cursor_column = buf.cursor_column
            buf.code_lines[buf.cursor_line] = line + next_line

            buf.delete_line(buf.cursor_line + 1)

            buf.cursor_column = current_cursor_column
            buf.modified = True

    def _backspace(self) -> None:
        """Delete character before cursor."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if not buf.is_code_file or not buf.edit_mode:
            if buf.cursor_pos > 0:
                buf.cursor_pos -= 1
                buf.delete_byte(buf.cursor_pos)
            return

        if buf.cursor_column > 0:
            current_line = buf.get_code_line(buf.cursor_line)
            new_line = current_line[:buf.cursor_column - 1] + current_line[buf.cursor_column:]
            buf.code_lines[buf.cursor_line] = new_line
            buf.cursor_column -= 1
            buf.modified = True
            return

        if buf.cursor_line > 0:
            prev_line = buf.get_code_line(buf.cursor_line - 1)
            current_line = buf.get_code_line(buf.cursor_line)

            new_cursor_column = len(prev_line)

            buf.code_lines[buf.cursor_line - 1] = prev_line + current_line

            buf.delete_line(buf.cursor_line)

            buf.cursor_line -= 1
            buf.cursor_column = new_cursor_column
            buf.modified = True
            return

    def _handle_enter(self) -> None:
        """Handle enter key press."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if self.search_mode:
            self._execute_search()
            return

        if not buf.is_code_file or not buf.edit_mode:
            self._move_down()
            self._move_line_start()
            return

        if len(buf.code_lines) == 0:
            buf.code_lines.append('')
            buf.code_lines.append('')
            buf.cursor_line = 1
            buf.cursor_column = 0
            buf.modified = True
            return

        current_line_index = buf.cursor_line
        current_line = buf.get_code_line(current_line_index)

        text_before_cursor = current_line[:buf.cursor_column]
        text_after_cursor = current_line[buf.cursor_column:]

        buf.code_lines[current_line_index] = text_before_cursor

        old_cursor_line = buf.cursor_line

        buf.code_lines.insert(current_line_index + 1, text_after_cursor)

        buf.cursor_line = old_cursor_line + 1
        buf.cursor_column = 0
        buf.modified = True

    def _handle_tab(self) -> None:
        """Toggle between hex and ASCII views."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file and buf.edit_mode:
            buf.insert_text(buf.cursor_line, buf.cursor_column, "    ")
            return

        self.insert_mode = not self.insert_mode
        if self.insert_mode:
            return

        self.current_hex_digit = None

    def _toggle_edit_mode(self) -> None:
        """Toggle edit mode for code files."""

        buf = self.window_manager.get_active_buffer()
        if not buf or not buf.is_code_file:
            return

        buf.edit_mode = not buf.edit_mode
        self.window_manager.status_message = f"{'Edit' if buf.edit_mode else 'View'} mode"

    def _quit(self) -> None:
        """Quit the application or close the current buffer."""

        current_buffer = self.window_manager.get_active_buffer()
        if current_buffer and current_buffer.modified:
            self.window_manager.status_message = UNSAVED_CHANGES_STATUS_MESSAGE
            if not hasattr(self, '_quit_warning_shown') or not self._quit_warning_shown:
                self._quit_warning_shown = True
                return

        self._quit_warning_shown = False

        if len(self.window_manager.buffers) == 1:
            raise KeyboardInterrupt()

        self._close_current_buffer()

    def _close_current_buffer(self) -> None:
        """Close the current buffer and switch to another one."""

        if not self.window_manager.buffers:
            return

        current_buffer = self.window_manager.get_active_buffer()
        if current_buffer and current_buffer.modified:
            self.window_manager.status_message = UNSAVED_CHANGES_STATUS_MESSAGE_BUFFER
            return

        if current_buffer:
            current_buffer.close()

        current_index = self.window_manager.active_buffer_index
        self.window_manager.buffers.pop(current_index)

        if self.window_manager.buffers:
            if current_index >= len(self.window_manager.buffers):
                self.window_manager.active_buffer_index = len(self.window_manager.buffers) - 1
            else:
                self.window_manager.active_buffer_index = current_index
        else:
            self.window_manager.add_buffer(Buffer())

        self.window_manager.status_message = "File closed"

    def _save(self) -> None:
        """Save the current buffer."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        try:
            if not buf.filename:
                self.open_mode = True
                self.open_query = ""
                self.window_manager.dialog_window = None
                self.window_manager.status_message = "Enter filename to save"
                return

            if buf.save_file():
                self.window_manager.status_message = f"Saved: {buf.filename}"
                return

            self.window_manager.status_message = "Error: No filename specified"
        except Exception as e:
            self.window_manager.status_message = f"Error saving: {str(e)}"

    def _start_search(self) -> None:
        """Start search mode."""

        self.search_mode = True
        self.search_query = ""
        self.window_manager.status_message = SEARCH_STATUS_MESSAGE

    def _cycle_search_type(self) -> None:
        """Cycle through different search types."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            search_types = ["text", "regex", "wildcard"]
        else:
            search_types = ["text", "hex", "regex", "wildcard"]

        try:
            current_index = search_types.index(self.search_type)
            next_index = (current_index + 1) % len(search_types)
            self.search_type = search_types[next_index]
        except ValueError:
            self.search_type = search_types[0]

        self.window_manager.status_message = SEARCH_MESSAGES.get(self.search_type, "Unknown search type")

    def _execute_search(self) -> None:
        """Execute the search with current query and settings."""

        if not self.search_query:
            self.search_mode = False
            return

        buf = self.window_manager.get_active_buffer()
        if not buf:
            self.search_mode = False
            return

        if not self.search_engine or self.search_engine.buffer != buf:
            self.search_engine = SearchEngine(buf)

        self.search_results = self.search_engine.find_all(
            self.search_query, 
            self.search_type,
            self.case_sensitive
        )

        if not self.search_results:
            self.window_manager.status_message = f"No matches found for '{self.search_query}'"
            self.current_result_index = -1
            self.search_mode = False
            return

        self.current_result_index = 0
        result = self.search_results[0]

        if buf.is_code_file:
            line_start = 0
            for i, line in enumerate(buf.code_lines):
                line_length = len(line.encode('utf-8')) + 1
                if line_start <= result.position < line_start + line_length:
                    buf.cursor_line = i
                    buf.cursor_column = result.position - line_start
                    break
                line_start += line_length
        else:
            buf.cursor_pos = result.position

        self.window_manager.status_message = (
            f"Found {len(self.search_results)} matches for '{self.search_query}'. "
            f"Match 1 of {len(self.search_results)}."
        )

        self.search_mode = False

    def _find_next(self) -> None:
        """Find the next search result."""

        if not self.search_results:
            self._start_search()
            return

        if self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
        else:
            self.current_result_index = 0

        result = self.search_results[self.current_result_index]
        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            line_start = 0
            for i, line in enumerate(buf.code_lines):
                line_length = len(line.encode('utf-8')) + 1
                if line_start <= result.position < line_start + line_length:
                    buf.cursor_line = i
                    buf.cursor_column = result.position - line_start
                    break
                line_start += line_length
        else:
            buf.cursor_pos = result.position

        self.window_manager.status_message = (
            f"Match {self.current_result_index + 1} of {len(self.search_results)}"
        )

    def _find_previous(self) -> None:
        """Find the previous search result."""

        if not self.search_results:
            self._start_search()
            return

        if self.current_result_index > 0:
            self.current_result_index -= 1
        else:
            self.current_result_index = len(self.search_results) - 1

        result = self.search_results[self.current_result_index]
        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file:
            line_start = 0
            for i, line in enumerate(buf.code_lines):
                line_length = len(line.encode('utf-8')) + 1
                if line_start <= result.position < line_start + line_length:
                    buf.cursor_line = i
                    buf.cursor_column = result.position - line_start
                    break
                line_start += line_length
        else:
            buf.cursor_pos = result.position

        self.window_manager.status_message = (
            f"Match {self.current_result_index + 1} of {len(self.search_results)}"
        )

    def _start_replace(self) -> None:
        """Start replace mode."""

        if not self.search_results:
            self._start_search()
            return
            
        self.replace_mode = True
        self.replace_query = ""
        self.window_manager.status_message = REPLACE_STATUS_MESSAGE

    def _execute_replace(self) -> None:
        """Execute the replace operation on the current match."""

        if not self.replace_query or not self.search_results or self.current_result_index < 0:
            self.replace_mode = False
            return

        buf = self.window_manager.get_active_buffer()
        if not buf:
            self.replace_mode = False
            return

        result = self.search_results[self.current_result_index]

        self._replace_match(buf, result)

        self._execute_search()
        self.replace_mode = False

        self.window_manager.status_message = ONE_REPLACE_STATUS_MESSAGE

    def _replace_all(self) -> None:
        """Replace all occurrences of the search query."""

        if not self.replace_query or not self.search_results:
            self.replace_mode = False
            return

        buf = self.window_manager.get_active_buffer()
        if not buf:
            self.replace_mode = False
            return

        count = 0

        results_copy = self.search_results.copy()
        results_copy.sort(key=lambda r: r.position, reverse=True)

        batch_action = UndoAction(
            position=0,
            old_data=b'',
            new_data=b'',
            action_type='batch_replace'
        )

        for result in results_copy:
            action = self._prepare_replace_action(buf, result)
            if not action:
                continue

            batch_action.batch_actions.append(action)

            self._perform_replacement(buf, result)
            count += 1

        if count > 0:
            buf.undo_stack.append(batch_action)
            buf.redo_stack.clear()

        self._execute_search()
        self.replace_mode = False

        self.window_manager.status_message = f"Replaced {count} occurrences."

    def _prepare_replace_action(self, buf: Buffer, result: SearchResult) -> Optional[UndoAction]:
        """Prepare a replacement action without performing the replacement."""

        if self.search_type == 'hex':
            try:
                replacement_bytes = bytes.fromhex(''.join(self.replace_query.split()))
            except ValueError:
                return None
        else:
            replacement_bytes = self.replace_query.encode('utf-8')

        if not buf.is_code_file:
            old_data = buf.data[result.position:result.position + result.length]

            return UndoAction(
                position=result.position,
                old_data=bytes(old_data),
                new_data=replacement_bytes,
                action_type='replace_range'
            )

        line_start = 0
        for i, line in enumerate(buf.code_lines):
            line_length = len(line.encode('utf-8')) + 1
            if line_start <= result.position < line_start + line_length:
                old_line = buf.code_lines[i]

                col_start = result.position - line_start
                col_end = col_start + result.length

                new_line = line[:col_start] + self.replace_query + line[col_end:]

                return UndoAction(
                    position=i,
                    old_data=old_line.encode('utf-8'),
                    new_data=new_line.encode('utf-8'),
                    action_type='replace_line'
                )

            line_start += line_length

        return None

    def _perform_replacement(self, buf: Buffer, result: SearchResult) -> None:
        """Perform the actual replacement without creating an undo action."""

        if self.search_type == 'hex':
            try:
                replacement_bytes = bytes.fromhex(''.join(self.replace_query.split()))
            except ValueError:
                self.window_manager.status_message = "Invalid hex format in replacement"
                return
        else:
            replacement_bytes = self.replace_query.encode('utf-8')

        if buf.is_code_file:
            line_start = 0
            for i, line in enumerate(buf.code_lines):
                line_length = len(line.encode('utf-8')) + 1
                if line_start <= result.position < line_start + line_length:
                    col_start = result.position - line_start
                    col_end = col_start + result.length

                    new_line = line[:col_start] + self.replace_query + line[col_end:]
                    buf.code_lines[i] = new_line

                    buf.cursor_line = i
                    buf.cursor_column = col_start + len(self.replace_query)
                    break
                line_start += line_length
        else:
            buf.data[result.position:result.position + result.length] = replacement_bytes
            buf.cursor_pos = result.position + len(replacement_bytes)

        buf.modified = True

    def _replace_match(self, buf: Buffer, result: SearchResult) -> None:
        """Replace a single match in the buffer."""

        if self.search_type == 'hex':
            try:
                replacement_bytes = bytes.fromhex(''.join(self.replace_query.split()))
            except ValueError:
                self.window_manager.status_message = "Invalid hex format in replacement"
                return
        else:
            replacement_bytes = self.replace_query.encode('utf-8')

        if buf.is_code_file:
            line_start = 0
            for i, line in enumerate(buf.code_lines):
                line_length = len(line.encode('utf-8')) + 1
                if line_start <= result.position < line_start + line_length:
                    col_start = result.position - line_start
                    col_end = col_start + result.length

                    old_line = buf.code_lines[i]

                    new_line = line[:col_start] + self.replace_query + line[col_end:]
                    buf.code_lines[i] = new_line

                    action = UndoAction(
                        position=i,
                        old_data=old_line.encode('utf-8'),
                        new_data=new_line.encode('utf-8'),
                        action_type='replace_line'
                    )
                    buf.undo_stack.append(action)
                    buf.redo_stack.clear()

                    buf.cursor_line = i
                    buf.cursor_column = col_start + len(self.replace_query)
                    break
                line_start += line_length
        else:
            old_data = buf.data[result.position:result.position + result.length]

            action = UndoAction(
                position=result.position,
                old_data=bytes(old_data),
                new_data=replacement_bytes,
                action_type='replace_range'
            )
            buf.undo_stack.append(action)
            buf.redo_stack.clear()

            buf.data[result.position:result.position + result.length] = replacement_bytes

            buf.cursor_pos = result.position + len(replacement_bytes)

        buf.modified = True

    def _undo(self) -> None:
        """Undo last action."""

        buf = self.window_manager.get_active_buffer()
        if buf:
            buf.undo()

    def _redo(self) -> None:
        """Redo last undone action."""

        buf = self.window_manager.get_active_buffer()
        if buf:
            buf.redo()

    def _cut_line(self) -> None:
        """Cut current line."""

        buf = self.window_manager.get_active_buffer()
        if not buf:
            return

        if buf.is_code_file and buf.edit_mode:
            buf.delete_line(buf.cursor_line)
            return

        line_start = (buf.cursor_pos // buf.bytes_per_line) * buf.bytes_per_line
        line_end = min(line_start + buf.bytes_per_line, buf.get_size())
        # TODO: Implement clipboard functionality
        for i in range(line_end - 1, line_start - 1, -1):
            buf.delete_byte(i)

    def _paste_line(self) -> None:
        """Paste last cut line."""

        # TODO: Implement clipboard functionality
        pass

    def _execute_open(self) -> None:
        """Execute file open with current query."""

        if not self.open_query:
            self.open_mode = False
            return

        try:
            path = os.path.expanduser(self.open_query)

            active_buffer = self.window_manager.get_active_buffer()
            if active_buffer and not active_buffer.filename:
                if active_buffer.save_file(path):
                    self.window_manager.status_message = f"Saved: {path}"
                    self.open_mode = False
                    self.open_query = ""
                    return

                self.window_manager.status_message = "Error: Could not save file"
                self.open_mode = False
                self.open_query = ""
                return

            if not os.path.exists(path):
                buf = Buffer()
                buf.code_lines = ['']
                buf.filename = path
                buf.is_code_file = True
                buf.edit_mode = True
                
                highlighter = SyntaxHighlighter()
                buf.language = highlighter.detect_language(path, '')
                
                self.window_manager.add_buffer(buf)
                self.window_manager.status_message = f"Created new file: {path}"
                self.open_mode = False
                self.open_query = ""
                return

            buf = Buffer()
            buf.load_file(path)
            self.window_manager.add_buffer(buf)
            self.window_manager.status_message = f"Opened: {path}"
            self.open_mode = False
            self.open_query = ""

        except Exception as e:
            self.window_manager.status_message = f"Error: {str(e)}"
            self.open_query = f"Error: {str(e)}"

    def _start_open(self) -> None:
        """Start open file mode."""

        self.open_mode = True
        self.open_query = ""
        self.window_manager.status_message = OPEN_MODE_STATUS_MESSAGE
