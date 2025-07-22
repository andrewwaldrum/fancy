#!/usr/bin/env python3
import sys
import cmd
import inspect
from my_class import MyClass

import readline

# macOS uses libedit, which requires this special binding
if 'libedit' in readline.__doc__:
    readline.parse_and_bind("bind ^I rl_complete")  # For libedit
else:
    readline.parse_and_bind("tab: complete")        # For readline

class DynamicShell(cmd.Cmd):
    intro = "Welcome to MyClass interactive shell. Type 'help' or '?' to list commands.\n"
    prompt = "(myclass) "

    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        # Dynamically get all public methods (ignore _private)
        self.methods = [m for m, _ in inspect.getmembers(obj, predicate=inspect.ismethod) if not m.startswith("_")]
        # Add our built-in commands
        self.builtin_cmds = ['methods', 'exit']

    def completenames(self, text, *ignored):
        """Autocomplete method names and built-in commands."""
        commands = self.methods + self.builtin_cmds
        return [name for name in commands if name.startswith(text)]

    def default(self, line):
        """Attempt to call a method dynamically if command not found."""
        parts = line.split()
        if not parts:
            return
        method_name, *args = parts
        if method_name in self.methods:
            try:
                method = getattr(self.obj, method_name)
                result = method(*args)
                print(result)
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"Unknown command: {method_name}")

    def do_methods(self, arg):
        """List available methods of the class."""
        print("Available methods:")
        for m in self.methods:
            sig = inspect.signature(getattr(self.obj, m))
            print(f"  {m}{sig}")

    def do_exit(self, arg):
        """Exit the shell."""
        print("Goodbye!")
        return True

    def do_EOF(self, arg):
        """Exit on Ctrl-D."""
        print("Goodbye!")
        return True

def main():
    if len(sys.argv) < 2:
        print("Usage: cli_wrapper.py <path>")
        sys.exit(1)
    path = sys.argv[1]
    obj = MyClass(path)
    DynamicShell(obj).cmdloop()

if __name__ == "__main__":
    main()
