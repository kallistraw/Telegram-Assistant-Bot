import importlib
import os
import traceback

from .. import LOGS


def load_modules():
    """
    Dynamically imports all Python files inside 'modules' directory.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    module_dir = os.path.join(base_dir, "modules")
    if not os.path.exist(module_dir):
        raise FileNotFoundError(
            f"Expected '{base_dir}/modules' but got '{module_dir}' instead."
        )

    for file in os.listdir(module_dir):
        if file.endswith(".py") and not file.startswith("_"):
            module_name = f"{module_dir}.{file[:-3]}"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                # debugging
                import sys

                tb = traceback.format_exc()
                LOGS.error(f"Failed to load {module_name}: {e}\n{tb}")
                sys.exit()


def is_dangerous(cmd: str):
    """
    Used to determine wheter something is considered dangerous or not.

    Args:
        cmd (str): The string to be analyzed.

    Returns:
        bool: True if it's dangerous.
    """
