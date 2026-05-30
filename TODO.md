# TODO

- Ensure all multi-line docstrings look like so:

"""
Content that would have
multiple lines.
"""

and NOT:

"""Content that would have
multiple lines.
"""

- Make sure all leaf commands have pretty output by default.
- Make sure all leaf commands have --json, if it is applicable.
- Make sure leaf command's tables do not have JSON (or Python objects, or machine-readable output)
  in rows.
- Make sure all TypedDict fields are ordered alphabetically case-sensitive.
- Make sure all .py files under typing/ have TypeAliases first (ordered alphabetically
  case-sensitive), then TypedDicts.
- Make sure all Returns sections in docstrings match the actual return type.
- Get the correct return type (a typeddict) for `find_next_departure`
- Make `_extract_schedules` use a stronger parameter type
- Make sure docs build without a warning or error
- Write unit tests covering every file, 100% coverage.
- Move fordpass/commands/root.py to fordpass/main.py and fix all imports.
