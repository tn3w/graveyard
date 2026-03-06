"""
Window management module for the hex editor UI.
"""

import curses
import os
import time
from typing import List, Optional, TYPE_CHECKING
from ..core.buffer import Buffer
from ..core.syntax import SyntaxHighlighter

if TYPE_CHECKING:
    from .input_handler import InputHandler


def safe_addstr(window: 'curses.window', y: int, x: int, string: str, attr: int = 0) -> None:
    """Safely add a string to a window, truncating if necessary."""

    height, width = window.getmaxyx()
    if y >= height or x >= width:
        return

    available = width - x
    if available <= 0:
        return

    if len(string) > available:
        string = string[:available]
    
    try:
        window.addstr(y, x, string, attr)
    except curses.error:
        pass


class WindowManager:
    """Manages the curses windows and UI layout."""

    SUMMARY_WIDTH = 12
    STATUS_MESSAGE_DURATION = 3
    LINE_NUMBER_WIDTH = 6
    SEARCH_HIGHLIGHT_COLOR = 8

    def __init__(self, stdscr: 'curses.window'):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

        if self.height < 10 or self.width < 40:
            raise ValueError(f"Terminal too small. Minimum size: 40x10, Current size: {self.width}x{self.height}")

        self.buffers: List[Buffer] = []
        self.active_buffer_index = 0
        self.status_window: Optional['curses.window'] = None
        self.hex_window: Optional['curses.window'] = None
        self.ascii_window: Optional['curses.window'] = None
        self.code_window: Optional['curses.window'] = None
        self.line_numbers_window: Optional['curses.window'] = None
        self.summary_window: Optional['curses.window'] = None
        self.tab_window: Optional['curses.window'] = None
        self.dialog_window: Optional['curses.window'] = None
        self.input_handler: Optional['InputHandler'] = None
        self.status_message: Optional[str] = None
        self.status_message_time = 0
        
        self.syntax_highlighter = SyntaxHighlighter()
        self.syntax_highlighter.init_colors()

        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, -1)  # Status bar (was blue background)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # Highlights
        curses.init_pair(3, curses.COLOR_GREEN, -1)  # ASCII
        curses.init_pair(4, curses.COLOR_GREEN, -1)  # Summary top
        curses.init_pair(5, curses.COLOR_WHITE, -1)  # Summary bottom
        curses.init_pair(6, curses.COLOR_WHITE, -1)  # Dialog (was blue background)
        curses.init_pair(7, curses.COLOR_RED, -1)   # Error messages
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Search highlights
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)   # Current search match
        curses.init_pair(10, 8, -1)  # Line numbers (gray, default background)

        self.setup_windows()

    def setup_windows(self) -> None:
        """Create and position all windows."""

        if self.height < 10 or self.width < 40:
            return

        self.tab_window = curses.newwin(2, self.width, 0, 0)

        content_width = self.width - self.SUMMARY_WIDTH
        hex_width = max((content_width * 2) // 3, content_width // 2)
        ascii_width = content_width - hex_width

        self.summary_window = curses.newwin(
            self.height - 3,
            self.SUMMARY_WIDTH,
            2,
            0
        )

        self.hex_window = curses.newwin(
            self.height - 3,
            hex_width,
            2,
            self.SUMMARY_WIDTH
        )

        self.ascii_window = curses.newwin(
            self.height - 3,
            ascii_width,
            2,
            self.SUMMARY_WIDTH + hex_width
        )

        self.line_numbers_window = curses.newwin(
            self.height - 3,
            self.LINE_NUMBER_WIDTH,
            2,
            0
        )

        self.code_window = curses.newwin(
            self.height - 3,
            self.width - self.LINE_NUMBER_WIDTH,
            2,
            self.LINE_NUMBER_WIDTH
        )

        self.status_window = curses.newwin(1, self.width, self.height - 1, 0)

        if self.buffers:
            self.buffers[self.active_buffer_index].set_bytes_per_line(hex_width)

    def refresh_all(self) -> None:
        """Refresh all windows."""

        self.draw_tabs()

        if self.input_handler and self.input_handler.open_mode:
            self.draw_open_dialog()
        elif self.input_handler and self.input_handler.search_mode:
            self.draw_search_dialog()
        elif self.input_handler and self.input_handler.replace_mode:
            self.draw_replace_dialog()
        else:
            if self.buffers:
                buf = self.buffers[self.active_buffer_index]

                if buf.is_code_file:
                    self.draw_line_numbers()
                    self.draw_code_view()
                else:
                    self.draw_summary()
                    self.draw_hex_view()
                    self.draw_ascii_view()

        self.draw_status()
        curses.doupdate()

    def draw_tabs(self) -> None:
        """Draw the tab bar with open files."""

        if not self.tab_window:
            return

        self.tab_window.clear()
        tab_bar = ""
        for i, buf in enumerate(self.buffers):
            name = os.path.basename(buf.filename) if buf.filename else f"[New File {i+1}]"
            if i == self.active_buffer_index:
                tab_bar += f"[{i+1}:{name}] "
                continue

            tab_bar += f" {i+1}:{name} "

        safe_addstr(self.tab_window, 0, 0, tab_bar)

        self.tab_window.hline(1, 0, curses.ACS_HLINE, self.width)
        self.tab_window.noutrefresh()

    def draw_summary(self) -> None:
        """Draw the summary panel."""

        if not self.summary_window or not self.buffers:
            return
            
        buf = self.buffers[self.active_buffer_index]
        self.summary_window.clear()

        if buf.is_code_file:
            line = f"{buf.cursor_line + 1:08d}"
            col = f"{buf.cursor_column + 1:08d}"
            offset = f"{0:08X}"
        else:
            offset = f"{buf.cursor_pos:08X}"
            line = f"{buf.get_cursor_line() + 1:08d}"
            col = f"{buf.get_cursor_column() + 1:08d}"

        self.summary_window.attron(curses.color_pair(4))
        summary_top = [
            "Summary",
            "--------",
            offset,
        ]
        
        for i, line_text in enumerate(summary_top):
            safe_addstr(self.summary_window, i, 0, line_text[:8])
        self.summary_window.attroff(curses.color_pair(4))

        self.summary_window.attron(curses.color_pair(5))
        summary_bottom = [
            line,
            col,
            "--------",
            "Mod:" + ("Y" if buf.modified else "N")
        ]

        if buf.is_code_file:
            summary_bottom.append(f"Lang:{buf.language or 'txt'}")
            summary_bottom.append("Mode:" + ("Edit" if buf.edit_mode else "View"))

        for i, line_text in enumerate(summary_bottom):
            safe_addstr(self.summary_window, i + len(summary_top), 0, line_text[:8])

        self.summary_window.attroff(curses.color_pair(5))
        self.summary_window.noutrefresh()

    def draw_hex_view(self) -> None:
        """Draw the hex editor view."""

        if not self.hex_window or not self.buffers:
            return

        buf = self.buffers[self.active_buffer_index]
        self.hex_window.clear()

        visible_lines = self.height - 3
        cursor_line = buf.get_cursor_line()
        start_line = max(0, cursor_line - (visible_lines // 2))

        search_results = []
        current_result_index = -1
        if self.input_handler:
            search_results = self.input_handler.search_results
            current_result_index = self.input_handler.current_result_index

        for i in range(visible_lines):
            line_num = start_line + i
            if line_num * buf.bytes_per_line >= buf.get_size():
                break

            hex_data, _ = buf.get_line(line_num)
            offset = f"{line_num * buf.bytes_per_line:08X}"

            safe_addstr(self.hex_window, i, 0, offset)
            safe_addstr(self.hex_window, i, 8, "  ")

            for j, byte in enumerate(hex_data):
                pos = 10 + j * 3
                if pos + 2 >= self.width:
                    break

                abs_pos = line_num * buf.bytes_per_line + j

                attr = curses.A_NORMAL

                in_search_result = False
                is_current_match = False
                for idx, result in enumerate(search_results):
                    if result.position <= abs_pos < result.position + result.length:
                        in_search_result = True
                        if idx == current_result_index:
                            is_current_match = True
                        break

                if abs_pos == buf.cursor_pos:
                    attr = curses.A_REVERSE | curses.A_BOLD
                elif is_current_match:
                    attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR + 1)
                elif in_search_result:
                    attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR)

                safe_addstr(self.hex_window, i, pos, f"{byte:02X}", attr)

        self.hex_window.noutrefresh()

    def draw_ascii_view(self) -> None:
        """Draw the ASCII representation view."""

        if not self.ascii_window or not self.buffers:
            return

        buf = self.buffers[self.active_buffer_index]
        self.ascii_window.clear()

        visible_lines = self.height - 3
        cursor_line = buf.get_cursor_line()
        start_line = max(0, cursor_line - (visible_lines // 2))

        search_results = []
        current_result_index = -1
        if self.input_handler:
            search_results = self.input_handler.search_results
            current_result_index = self.input_handler.current_result_index

        for i in range(visible_lines):
            line_num = start_line + i
            if line_num * buf.bytes_per_line >= buf.get_size():
                break

            _, ascii_str = buf.get_line(line_num)

            for j, char in enumerate(ascii_str):
                if j >= self.width:
                    break

                abs_pos = line_num * buf.bytes_per_line + j

                attr = curses.color_pair(3)

                in_search_result = False
                is_current_match = False
                for idx, result in enumerate(search_results):
                    if result.position <= abs_pos < result.position + result.length:
                        in_search_result = True
                        if idx == current_result_index:
                            is_current_match = True
                        break

                if abs_pos == buf.cursor_pos:
                    attr = curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD
                elif is_current_match:
                    attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR + 1)
                elif in_search_result:
                    attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR)

                try:
                    self.ascii_window.addch(i, j, ord(char), attr)
                except curses.error:
                    pass

        self.ascii_window.noutrefresh()

    def draw_line_numbers(self) -> None:
        """Draw line numbers for code view."""

        if not self.line_numbers_window or not self.buffers:
            return

        buf = self.buffers[self.active_buffer_index]
        if not buf.is_code_file:
            return

        self.line_numbers_window.clear()

        visible_lines = self.height - 3
        cursor_line = buf.cursor_line
        start_line = max(0, cursor_line - (visible_lines // 2))

        for i in range(visible_lines):
            line_num = start_line + i
            if line_num >= buf.get_line_count():
                break

            line_str = f"{line_num + 1:4d} "
            attr = curses.color_pair(10)
            if line_num == cursor_line:
                attr |= curses.A_BOLD

            safe_addstr(self.line_numbers_window, i, 0, line_str, attr)

        self.line_numbers_window.noutrefresh()

    def draw_code_view(self) -> None:
        """Draw the code editor view with syntax highlighting."""

        if not self.code_window or not self.buffers:
            return

        buf = self.buffers[self.active_buffer_index]
        if not buf.is_code_file:
            return

        self.code_window.clear()

        visible_lines = self.height - 3
        cursor_line = buf.cursor_line
        start_line = max(0, cursor_line - (visible_lines // 2))

        if buf.language and buf.filename and not self.syntax_highlighter.lexer:
            self.syntax_highlighter.detect_language(buf.filename, ''.join(buf.code_lines[:100]))

        self.code_window.bkgd(' ', curses.A_NORMAL)

        search_results = []
        current_result_index = -1
        if self.input_handler:
            search_results = self.input_handler.search_results
            current_result_index = self.input_handler.current_result_index

        if len(buf.code_lines) == 0:
            try:
                self.code_window.addch(0, 0, ord(' '), curses.A_REVERSE)
            except curses.error:
                pass

            self.code_window.noutrefresh()
            return

        line_byte_positions = []
        byte_pos = 0
        for line in buf.code_lines:
            line_byte_positions.append(byte_pos)
            byte_pos += len(line.encode('utf-8')) + 1

        for i in range(visible_lines):
            line_num = start_line + i
            if line_num >= buf.get_line_count():
                break

            line = buf.get_code_line(line_num)

            is_cursor_line = (line_num == cursor_line)
            if self.syntax_highlighter.lexer:
                if is_cursor_line and len(line) == 0:
                    try:
                        self.code_window.addch(i, 0, ord(' '), curses.A_REVERSE)
                    except curses.error:
                        pass
                    continue

                highlighted = self.syntax_highlighter.highlight_line(line)

                x_pos = 0
                for text, color in highlighted:
                    attr = color
                    if is_cursor_line:
                        attr |= curses.A_BOLD

                    attr = attr & ~curses.A_COLOR
                    attr |= (color & curses.A_COLOR)

                    line_start_byte = line_byte_positions[line_num]

                    for char_idx, char in enumerate(text):
                        char_x = x_pos + char_idx
                        char_byte_pos = line_start_byte + char_x

                        char_attr = attr
                        in_search_result = False
                        is_current_match = False

                        for idx, result in enumerate(search_results):
                            if result.position <= char_byte_pos < result.position + result.length:
                                in_search_result = True
                                if idx == current_result_index:
                                    is_current_match = True
                                break

                        if is_current_match:
                            char_attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR + 1)
                        elif in_search_result:
                            char_attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR)

                        if is_cursor_line and char_x == buf.cursor_column:
                            char_attr = curses.A_REVERSE

                        try:
                            self.code_window.addch(i, char_x, ord(char), char_attr)
                        except curses.error:
                            pass

                    x_pos += len(text)

                if is_cursor_line and buf.cursor_column >= x_pos:
                    try:
                        self.code_window.addch(i, buf.cursor_column, ord(' '), curses.A_REVERSE)
                    except curses.error:
                        pass
            else:
                attr = curses.A_NORMAL
                if is_cursor_line:
                    attr |= curses.A_BOLD

                line_start_byte = line_byte_positions[line_num]

                for char_idx, char in enumerate(line):
                    char_byte_pos = line_start_byte + char_idx

                    char_attr = attr
                    in_search_result = False
                    is_current_match = False

                    for idx, result in enumerate(search_results):
                        if result.position <= char_byte_pos < result.position + result.length:
                            in_search_result = True
                            if idx == current_result_index:
                                is_current_match = True
                            break

                    if is_current_match:
                        char_attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR + 1)
                    elif in_search_result:
                        char_attr = curses.color_pair(self.SEARCH_HIGHLIGHT_COLOR)

                    if is_cursor_line and char_idx == buf.cursor_column:
                        char_attr = curses.A_REVERSE

                    try:
                        self.code_window.addch(i, char_idx, ord(char), char_attr)
                    except curses.error:
                        pass

                if is_cursor_line:
                    cursor_x = min(buf.cursor_column, len(line))
                    try:
                        if cursor_x >= len(line) or len(line) == 0:
                            self.code_window.addch(i, cursor_x, ord(' '), curses.A_REVERSE)
                    except curses.error:
                        pass

        self.code_window.noutrefresh()

    def draw_open_dialog(self) -> None:
        """Draw the open file dialog."""

        if not self.dialog_window:
            dialog_height = 6
            dialog_width = min(80, self.width - 4)
            dialog_y = (self.height - dialog_height) // 2
            dialog_x = (self.width - dialog_width) // 2
            self.dialog_window = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        else:
            _, dialog_width = self.dialog_window.getmaxyx()

        self.dialog_window.clear()
        self.dialog_window.attron(curses.color_pair(6) | curses.A_BOLD)
        self.dialog_window.box()

        title = " Open File "
        title_x = (self.dialog_window.getmaxyx()[1] - len(title)) // 2
        safe_addstr(self.dialog_window, 0, title_x, title)

        prompt = "Enter file path:"
        safe_addstr(self.dialog_window, 2, 2, prompt)

        input_x = len(prompt) + 3
        query = "" if self.input_handler is None else self.input_handler.open_query
        safe_addstr(self.dialog_window, 2, input_x, query + " ")

        if len(query) < self.dialog_window.getmaxyx()[1] - input_x - 3:
            self.dialog_window.attron(curses.A_REVERSE)
            safe_addstr(self.dialog_window, 2, input_x + len(query), " ")
            self.dialog_window.attroff(curses.A_REVERSE)

        safe_addstr(self.dialog_window, 4, 2, "Enter: Open/Save file")
        safe_addstr(self.dialog_window, 4, dialog_width // 2, "Esc: Cancel")

        self.dialog_window.attroff(curses.color_pair(6) | curses.A_BOLD)
        self.dialog_window.noutrefresh()

    def draw_search_dialog(self) -> None:
        """Draw the search dialog."""

        if not self.dialog_window:
            dialog_height = 9
            dialog_width = min(80, self.width - 4)
            dialog_y = (self.height - dialog_height) // 2
            dialog_x = (self.width - dialog_width) // 2
            self.dialog_window = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        else:
            _, dialog_width = self.dialog_window.getmaxyx()

        self.dialog_window.clear()
        self.dialog_window.attron(curses.color_pair(6) | curses.A_BOLD)
        self.dialog_window.box()

        title = " Search "
        title_x = (self.dialog_window.getmaxyx()[1] - len(title)) // 2
        safe_addstr(self.dialog_window, 0, title_x, title)

        prompt = "Find:"
        safe_addstr(self.dialog_window, 2, 2, prompt)

        input_x = len(prompt) + 3
        query = "" if self.input_handler is None else self.input_handler.search_query
        safe_addstr(self.dialog_window, 2, input_x, query + " ")

        if len(query) < self.dialog_window.getmaxyx()[1] - input_x - 3:
            self.dialog_window.attron(curses.A_REVERSE)
            safe_addstr(self.dialog_window, 2, input_x + len(query), " ")
            self.dialog_window.attroff(curses.A_REVERSE)

        search_type = "text" if self.input_handler is None else self.input_handler.search_type
        case_sensitive = False if self.input_handler is None else self.input_handler.case_sensitive
        options_text = f"Type: {search_type.capitalize()}  "
        options_text += f"Case Sensitive: {'Yes' if case_sensitive else 'No'}"
        safe_addstr(self.dialog_window, 4, 2, options_text)

        if search_type == "wildcard":
            help_text = "Wildcard: ? = one character, * = any number of characters"
            safe_addstr(self.dialog_window, 5, 2, help_text)
        elif search_type == "hex":
            help_text = "Hex: Enter space-separated hex values (e.g. 'FF 00 A3')"
            safe_addstr(self.dialog_window, 5, 2, help_text)
        elif search_type == "regex":
            help_text = "Regex: Enter a regular expression pattern"
            safe_addstr(self.dialog_window, 5, 2, help_text)

        safe_addstr(self.dialog_window, 6, 2, "Tab: Change search type")
        safe_addstr(self.dialog_window, 7, 2, "Alt+C: Toggle case sensitivity")
        safe_addstr(self.dialog_window, 6, dialog_width // 2, "Enter: Search")
        safe_addstr(self.dialog_window, 7, dialog_width // 2, "Esc: Cancel")

        self.dialog_window.attroff(curses.color_pair(6) | curses.A_BOLD)
        self.dialog_window.noutrefresh()

    def draw_replace_dialog(self) -> None:
        """Draw the replace dialog."""

        if not self.dialog_window:
            dialog_height = 7
            dialog_width = min(80, self.width - 4)
            dialog_y = (self.height - dialog_height) // 2
            dialog_x = (self.width - dialog_width) // 2
            self.dialog_window = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        else:
            _, dialog_width = self.dialog_window.getmaxyx()

        self.dialog_window.clear()
        self.dialog_window.attron(curses.color_pair(6) | curses.A_BOLD)
        self.dialog_window.box()

        title = " Replace "
        title_x = (self.dialog_window.getmaxyx()[1] - len(title)) // 2
        safe_addstr(self.dialog_window, 0, title_x, title)

        prompt = "Replace with:"
        safe_addstr(self.dialog_window, 2, 2, prompt)

        input_x = len(prompt) + 3
        query = "" if self.input_handler is None else self.input_handler.replace_query
        safe_addstr(self.dialog_window, 2, input_x, query + " ")

        if len(query) < self.dialog_window.getmaxyx()[1] - input_x - 3:
            self.dialog_window.attron(curses.A_REVERSE)
            safe_addstr(self.dialog_window, 2, input_x + len(query), " ")
            self.dialog_window.attroff(curses.A_REVERSE)

        safe_addstr(self.dialog_window, 4, 2, "Enter: Replace current match")
        safe_addstr(self.dialog_window, 5, 2, "Ctrl+A: Replace all matches")
        safe_addstr(self.dialog_window, 4, dialog_width // 2, "Esc: Cancel")

        self.dialog_window.attroff(curses.color_pair(6) | curses.A_BOLD)
        self.dialog_window.noutrefresh()

    def draw_status(self) -> None:
        """Draw the status bar."""

        if not self.status_window:
            return

        self.status_window.clear()
        self.status_window.attron(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)

        if self.input_handler and self.input_handler.open_mode:
            if not self.input_handler.open_query.startswith("Error:"):
                status = " Press Enter to open file, Esc to cancel "
            else:
                status = self.input_handler.open_query

            safe_addstr(self.status_window, 0, 0, status)
            self.status_window.attroff(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
            self.status_window.noutrefresh()
            return

        if not self.buffers:
            safe_addstr(self.status_window, 0, 0, " No file opened - Press Ctrl+O to open a file")
            self.status_window.attroff(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
            self.status_window.noutrefresh()
            return

        buf = self.buffers[self.active_buffer_index]

        if self.status_message:
            if self.status_message_time == 0:
                self.status_message_time = time.time()
            elif time.time() - self.status_message_time > self.STATUS_MESSAGE_DURATION:
                self.status_message = None
                self.status_message_time = 0
            else:
                if self.status_message.startswith("Error:"):
                    self.status_window.attron(curses.color_pair(7) | curses.A_BOLD)
                safe_addstr(self.status_window, 0, 0, " " + self.status_message)
                if self.status_message.startswith("Error:"):
                    self.status_window.attroff(curses.color_pair(7) | curses.A_BOLD)
                self.status_window.attroff(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
                self.status_window.noutrefresh()
                return

        name = os.path.basename(buf.filename) if buf.filename else '[No Name]'
        status = f" {name} "

        if buf.is_code_file:
            status += f"[{buf.language or 'text'}] "
            status += f"[{len(buf.code_lines)} lines] "

            if buf.edit_mode:
                status += "[Edit] "
            else:
                status += "[View] "

            if buf.modified:
                status += "[Modified] "

        else:
            status += f"[{buf.get_size()} bytes] "

            if buf.modified:
                status += "[Modified] "

            if self.input_handler:
                if self.input_handler.insert_mode:
                    if self.input_handler.current_hex_digit is not None:
                        status += "[Insert:2nd] "
                    else:
                        status += "[Insert:1st] "
                else:
                    status += "[View] "

        if buf.is_code_file:
            pos_info = f"Line: {buf.cursor_line + 1} "
            pos_info += f"Col: {buf.cursor_column + 1}"
        else:
            pos_info = f"Offset: 0x{buf.cursor_pos:08X} "
            pos_info += f"Line: {buf.get_cursor_line() + 1} "
            pos_info += f"Col: {buf.get_cursor_column() + 1}"

        available_width = self.width - len(pos_info) - 1
        if len(status) > available_width:
            status = status[:available_width-3] + "... "
        else:
            status += " " * (available_width - len(status))

        safe_addstr(self.status_window, 0, 0, status + pos_info)
        self.status_window.attroff(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
        self.status_window.noutrefresh()

    def add_buffer(self, buf: Buffer) -> None:
        """Add a new buffer to the editor."""

        self.buffers.append(buf)
        self.active_buffer_index = len(self.buffers) - 1

        if self.hex_window:
            buf.set_bytes_per_line(self.hex_window.getmaxyx()[1])

    def switch_buffer(self, index: int) -> bool:
        """Switch to the buffer at the given index."""

        if index < 0 or index >= len(self.buffers):
            return False

        self.active_buffer_index = index
        buf = self.buffers[index]
        name = os.path.basename(buf.filename) if buf.filename else '[No Name]'
        self.status_message = f"Switched to: {name}"
        return True

    def get_active_buffer(self) -> Optional[Buffer]:
        """Get the currently active buffer."""

        if not self.buffers or self.active_buffer_index < 0 or self.active_buffer_index >= len(self.buffers):
            return None

        return self.buffers[self.active_buffer_index]

    def resize(self) -> None:
        """Handle terminal resize events."""

        self.height, self.width = self.stdscr.getmaxyx()

        if self.height < 10 or self.width < 40:
            self.status_message = "Error: Terminal too small"
            return

        self.dialog_window = None

        self.setup_windows()
        if self.hex_window and self.buffers:
            hex_width = self.hex_window.getmaxyx()[1]
            for buf in self.buffers:
                buf.set_bytes_per_line(hex_width)
