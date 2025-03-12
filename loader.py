import importlib
import os
from . import log

loaded_modules = {}


def load_modules():
    """Dynamically load all modules."""
    module_dir = "modules"
    for filename in os.listdir(module_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"modules.{filename[:-3]}"
            #            try:
            loaded_modules[module_name] = importlib.import_module(module_name)
    #            except Exception as e:
    #                log.error(f"Failed to load {module_name}: {e}")
    log.info(f"{len(loaded_modules)} Modules loaded.")


def reload_modules():
    """Unload and reload all modules."""
    for module_name in list(loaded_modules.keys()):
        try:
            loaded_modules[module_name] = importlib.reload(loaded_modules[module_name])
        except Exception as e:
            log.error(f"Failed to reload {module_name}: {e}")
    log.info(f"{len(loaded_modules)} Modules reloaded.")
