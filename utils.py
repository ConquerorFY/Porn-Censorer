import pprint
import os

pp = pprint.PrettyPrinter(indent=1, width=80, depth=None)

def print(args: str):
    pp.pprint(args)

def delete_rename_file(old_name, new_name):
    try:
        os.remove(new_name)
        os.rename(old_name, new_name)
        # print(f"File renamed from {old_name} to {new_name}")
    except FileNotFoundError:
        print(f"The file {old_name} does not exist.")
    except PermissionError:
        print(f"Permission denied to rename the file {old_name}.")
    except Exception as e:
        print(f"An error occurred: {e}")