# EditPy - Advanced Code Editor and Hex Viewer

A powerful terminal-based code editor and hex viewer implemented in Python using curses. Features a modern interface with multi-file support, advanced editing capabilities, and an intuitive user interface.

## Features
- Multi-file support with quick switching (Ctrl + Number)
- File summary and statistics
- Large file support:
  - Efficient chunked loading
  - Memory-mapped files
  - Handles files of any size

### Code Editor
- Syntax highlighting:
  - Automatic language detection
  - Support for Python, JavaScript, HTML, CSS, C, C++
  - Line numbers for easy navigation
  - Edit mode for code files
- Advanced editing functions:
  - Insert, delete (char/word/line)
  - Cut, copy, and paste
  - Undo/redo support
- Navigation features:
  - Cursor movement
  - Jump to start/end
  - Text selection
- Search and replace:
  - Plain text search
  - Regex support
  - Wildcards

### Hex Viewer & Editor
- Split view showing hex and ASCII representation
- 16 bytes per line display with automatic adjustment
- Real-time hex and string editing
- Byte manipulation:
  - Direct hex editing 
  - Byte offset navigation
  - Hex file autodetection

## Installation

### Quick Install
```bash
git clone https://github.com/TN3W/editpy.git
```

```bash
cd editpy
```

```bash
pip install -e .
```

## Usage

```bash
editpy [filename]
```

## Keyboard Shortcuts

### General
- `Ctrl + X`: Quit
- `Ctrl + W`: Save
- `Ctrl + O`: Open file
- `Ctrl + E`: Toggle edit mode for code files
- `Alt + [1-9]`: Switch between open files

### Navigation
- Arrow keys: Move cursor
- `Home/End`: Start/end of line
- `PgUp/PgDn`: Page up/down
- `Scroll`: Scroll up/down
- `Ctrl + Home/End`: Start/end of file

### Editing
- `Tab`: Toggle insert mode (hex) or insert 4 spaces (code)
- `Delete`: Delete character
- `Backspace`: Delete previous character
- `Ctrl + K`: Cut line
- `Ctrl + U`: Paste line
- `Ctrl + B`: Back / Undo
- `Ctrl + Y`: Redo

### Search
- `Ctrl + F`: Find
- `Ctrl + R`: Replace
- `Ctrl + N`: Find next
- `Ctrl + P`: Find previous

## License
Copyright 2025 TN3W

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
