```
███████╗██╗██╗     ██╗  ██╗   ██╗    ██████╗ ██╗   ██╗
██╔════╝██║██║     ██║  ╚██╗ ██╔╝    ██╔══██╗╚██╗ ██╔╝
███████╗██║██║     ██║   ╚████╔╝     ██████╔╝ ╚████╔╝ 
╚════██║██║██║     ██║    ╚██╔╝      ██╔═══╝   ╚██╔╝  
███████║██║███████╗███████╗██║       ██║        ██║   
╚══════╝╚═╝╚══════╝╚══════╝╚═╝       ╚═╝        ╚═╝ 
```
# Silly Python
A command line tool to hide your Python file behind random code.

## Silly Python installation
Before you start installing Silly Python, you need python installed (download at: [https://www.python.org/downloads/](https://www.python.org/downloads/))
1. Download this script as a ZIP folder: ![Click here](https://github.com/tn3w/sillypython/archive/refs/heads/master.zip) or use git to download it with `git clone https://github.com/tn3w/sillypython.git`.
2. Unpack the ZIP archive into a folder.
3. Use the Python script `silly.py` in the folder with the `-h` arg to get help.

## Commands
| Command                   | Information                                                                              | Example                                  |
| ------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------- |
| -a, --about               | Displays an About menu with information about the software                               | `python silly.py -a`                     |
| -h, --help                | Displays a help menu similar to this                                                     | `python silly.py -h`                     |
| -f, --file <file_path>    | Defines which file to use, file_path should be a string.                                 | `python silly.py -f some_python_file.py` |
| -i, --iterations <number> | Specifies how many times Sillify should run. From 30 - 40 the program becomes very slow. | `python silly.py -i 25`                  |
