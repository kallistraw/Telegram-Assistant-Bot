import re
import os
# import yaml
from .database import var


# -------------------------------- Command regex ------------------------------- #
hndlr = rf"^({'|'.join(map(re.escape, var.PREFIXES))})"  # Store the prefix-matching regex

# ---------------------------- Multi-language thing -----------------------fine the path to the local
# TODO: Finish this thing...
# LOCALES_DIR = '..locales/strings'
# 
# def load_language(language_code):
#     file_path = os.path.join(LOCALES_DIR, f"{language_code}.yml")
#     with open(file_path, 'r', encoding='utf-8') as file:
#         return yaml.safe_load(file)
# 
# def get_string(key, strings, fallback_strings=None):
#     if key in strings:
#         return strings[key]
#     elif fallback_strings and key in fallback_strings:
#         return fallback_strings[key]
#     else:
#         return f"String not found: {key}"
# 
# # Load user's language
# user_language = LANG if LANG else 'en'
# user_language_data = load_language(user_language)
# user_strings = user_language_data.get('strings', {})
# 
# # Load fallback language (English)
# fallback_language_data = load_language('en')
# fallback_strings = fallback_language_data.get('strings', {})
# 
# # Get a string
# start = get_string('start', user_strings, fallback_strings)
