# keepassfunctions

`keepassfunctions` is a context-managed wrapper around `pykeepass` for exact-title
credential lookup and KeePass AutoType execution. It supports console and GUI
password prompts, exposes only a restricted database proxy, and performs
best-effort cleanup of sensitive values after use.

## Highlights

- Context manager based database access
- Exact-title lookup for credentials and entries
- KeePass AutoType support with placeholders, special keys, delays, and virtual keys
- Console or GUI password prompt
- Restricted proxy instead of raw `PyKeePass` access
- Best-effort cleanup of passwords and replacement values

## Requirements

- Python 3.10 or newer
- A KeePass `.kdbx` database
- Windows is recommended for AutoType because key input is sent with `pywinauto`

## Installation

From this repository:

```bash
pip install .
```

This installs the declared runtime dependencies:

- `dynamicinputbox`
- `pykeepass`
- `pywinauto`

## Quick Start

### Retrieve credentials

```python
from keepassfunctions.keepassfunctions import KeePassFunctions

db_path = r"C:\Passwords.kdbx"

with KeePassFunctions(db_path=db_path, with_gui=False) as kp:
    username, password = kp.get_credentials("My Entry")
    print(username)
    print("*" * len(password) if password else "N/A")
```

### Retrieve the full entry

```python
from keepassfunctions.keepassfunctions import KeePassFunctions

db_path = r"C:\Passwords.kdbx"

with KeePassFunctions(db_path=db_path, with_gui=True) as kp:
    entry = kp.get_credentials("My Entry", return_entry=True)
    print(entry.title)
    print(entry.username)
    print(entry.url)
    print(bool(entry.autotype_sequence))
```

### Execute the KeePass AutoType sequence

```python
from keepassfunctions.keepassfunctions import KeePassFunctions

db_path = r"C:\Passwords.kdbx"

with KeePassFunctions(db_path=db_path, with_gui=False) as kp:
    kp.use_KeePass_sequence("My Entry")
```

### Send a custom AutoType sequence

```python
from keepassfunctions.keepassfunctions import KeePassFunctions

db_path = r"C:\Passwords.kdbx"

with KeePassFunctions(db_path=db_path, with_gui=False) as kp:
    username, password = kp.get_credentials("My Entry")

    kp.send_autotype_sequence(
        "{USERNAME}{TAB}{PASSWORD}{DELAY 500}{ENTER}",
        {
            "{USERNAME}": username,
            "{PASSWORD}": password,
        },
    )
```

## Public API

### `KeePassFunctions(db_path: str, with_gui: bool = False)`

Create the wrapper. The database is opened only when the instance is used in a
`with` block.

### `get_credentials(entry_title: str, return_entry: bool = False)`

Return credentials for the first exact-title match.

- `return_entry=False`: returns `(username, password)`
- `return_entry=True`: returns the full `Entry`

Raises `ValueError` if no matching entry is found.

### `use_KeePass_sequence(kp_entry: str) -> None`

Load the entry by exact title and execute its stored AutoType sequence.

Raises `ValueError` if the entry is missing or if no AutoType sequence is set.

### `entry_exists(title: str) -> bool`

Return `True` if at least one exact-title match exists.

### `get_entry_count() -> int`

Return the total number of entries in the open database.

### `validate_autotype_available(entry_title: str) -> bool`

Return whether the first exact-title match has a non-empty AutoType sequence.

### `send_autotype_sequence(sequence: str, replacements: dict) -> None`

Resolve placeholders in a sequence and send the resulting key events to the
active window.

Supported token categories include:

- Placeholder replacements such as `{USERNAME}` and `{PASSWORD}`
- Special keys such as `{ENTER}`, `{TAB}`, and function keys
- Modifier keys such as `{CTRL}` and `{SHIFT}`
- Delays such as `{DELAY 500}`
- Virtual keys such as `{VKEY 0D}`

## Restricted Proxy

The `kp` property exposes a restricted proxy rather than the raw `PyKeePass`
instance.

```python
from keepassfunctions.keepassfunctions import KeePassFunctions

db_path = r"C:\Passwords.kdbx"

with KeePassFunctions(db_path=db_path, with_gui=False) as kp:
    count = kp.kp.get_entry_count()
    exists = kp.kp.validate_entry_exists("My Entry")
    entries = kp.kp.find_entries_by_title("My Entry", first=True)
```

The proxy only exposes:

- `find_entries_by_title()`
- `get_entry_count()`
- `validate_entry_exists()`

## Demo Script

The repository includes a demo script with both non-interactive and interactive
usage modes.

```bash
python demo.py --interactive
python demo.py --interactive --gui
python demo.py --db C:\Passwords.kdbx --entry "My Entry" --get-credentials
python demo.py --db C:\Passwords.kdbx --entry "My Entry" --get-full-entry
python demo.py --db C:\Passwords.kdbx --entry "My Entry" --autotype
```

## Usage Notes

- Use `KeePassFunctions` inside a `with` block. Public operations are designed
  around an active context manager.
- Entry lookup is based on exact title matches.
- AutoType sends keystrokes to the currently focused window, so make sure the
  correct target window is active before running it.
- Cleanup is best-effort. Sensitive values are cleared where practical, but
  memory handling still depends on Python and the operating system.

## Error Handling

Typical exceptions include:

- `FileNotFoundError` for an invalid database path
- `RuntimeError` when methods are used outside a context manager
- `ValueError` when an entry cannot be found or an AutoType sequence is missing

## Version History

- `2.1.0`: Refined the wrapper API, updated dependency metadata, and refreshed the demo scripts
- `2.0`: Added the secure proxy pattern and context-manager based access

## License

MIT License. See `LICENSE`.
