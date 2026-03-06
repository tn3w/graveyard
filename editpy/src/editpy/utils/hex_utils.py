"""
Utility functions for hex file operations.
"""

from typing import Optional, Tuple


def is_hex_file(filename: str, sample_size: int = 512) -> bool:
    """
    Detect if a file is likely a hex file by analyzing its contents.

    Args:
        filename (str): Path to the file to analyze
        sample_size (int): Number of bytes to sample for analysis

    Returns:
        bool: True if the file appears to be a hex file
    """

    try:
        with open(filename, 'rb') as f:
            data = f.read(sample_size)

        if not data:
            return False

        printable = sum(32 <= b <= 126 for b in data)
        binary = len(data) - printable

        return (binary / len(data)) > 0.3

    except Exception:
        pass

    return False


def parse_hex_string(hex_str: str) -> Optional[bytes]:
    """
    Parse a hex string into bytes.

    Args:
        hex_str (str): String of hex values (e.g. "FF 00 A5")

    Returns:
        bytes: Parsed bytes or None if invalid
    """

    try:
        clean_str = ''.join(hex_str.split())
        if not all(c in '0123456789ABCDEFabcdef' for c in clean_str):
            return None

        return bytes.fromhex(clean_str)

    except Exception:
        pass

    return None


def format_offset(offset: int, width: int = 8) -> str:
    """
    Format a byte offset as a hex string.

    Args:
        offset (int): Byte offset to format
        width (int): Number of hex digits to use

    Returns:
        str: Formatted hex string
    """

    return f"{offset:0{width}X}"


def get_byte_range(data: bytes, start: int, length: int) -> Tuple[bytes, int]:
    """
    Get a range of bytes and the actual number of bytes returned.
    
    Args:
        data (bytes): Source bytes
        start (int): Starting offset
        length (int): Number of bytes to get
        
    Returns:
        Tuple[bytes, int]: The bytes and actual length returned
    """

    end = min(start + length, len(data))
    return data[start:end], end - start


def find_pattern(data: bytes, pattern: bytes, start: int = 0) -> Optional[int]:
    """
    Find the next occurrence of a byte pattern.

    Args:
        data (bytes): Data to search in
        pattern (bytes): Pattern to search for
        start (int): Starting position for search

    Returns:
        int: Position of pattern or None if not found
    """

    try:
        return data.index(pattern, start)
    except ValueError:
        pass

    return None


def replace_pattern(data: bytearray, pattern: bytes, replacement: bytes) -> int:
    """
    Replace all occurrences of a pattern in the data.

    Args:
        data (bytearray): Data to modify
        pattern (bytes): Pattern to replace
        replacement (bytes): Replacement bytes

    Returns:
        int: Number of replacements made
    """

    if not pattern:
        return 0

    count = 0
    pos = 0

    while True:
        pos = find_pattern(data, pattern, pos)
        if pos is None:
            break

        data[pos:pos + len(pattern)] = replacement
        pos += len(replacement)
        count += 1

    return count
