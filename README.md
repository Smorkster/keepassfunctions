# KeePass AutoType Helper

A secure Python wrapper for retrieving credentials from a **KeePass** database and automatically typing them into applications using custom AutoType sequences. This library prioritizes security with controlled access patterns and cleanup of sensitive data.

## Features

- **Security-focused design** with restricted access to KeePass database
- **Context manager support** for automatic resource cleanup
- **Secure password handling** with automatic memory clearing
- **GUI and CLI password prompts** via dynamicinputbox
- **KeePass AutoType support** with placeholders, special keys, delays, and virtual keys, see [KeePass Auto-Type documentation](https://keepass.info/help/base/autotype.html)
- **Error handling and logging** for robust operation
- **Controlled database access** through a secure proxy pattern

## Requirements

Install dependencies via pip:

```bash
pip install pykeepass pywinauto dynamicinputbox
```

## Quick Start

### Basic Usage

```python
from keepassfunctions import KeePassFunctions

# Initialize with your database path
db_path = "~/Pwd_Db.kdbx"  # or full path to your .kdbx file

# Use context manager for secure handling
with KeePassFunctions(db_path, with_gui=True) as kp:
    # Get username and password
    username, password = kp.get_credentials("My Entry Title")
    
    # Or auto-type using the entry's AutoType sequence
    kp.use_KeePass_sequence("My Entry Title")
```

### GUI vs CLI Mode

```python
# GUI mode (default) - shows password dialog
with KeePassFunctions(db_path, with_gui=True) as kp:
    # Your code here
    pass

# CLI mode - command line password prompt
with KeePassFunctions(db_path, with_gui=False) as kp:
    # Your code here
    pass
```

## API Reference

### Core Methods

#### `get_credentials(entry_title: str, return_entry: bool = False) -> tuple`
Retrieve credentials from a KeePass entry.

- **Parameters:**
  - `entry_title`: Exact title of the KeePass entry
  - `return_entry`: If True, returns the full entry object instead of just username/password
- **Returns:** Tuple of `(username, password)` or full entry object
- **Raises:** `ValueError` if entry is not found

#### `use_KeePass_sequence(kp_entry: str) -> None`
Execute the AutoType sequence from a KeePass entry.

- **Parameters:**
  - `kp_entry`: Title of the entry containing the AutoType sequence
- **Raises:** `ValueError` if entry is not found or has no AutoType sequence

#### `entry_exists(title: str) -> bool`
Check if an entry with the given title exists.

#### `get_entry_count() -> int`
Get the total number of entries in the database.

#### `validate_autotype_available(entry_title: str) -> bool`
Check if an entry has an AutoType sequence available.

### Advanced Methods

#### `send_autotype_sequence(sequence: str, replacements: dict) -> None`
Send a custom AutoType sequence with placeholder replacements.

```python
with KeePassFunctions(db_path) as kp:
    username, password = kp.get_credentials("My Entry")
    
    custom_sequence = "{USERNAME}{TAB}{PASSWORD}{DELAY 1000}{ENTER}"
    replacements = {
        '{USERNAME}': username,
        '{PASSWORD}': password
    }
    
    kp.send_autotype_sequence(custom_sequence, replacements)
```

## Security Features

### Controlled Access
The library uses a secure proxy pattern that restricts access to KeePass database operations:

```python
with KeePassFunctions(db_path) as kp:
    # Only specific operations are allowed through kp.kp proxy
    entry_count = kp.kp.get_entry_count()
    exists = kp.kp.validate_entry_exists("My Entry")
    entry = kp.kp.find_entries_by_title("My Entry")
```

### Automatic Cleanup
- **Context manager required:** All operations must use `with` statement
- **Automatic password clearing:** Sensitive data is securely overwritten in memory
- **Resource cleanup:** Database connections and sensitive data are automatically cleaned up
- **Error handling:** Comprehensive cleanup even during exceptions

### Security Best Practices
- Database passwords are never stored permanently
- Sensitive data is cleared from memory after use
- Limited exposure of KeePass database internals
- Secure handling of AutoType sequences and replacements

## Error Handling

The library provides comprehensive error handling:

```python
try:
    with KeePassFunctions("nonexistent.kdbx") as kp:
        username, password = kp.get_credentials("My Entry")
except FileNotFoundError:
    print("Database file not found")
except ValueError as e:
    print(f"Entry not found: {e}")
except RuntimeError as e:
    print(f"Context manager error: {e}")
```

## Examples

### Complete Login Automation

```python
from keepassfunctions import KeePassFunctions

def auto_login(entry_name: str, db_path: str = "~/Pwd_Db.kdbx"):
    """Automatically log in using KeePass entry."""
    try:
        with KeePassFunctions(db_path, with_gui=True) as kp:
            if kp.validate_autotype_available(entry_name):
                print(f"Executing AutoType for: {entry_name}")
                kp.use_KeePass_sequence(entry_name)
            else:
                print("No AutoType sequence available")
                username, password = kp.get_credentials(entry_name)
                print(f"Retrieved credentials for: {username}")
                
    except Exception as e:
        print(f"Error: {e}")

# Usage
auto_login("Gmail Account")
```

### Database Statistics

```python
with KeePassFunctions("~/Pwd_Db.kdbx") as kp:
    total_entries = kp.get_entry_count()
    print(f"Database contains {total_entries} entries")
    
    # Check specific entries
    entries_to_check = ["Gmail", "GitHub", "Bank Account"]
    for entry in entries_to_check:
        if kp.entry_exists(entry):
            has_autotype = kp.validate_autotype_available(entry)
            print(f"✓ {entry} (AutoType: {'Yes' if has_autotype else 'No'})")
        else:
            print(f"✗ {entry} (Not found)")
```

## Security Notice

- **Window focus:** AutoType sends keystrokes to the currently focused window - ensure correct window is active
- **Trusted environment:** Use only in secure, trusted environments
- **Password visibility:** Be aware that AutoType sequences are visible as they're typed
- **Memory security:** While passwords are cleared from memory, complete security depends on your system's memory management

## License

MIT License - See LICENSE file for details.

## Author

**Smorkster**  
GitHub: [https://github.com/Smorkster/keepassfunctions](https://github.com/Smorkster/keepassfunctions)

## Version History

- **v2.0** - Major security improvements, context manager support, secure proxy pattern
- **v1.x** - Initial implementation