import random as rand
import sys
import os
import json
from base64 import b64encode

LOGO = """
███████╗██╗██╗     ██╗  ██╗   ██╗    ██████╗ ██╗   ██╗
██╔════╝██║██║     ██║  ╚██╗ ██╔╝    ██╔══██╗╚██╗ ██╔╝
███████╗██║██║     ██║   ╚████╔╝     ██████╔╝ ╚████╔╝ 
╚════██║██║██║     ██║    ╚██╔╝      ██╔═══╝   ╚██╔╝  
███████║██║███████╗███████╗██║       ██║        ██║   
╚══════╝╚═╝╚══════╝╚══════╝╚═╝       ╚═╝        ╚═╝   
"""

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(LOGO)

def sillyfy(python_code: str):
    unique_characters = list(set(python_code))
    new_character_meanings = dict()
    character_used = []
    for character in unique_characters:
        random_character = rand.choice(unique_characters)
        while random_character in character_used:
            random_character = rand.choice(unique_characters)
        character_used.append(random_character)
        if character == random_character:
            continue
        new_character_meanings[character] = random_character
    
    new_python_code = list(python_code)
    for character, new_character_meaning  in new_character_meanings.items():
        for char_index, char in enumerate(python_code):
            if char == character:
                new_python_code[char_index] = new_character_meaning
    return ''.join(new_python_code), new_character_meanings

def random():
    return ''.join(rand.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz") for _ in range(rand.choice([3, 4, 5, 6, 7, 8, 9, 10, 11])))

def create_template(silly_code: str, replaces: str):
    r1, ra, rb, r2, r3, r4, r5, r6, r7, r8, r9 = random(), random(), random(), random(), random(), random(), random(), random(), random(), random(), random()
    while len(set([r1, ra, rb, r2, r3, r4, r5])) < 5:
        r1, ra, rb, r2, r3, r4, r5, r6, r7, r8, r9 = random(), random(), random(), random(), random(), random(), random(), random(), random(), random(), random(), random()

    replaces = json.dumps(replaces)
    template = f'''from base64 import b64decode as {r4}
{r1} = {replaces}
{r1} = dict(({ra}, {rb}) for {rb}, {ra} in {r1}.items())

def {r2}({r3}):
    {r3} = {r4}({r3}).decode()
    {r5} = list({r3})
    for {r6}, {r7} in {r1}.items():
        for {r8}, {r9} in enumerate({r3}):
            if {r9} == {r6}:
                {r5}[{r8}] = {r7}
    return ''.join({r5})
    
exec({r2}("""{silly_code}"""))'''
    return template

if __name__ == "__main__":
    clear_console()

    if len(sys.argv) < 2:
        print("[Error] No args given, use -h or --help to get a help menu with all commands displayed.")

    elif "-a" in sys.argv or "--about" in sys.argv:
        print("Programmed by TN3W\nMake your Python code look silly")
        print("- https://github.com/tn3w/sillypython -")

    elif "-h" in sys.argv or "--help" in sys.argv:
        print("Use the following command arguments:")
        print("-a, --about               > Displays an About menu with information about the software")
        print("-h, --help                > Displays this help menu")
        print("-f, --file <filename>     > Define the file which should look silly")
        print("-i, --iterations <number> > How many layers of sillyity there should be. (Default: 20)")

    elif not "-f" in sys.argv and not "--file" in sys.argv:
        print("[Error] No file was specified with -f or --file. For more information use -h or --help.")

    else:
        if "-f" in sys.argv:
            file_arg_index = sys.argv.index("-f") + 1
        else:
            file_arg_index = sys.argv.index("--file") + 1

        try:
            file_path = sys.argv[file_arg_index]
        except:
            print("[Error] No file was specified after -f or --file.")
        else:
            if not os.path.isfile(file_path):
                print(f"[Error] The given file '{file_path}' either does not exist or no file was specified after -f or --file.")
            else:
                iterations = 10
                is_error = False
                if "-i" in sys.argv or "--iterations" in sys.argv:
                    if "-i" in sys.argv:
                        iteration_arg_index = sys.argv.index("-i") + 1
                    else:
                        iteration_arg_index = sys.argv.index("--iterations") + 1
                    try:
                        new_iterations = sys.argv[iteration_arg_index]
                    except:
                        is_error = True
                        print("[Error] No iteration number was given after -i or --iterations.")
                    else:
                        try:
                            iterations = int(new_iterations)
                            if iterations < 1:
                                is_error = True
                                print("[Error] The iteration number given by -i or --iterations is less than 1, which does not work.")
                        except:
                            is_error = True
                            print("[Error] The iteration number given after -i or --iterations is not a number.")
                if not is_error:
                    _, file_name = os.path.split(file_path)
                    file_name = file_name.replace("." + file_name.split(".")[-1], "")
                    try:
                        with open(file_path, "r", encoding = "utf-8") as file:
                            code = file.read()
                    except Exception as e:
                        print(f"[Error] File '{file_path}' could not be read, error information: {e}")
                    else:
                        for index in range(iterations):
                            clear_console()
                            print("Iteration Count:", index+1)

                            silly_code, replaces = sillyfy(code)
                            silly_code = b64encode(silly_code.encode()).decode()
                            code = create_template(silly_code, replaces)

                        clear_console()
                        new_file_path = os.path.join(os.path.dirname(file_path), file_name + "-s.py")
                        if os.path.isfile(new_file_path):
                            print(f"[Error] File '{new_file_path}' could not be written to because it already exists.")
                        else:
                            try:
                                with open(new_file_path, "w") as file:
                                    file.write(code)
                            except Exception as e:
                                print(f"[Error] Could not write to file '{new_file_path}', error information: {e}")
                            else:
                                print(f"File '{file_path}' successfully made silly, result stored in file '{new_file_path}'.")
    input("Enter: ")
    exit()

