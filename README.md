# KeePass AutoType Helper

This Python script allows you to retrieve credentials from a **KeePass** database and automatically type them into applications or fields using a custom AutoType sequence.

It integrates with:
- [**pykeepass**](https://github.com/libkeepass/pykeepass) — to read entries from a KeePass database (`.kdbx`).
- [**pywinauto**](https://pywinauto.readthedocs.io/) — to send keystrokes and control windows.
- [**dynamicinputbox**](https://pypi.org/project/dynamicinputbox/) — to prompt for KeePass database password interactively.



## Features

- Prompt for KeePass database password in a secure dialog.
- Retrieve a full KeePass entry or just username/password.
- Support for `{USERNAME}`, `{PASSWORD}`, `{URL}`, `{NOTES}`, and `{TITLE}` placeholders in AutoType sequences.
- Handle **special keys** (`{ENTER}`, `{TAB}`, `{F1}`, etc.).
- Handle **delays** (`{DELAY 1000}` for 1 second pause).
- Support **virtual key codes** (`{VKEY 0x41}` for `A`).
- Handle **modifier keys** (`{CTRL}`, `{ALT}`, `{SHIFT}`, `{WIN}`).



## Requirements

Install dependencies via pip:

```bash
pip install pykeepass pywinauto dynamicinputbox
```

## Usage
### 1. Prepare your KeePass database

Make sure your KeePass .kdbx file exists (default: ~/Pwd_Db.kdbx).

Add entries with:
- Title (used to look up the entry).
- Username and Password fields.
- AutoType sequence (e.g., {USERNAME}{TAB}{PASSWORD}{ENTER}). This is optional for the entry, but needed for the use_KeePass_sequence method.

### 2. Import and use in Python
`from keepass_autotype import get_credentials, use_KeePass_sequence `

## Retrieve only username & password
`username, password = get_credentials( "My Entry Title" )`

## Retrieve full entry and auto-type it
`use_KeePass_sequence( "My Entry Title" )`

## Default values

Database file: Pwd_Db.kdbx

Database path: ~ (home directory)

These can be replaced with:
`get_credentials("My Entry Title", file="Custom.kdbx", path="/path/to/db")`


## AutoType Sequence Syntax
Supported placeholders:

* {USERNAME} — Entry's username.
* {PASSWORD} — Entry's password.
* {URL} — Entry's URL.
* {NOTES} — Entry's notes.
* {TITLE} — Entry's title.

Special commands:
* {ENTER}, {TAB}, {ESC}, {F1} ... {F12}, {UP}, {DOWN}, {LEFT}, {RIGHT}.
* {DELAY 1000} — Pause for 1000ms.
* {VKEY 0x41} — Press virtual key (hex code).
* {CTRL}, {ALT}, {SHIFT}, {WIN} — Press and hold modifier.
* {CTRLUP}, {ALTUP}, {SHIFTUP}, {WINUP} — Release modifier.

### Example
In KeePass, set the entry's AutoType sequence to:

`{USERNAME}{TAB}{PASSWORD}{ENTER} `

Then in Python:

`use_KeePass_sequence("My Entry Title") `

The script will:

- Prompt for your KeePass database password.
- Retrieve the username and password from the given entry.
- Automatically type them into the currently focused application.

# Security Notice

This script sends keystrokes to the active window — make sure the correct window is focused before running.

The KeePass database password is entered via a masked prompt but is kept in memory during runtime.

**Use responsibly in trusted environments.**
