"""
Utility package for code editor support functions.
"""

from .hex_utils import (
    is_hex_file,
    parse_hex_string,
    format_offset,
    get_byte_range,
    find_pattern,
    replace_pattern
)
from .search import SearchEngine, SearchResult

__all__ = [
    'is_hex_file',
    'parse_hex_string',
    'format_offset',
    'get_byte_range',
    'find_pattern',
    'replace_pattern',
    'SearchEngine',
    'SearchResult'
]
