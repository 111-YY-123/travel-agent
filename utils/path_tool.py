import os
from pathlib import Path

def get_abs_path(relative_path):
    return str(Path(__file__).resolve().parent.parent / relative_path)

if __name__ == "__main__":
    print(get_abs_path("prompts/supervisor_prompts.txt"))
    with open(get_abs_path("prompts/supervisor_prompts.txt"), "r") as f:
        print(f.read())