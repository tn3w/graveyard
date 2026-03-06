"""
Buffer module for handling code editing and hex data manipulation.
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from collections import deque
import os
import mmap
from ..core.syntax import SyntaxHighlighter


@dataclass
class UndoAction:
    """Represents an undoable action in the buffer."""
    position: int
    old_data: bytes
    new_data: bytes
    action_type: str
    batch_actions: List['UndoAction'] = field(default_factory=list)


class Buffer:
    """Main buffer class for handling hex data."""

    CHUNK_SIZE = 1024 * 1024

    def __init__(self, initial_data: bytes = b'') -> None:
        self.data = bytearray(initial_data)
        self.modified = False
        self.filename: Optional[str] = None
        self.cursor_pos = 0
        self.undo_stack: deque[UndoAction] = deque(maxlen=100)
        self.redo_stack: deque[UndoAction] = deque(maxlen=100)
        self.selection_start: Optional[int] = None
        self.selection_end: Optional[int] = None
        self.bytes_per_line = 16

        self.is_code_file = False
        self.language = None
        self.code_lines: List[str] = []
        self.line_count = 0
        self.top_line = 0
        self.cursor_line = 0
        self.cursor_column = 0
        self.edit_mode = False

        self.file_size = 0
        self.file_map = None
        self.is_large_file = False
        self.loaded_chunks: Dict[int, bytearray] = {}

    def get_line(self, line_number: int) -> Tuple[bytes, str]:
        """Get a line of hex data and its ASCII representation."""

        if self.is_large_file:
            chunk_index = (line_number * self.bytes_per_line) // self.CHUNK_SIZE
            chunk_offset = (line_number * self.bytes_per_line) % self.CHUNK_SIZE

            if chunk_index not in self.loaded_chunks:
                self._load_chunk(chunk_index)

            chunk_data = self.loaded_chunks[chunk_index]
            start = chunk_offset
            end = min(start + self.bytes_per_line, len(chunk_data))
            hex_data = chunk_data[start:end]
        else:
            start = line_number * self.bytes_per_line
            end = min(start + self.bytes_per_line, len(self.data))
            hex_data = self.data[start:end]

        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in hex_data)

        return hex_data, ascii_str

    def _load_chunk(self, chunk_index: int) -> None:
        """Load a chunk of data from a large file."""

        if not self.file_map:
            return

        start_pos = chunk_index * self.CHUNK_SIZE
        end_pos = min(start_pos + self.CHUNK_SIZE, self.file_size)

        if start_pos >= self.file_size:
            self.loaded_chunks[chunk_index] = bytearray()
            return

        self.loaded_chunks[chunk_index] = bytearray(self.file_map[start_pos:end_pos])

        if len(self.loaded_chunks) > 5:
            oldest_chunk = min(self.loaded_chunks.keys())
            if oldest_chunk != chunk_index:
                del self.loaded_chunks[oldest_chunk]

    def get_code_line(self, line_number: int) -> str:
        """Get a line of code text."""

        if not self.is_code_file or line_number >= len(self.code_lines):
            return ""

        return self.code_lines[line_number]

    def set_bytes_per_line(self, width: int) -> None:
        """Calculate and set the number of bytes per line based on window width."""

        hex_width = width - 10
        max_bytes = (hex_width - 2) // 3

        self.bytes_per_line = max(8, (max_bytes // 8) * 8)

    def get_line_count(self) -> int:
        """Get the total number of lines based on current bytes_per_line."""

        if self.is_code_file:
            return len(self.code_lines)
        elif self.is_large_file:
            return (self.file_size + self.bytes_per_line - 1) // self.bytes_per_line

        return (len(self.data) + self.bytes_per_line - 1) // self.bytes_per_line

    def get_cursor_line(self) -> int:
        """Get the line number where the cursor is."""

        if self.is_code_file:
            return self.cursor_line

        return self.cursor_pos // self.bytes_per_line

    def get_cursor_column(self) -> int:
        """Get the column number where the cursor is."""

        if self.is_code_file:
            return self.cursor_column

        return self.cursor_pos % self.bytes_per_line

    def insert_byte(self, position: int, value: int) -> None:
        """Insert a byte at the specified position."""

        if not 0 <= value <= 255:
            raise ValueError("Byte value must be between 0 and 255")
            
        position = max(0, min(position, len(self.data)))
            
        action = UndoAction(position, b'', bytes([value]), 'insert')
        self.undo_stack.append(action)
        self.redo_stack.clear()
        
        self.data.insert(position, value)
        self.modified = True

    def delete_byte(self, position: int) -> None:
        """Delete a byte at the specified position."""

        if not 0 <= position < len(self.data):
            return

        old_value = self.data[position]
        action = UndoAction(position, bytes([old_value]), b'', 'delete')
        self.undo_stack.append(action)
        self.redo_stack.clear()
            
        del self.data[position]
        self.modified = True
        
        if self.cursor_pos >= len(self.data):
            self.cursor_pos = max(0, len(self.data) - 1)

    def replace_byte(self, position: int, value: int) -> None:
        """Replace a byte at the specified position."""

        if not 0 <= value <= 255:
            raise ValueError("Byte value must be between 0 and 255")

        if not 0 <= position < len(self.data):
            return

        old_value = self.data[position]

        if old_value == value:
            return

        action = UndoAction(position, bytes([old_value]), bytes([value]), 'replace')
        self.undo_stack.append(action)
        self.redo_stack.clear()

        self.data[position] = value
        self.modified = True

    def insert_text(self, line: int, column: int, text: str) -> None:
        """Insert text at the specified position in code view."""

        if not self.is_code_file or line >= len(self.code_lines):
            return

        current_line = self.code_lines[line]
        column = min(column, len(current_line))

        new_line = current_line[:column] + text + current_line[column:]
        self.code_lines[line] = new_line

        self.cursor_column = column + len(text)

        self.modified = True

        self.redo_stack.clear()
        # TODO: Implement proper undo/redo for text operations

    def delete_text(self, line: int, start_col: int, end_col: int) -> None:
        """Delete text in the specified range in code view."""

        if not self.is_code_file or line >= len(self.code_lines):
            return

        current_line = self.code_lines[line]
        start_col = min(start_col, len(current_line))
        end_col = min(end_col, len(current_line))

        new_line = current_line[:start_col] + current_line[end_col:]
        self.code_lines[line] = new_line

        self.cursor_column = start_col

        self.modified = True

        self.redo_stack.clear()
        # TODO: Implement proper undo/redo for text operations

    def insert_line(self, line: int, text: str = "") -> None:
        """Insert a new line at the specified position in code view."""

        if not self.is_code_file:
            return

        line = min(line, len(self.code_lines))

        self.code_lines.insert(line, text)
        
        if self.cursor_line >= line:
            self.cursor_line += 1

        self.modified = True
        self.redo_stack.clear()

    def delete_line(self, line: int) -> None:
        """Delete a line in code view."""

        if not self.is_code_file or line >= len(self.code_lines):
            return

        del self.code_lines[line]

        if self.cursor_line > line:
            self.cursor_line -= 1
        elif self.cursor_line >= len(self.code_lines):
            self.cursor_line = max(0, len(self.code_lines) - 1)

        self.modified = True
        self.redo_stack.clear()

    def undo(self) -> bool:
        """Undo the last action."""

        if not self.undo_stack:
            return False

        action = self.undo_stack.pop()
        self.redo_stack.append(action)

        if action.action_type == 'batch_replace':
            for batch_action in reversed(action.batch_actions):
                if batch_action.action_type == 'replace_range':
                    start = batch_action.position
                    end = start + len(batch_action.new_data)
                    self.data[start:end] = batch_action.old_data

                elif batch_action.action_type == 'replace_line' and self.is_code_file:
                    line_num = batch_action.position
                    if 0 <= line_num < len(self.code_lines):
                        self.code_lines[line_num] = batch_action.old_data.decode('utf-8', errors='replace')

        elif action.action_type == 'insert':
            del self.data[action.position]

        elif action.action_type == 'delete':
            self.data.insert(action.position, action.old_data[0])

        elif action.action_type == 'replace':
            self.data[action.position] = action.old_data[0]

        elif action.action_type == 'replace_range':
            start = action.position
            end = start + len(action.new_data)
            self.data[start:end] = action.old_data
            self.cursor_pos = start

        elif action.action_type == 'replace_line' and self.is_code_file:
            line_num = action.position
            if 0 <= line_num < len(self.code_lines):
                self.code_lines[line_num] = action.old_data.decode('utf-8', errors='replace')
                self.cursor_line = line_num
                self.cursor_column = 0

        self.modified = bool(self.undo_stack)

        if not self.is_code_file and self.cursor_pos >= len(self.data):
            self.cursor_pos = max(0, len(self.data) - 1)

        return True

    def redo(self) -> bool:
        """Redo the last undone action."""
        if not self.redo_stack:
            return False

        action = self.redo_stack.pop()
        self.undo_stack.append(action)

        if action.action_type == 'batch_replace':
            for batch_action in action.batch_actions:
                if batch_action.action_type == 'replace_range':
                    start = batch_action.position
                    end = start + len(batch_action.old_data)
                    self.data[start:end] = batch_action.new_data
                elif batch_action.action_type == 'replace_line' and self.is_code_file:
                    line_num = batch_action.position
                    if 0 <= line_num < len(self.code_lines):
                        self.code_lines[line_num] = batch_action.new_data.decode('utf-8', errors='replace')

        elif action.action_type == 'insert':
            self.data.insert(action.position, action.new_data[0])

        elif action.action_type == 'delete':
            del self.data[action.position]

        elif action.action_type == 'replace':
            self.data[action.position] = action.new_data[0]

        elif action.action_type == 'replace_range':
            start = action.position
            end = start + len(action.old_data)
            self.data[start:end] = action.new_data
            self.cursor_pos = start + len(action.new_data)

        elif action.action_type == 'replace_line' and self.is_code_file:
            line_num = action.position
            if 0 <= line_num < len(self.code_lines):
                self.code_lines[line_num] = action.new_data.decode('utf-8', errors='replace')
                self.cursor_line = line_num
                self.cursor_column = 0

        self.modified = True

        if not self.is_code_file and self.cursor_pos >= len(self.data):
            self.cursor_pos = max(0, len(self.data) - 1)

        return True

    def get_selection(self) -> Optional[Tuple[int, int]]:
        """Get the current selection range."""

        if self.selection_start is None or self.selection_end is None:
            return None

        return (min(self.selection_start, self.selection_end),
                max(self.selection_start, self.selection_end))

    def get_size(self) -> int:
        """Get the size of the buffer in bytes."""

        if self.is_large_file:
            return self.file_size

        return len(self.data)

    def _is_binary_file(self, sample: bytes) -> bool:
        """Check if a file is binary based on a sample of its content."""

        null_count = sample.count(0)
        printable_count = sum(32 <= b <= 126 or b in (9, 10, 13) for b in sample)

        return (null_count > len(sample) * 0.1) or (printable_count < len(sample) * 0.8)

    def load_file(self, filename: str) -> None:
        """Load data from a file."""

        self.filename = filename
        self.modified = False
        self.cursor_pos = 0
        self.undo_stack.clear()
        self.redo_stack.clear()

        file_size = os.path.getsize(filename)
        self.file_size = file_size

        if file_size > 10 * 1024 * 1024:
            self.is_large_file = True
            self._load_large_file(filename)
            return

        self.is_large_file = False
        with open(filename, 'rb') as f:
            self.data = bytearray(f.read())

        sample = bytes(self.data[:min(4096, len(self.data))])
        self._detect_file_type(sample)

    def _load_large_file(self, filename: str) -> None:
        """Load a large file using memory mapping."""

        self.file = open(filename, 'rb')
        self.file_map = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        self._load_chunk(0)

        sample = bytes(self.loaded_chunks[0][:min(4096, len(self.loaded_chunks[0]))])
        self._detect_file_type(sample)

    def _detect_file_type(self, sample: bytes) -> None:
        """Detect file type and set up appropriate mode."""

        self.is_code_file = False
        self.language = None
        self.code_lines = []

        if self._is_binary_file(sample):
            return
        
        if not self.filename:
            return

        try:
            text_sample = sample.decode('utf-8', errors='replace')
            
            highlighter = SyntaxHighlighter()
            self.language = highlighter.detect_language(self.filename, text_sample)

            if not self.language:
                return

            self.is_code_file = True
            self.edit_mode = True

            if self.is_large_file:
                self._load_text_chunk(0)
                return 

            text_content = self.data.decode('utf-8', errors='replace')
            self.code_lines = text_content.splitlines()

        except Exception:
            self.is_code_file = False
            self.language = None
            self.code_lines = []
            
    def _load_text_chunk(self, chunk_index: int) -> None:
        """Load a chunk of text for code view."""

        if not self.file_map:
            return

        start_pos = chunk_index * self.CHUNK_SIZE
        end_pos = min(start_pos + self.CHUNK_SIZE, self.file_size)

        if start_pos >= self.file_size:
            return

        chunk_data = self.file_map[start_pos:end_pos]
        text_chunk = chunk_data.decode('utf-8', errors='replace')

        lines = text_chunk.splitlines()

        if chunk_index == 0:
            self.code_lines = lines
            return

        self.code_lines.extend(lines)

    def save_file(self, filename: Optional[str] = None) -> bool:
        """
        Save data to a file.
        
        Args:
            filename: Optional filename to save to. If None, uses current filename.
            
        Returns:
            bool: True if save was successful, False otherwise
        """

        save_filename = filename or self.filename
        if not save_filename:
            return False

        try:
            if self.is_code_file:
                with open(save_filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(self.code_lines))
            else:
                with open(save_filename, 'wb') as f:
                    if self.is_large_file and self.file_map:
                        self.file_map.seek(0)
                        f.write(self.file_map)
                    else:
                        f.write(bytes(self.data))

            self.filename = save_filename
            self.modified = False
            return True
        except Exception as e:
            raise IOError(f"Failed to save file: {str(e)}")
            
    def close(self) -> None:
        """Close the buffer and release resources."""

        if not self.is_large_file or not self.file_map:
            return

        self.file_map.close()
        self.file_map = None

        self.loaded_chunks.clear()

        if not self.file:
            return

        self.file.close()
        self.file = None
