"""
Search functionality for the code editor.
"""

import re
from typing import List, Optional, Tuple
from ..core.buffer import Buffer, UndoAction


class SearchResult:
    """Represents a search result with position and match information."""
    
    def __init__(self, position: int, length: int, match: bytes):
        self.position = position
        self.length = length
        self.match = match


class SearchEngine:
    """Handles different types of searches in hex data."""

    def __init__(self, buffer: Buffer) -> None:
        self.buffer = buffer
        self.last_search: Optional[Tuple[str, str, bool]] = None

    def find_hex(self, pattern: str, start_pos: int = 0) -> Optional[SearchResult]:
        """Search for a hex pattern in binary data."""

        try:
            hex_bytes = bytes.fromhex(''.join(pattern.split()))
            pos = self.buffer.data.find(hex_bytes, start_pos)

            if pos >= 0:
                return SearchResult(pos, len(hex_bytes), hex_bytes)

        except ValueError:
            pass

        return None

    def find_text(self, text: str, case_sensitive: bool = True, start_pos: int = 0) -> Optional[SearchResult]:
        """Search for a text string in the ASCII representation of the buffer."""

        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in self.buffer.data)

        if case_sensitive:
            pos = ascii_str.find(text, start_pos)
            if pos >= 0:
                return SearchResult(pos, len(text), self.buffer.data[pos:pos+len(text)])

            return None

        search_str = text.lower()
        ascii_str_lower = ascii_str.lower()

        pos = ascii_str_lower.find(search_str, start_pos)
        if pos >= 0:
            return SearchResult(pos, len(text), self.buffer.data[pos:pos+len(text)])

        return None

    def find_regex(self, pattern: str, case_sensitive: bool = True, start_pos: int = 0) -> Optional[SearchResult]:
        """Search using a regular expression pattern in the ASCII representation."""

        try:
            ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in self.buffer.data)

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            match = regex.search(ascii_str, start_pos)
            if match:
                return SearchResult(
                    match.start(),
                    match.end() - match.start(),
                    self.buffer.data[match.start():match.end()]
                )

        except Exception as e:
            print(f"Regex search error: {e}")

        return None

    def find_wildcard(self, pattern: str, start_pos: int = 0) -> Optional[SearchResult]:
        """
        Search using wildcard pattern (* and ?) in the ASCII representation.

        Args:
            pattern (str): The pattern to search for, where:
                          * stands for any number of characters (including zero)
                          ? stands for exactly one character
            start_pos (int): Position to start searching from

        Returns:
            Optional[SearchResult]: The search result if found
        """

        if not pattern:
            return None

        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in self.buffer.data)

        regex_pattern = ""
        for c in pattern:
            if c == '*':
                regex_pattern += ".*"
                continue

            if c == '?':
                regex_pattern += "."
                continue

            if c in ('.', '+', '(', ')', '[', ']', '{', '}', '^', '$', '|'):
                regex_pattern += "\\" + c
                continue

            regex_pattern += c

        try:
            regex = re.compile(regex_pattern, re.DOTALL)

            match = regex.search(ascii_str, start_pos)
            if match:
                return SearchResult(
                    match.start(),
                    match.end() - match.start(),
                    self.buffer.data[match.start():match.end()]
                )

        except Exception as e:
            print(f"Wildcard search error: {e}")

        return None

    def find_next(self, pattern: str, search_type: str = 'text',
                 case_sensitive: bool = False, start_pos: Optional[int] = None) -> Optional[SearchResult]:
        """
        Find the next occurrence of a pattern.

        Args:
            pattern (str): The pattern to search for
            search_type (str): One of 'text', 'hex', 'regex', or 'wildcard'
            case_sensitive (bool): Whether to perform case-sensitive search
            start_pos (int): Position to start searching from (defaults to current cursor)

        Returns:
            Optional[SearchResult]: The search result if found
        """

        if not pattern:
            return None

        self.last_search = (pattern, search_type, case_sensitive)

        if start_pos is None:
            start_pos = self.buffer.cursor_pos

        if search_type == 'hex':
            return self.find_hex(pattern, start_pos)

        if search_type == 'regex':
            return self.find_regex(pattern, case_sensitive, start_pos)

        if search_type == 'wildcard':
            return self.find_wildcard(pattern, start_pos)

        return self.find_text(pattern, case_sensitive, start_pos)

    def find_previous(self) -> Optional[SearchResult]:
        """Find the previous occurrence of the last search."""

        if not self.last_search:
            return None

        pattern, search_type, case_sensitive = self.last_search

        cursor_pos = self.buffer.cursor_pos
        last_result = None
        pos = 0

        while True:
            result = self.find_next(pattern, search_type, case_sensitive, pos)
            if not result or result.position >= cursor_pos:
                break

            last_result = result
            pos = result.position + 1

        return last_result

    def replace_next(self, pattern: str, replacement: str,
                    search_type: str = 'text', case_sensitive: bool = False) -> bool:
        """
        Replace the next occurrence of a pattern.

        Args:
            pattern (str): Pattern to search for
            replacement (str): Replacement text/bytes
            search_type (str): Type of search ('text', 'hex', 'regex', 'wildcard')
            case_sensitive (bool): Whether to perform case-sensitive search

        Returns:
            bool: True if replacement was made
        """

        result = self.find_next(pattern, search_type, case_sensitive)
        if not result:
            return False

        if search_type == 'hex':
            try:
                replacement_bytes = bytes.fromhex(''.join(replacement.split()))
            except ValueError:
                return False
        else:
            replacement_bytes = replacement.encode('utf-8')

        old_data = self.buffer.data[result.position:result.position + result.length]
        self.buffer.data[result.position:result.position + result.length] = replacement_bytes

        self.buffer.undo_stack.append(UndoAction(
            position=result.position,
            old_data=old_data,
            new_data=replacement_bytes,
            action_type='replace'
        ))

        return True

    def replace_all(self, pattern: str, replacement: str,
                   search_type: str = 'text', case_sensitive: bool = False) -> int:
        """
        Replace all occurrences of a pattern.

        Args:
            pattern (str): Pattern to search for
            replacement (str): Replacement text/bytes
            search_type (str): Type of search ('text', 'hex', 'regex', 'wildcard')
            case_sensitive (bool): Whether to perform case-sensitive search

        Returns:
            int: Number of replacements made
        """

        count = 0
        while self.replace_next(pattern, replacement, search_type, case_sensitive):
            count += 1

        return count

    def find_all(self, pattern: str, search_type: str = 'text',
                case_sensitive: bool = False) -> List[SearchResult]:
        """
        Find all occurrences of a pattern.

        Args:
            pattern (str): The pattern to search for
            search_type (str): One of 'text', 'hex', 'regex', or 'wildcard'
            case_sensitive (bool): Whether to perform case-sensitive search

        Returns:
            List[SearchResult]: All search results found
        """

        if not pattern:
            return []

        self.last_search = (pattern, search_type, case_sensitive)

        results = []
        pos = 0

        while True:
            result = None

            if search_type == 'hex':
                result = self.find_hex(pattern, pos)
            elif search_type == 'regex':
                result = self.find_regex(pattern, case_sensitive, pos)
            elif search_type == 'wildcard':
                result = self.find_wildcard(pattern, pos)
            else:
                result = self.find_text(pattern, case_sensitive, pos)

            if not result:
                break

            results.append(result)
            pos = result.position + 1

            if pos >= len(self.buffer.data):
                break

        return results
