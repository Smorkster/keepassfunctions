import os
import sys
import time
import pykeepass

from pywinauto.keyboard import send_keys
from dynamicinputbox import dynamic_input

SPECIAL_KEYS = {
    "ENTER", "TAB", "ESC", "ESCAPE", "BACKSPACE", "SPACE",
    "LEFT", "RIGHT", "UP", "DOWN", "DELETE", "INSERT",
    "HOME", "END", "PGUP", "PGDN", "F1", "F2", "F3", "F4",
    "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
}

MODIFIER_KEYS = {"CTRL", "ALT", "SHIFT", "WIN"}
MODIFIER_RELEASE = {"CTRLUP", "ALTUP", "SHIFTUP", "WINUP"}

def _get_keepass_password():
    """
    Prompt the user for the KeePass database password.
    Returns the password as a bytearray so it can be securely cleared.
    """
    entered_password = dynamic_input(
        title="KeePass Password",
        inputs=[{'label': 'Enter password to KeePass-database file', 'show': '*'}]
    ).get(dictionary=True)
    
    pw_str = list(entered_password.get('inputs', {}).values())[0]
    if len(pw_str) == 0 or entered_password.get('button', None) != 'OK':
        dynamic_input("No password", "No password entered.\nExiting")
        sys.exit()

    pw_bytes = bytearray(pw_str, 'utf-8')
    # Overwrite pw_str immediately
    pw_str = "\0" * len(pw_str)
    del pw_str
    return pw_bytes


def get_credentials(entry_title, return_entry=False, file=None, path=None):
    """
    Get credential entry from KeePass database file.
    """
    if file is None:
        file = 'Pwd_Db.kdbx'
    if path is None:
        path = '~'
    keepass_file = os.path.expanduser(os.sep.join([path, file]))

    kp_password = _get_keepass_password()
    try:
        kp = pykeepass.PyKeePass(keepass_file, password=kp_password.decode())
    except pykeepass.exceptions.CredentialsError as e:
        kp_password[:] = b"\0" * len(kp_password)
        del kp_password
        dynamic_input("Error when reading", f"Could not read KeePass-database file:\n{e.args[0]}")
        sys.exit()
    except FileNotFoundError as e:
        kp_password[:] = b"\0" * len(kp_password)
        del kp_password
        dynamic_input("Error when reading", f"Could not find file:\n{e.args[1]}")
        sys.exit()
    except Exception as e:
        kp_password[:] = b"\0" * len(kp_password)
        del kp_password
        dynamic_input("Error when reading", e.args[0])
        sys.exit()

    # Clear KeePass DB password from memory
    kp_password[:] = b"\0" * len(kp_password)
    del kp_password

    entry = kp.find_entries(title=entry_title, first=True)
    if entry:
        if return_entry:
            return entry
        else:
            return entry.username, entry.password
    else:
        raise ValueError(f"Could not find entry with the given name '{entry_title}'")


def send_autotype_sequence(sequence: str, replacements: dict):
    """
    Send an autotype sequence to the active window, replacing placeholders with actual values.
    """
    for key, value in replacements.items():
        sequence = sequence.replace(key.upper(), value)

    i = 0
    output = ""
    while i < len(sequence):
        if sequence[i] == '{':
            end = sequence.find('}', i)
            if end == -1:
                sequence = None
                replacements.clear()
                raise ValueError(f"Unmatched curlybrace in sequence")
            token = sequence[i + 1:end].strip().upper()
            i = end + 1

            if token.startswith("DELAY "):
                if output:
                    send_keys(output, pause=0.01)
                    output = ""
                delay_ms = int(token.split()[1])
                time.sleep(delay_ms / 1000)
                continue
            elif token.startswith("VKEY "):
                if output:
                    send_keys(output, pause=0.01)
                    output = ""
                vkey_hex = token.split()[1]
                try:
                    key = chr(int(vkey_hex, 16))
                    send_keys(key)
                except Exception:
                    sequence = None
                    replacements.clear()
                    raise ValueError(f"Invalid VKEY: {token}")
                continue
            elif token in MODIFIER_KEYS.union(MODIFIER_RELEASE):
                output += "{" + token + "}"
                continue
            elif token in SPECIAL_KEYS:
                output += "{" + token + "}"
                continue
            else:
                output += "{" + token + "}"
        else:
            output += sequence[i]
            i += 1

    if output:
        send_keys(output, pause=0.01)

    # Clear sensitive data from memory
    for key in list(replacements.keys()):
        replacements[key] = "\0" * len(replacements[key])
    replacements.clear()
    sequence = None


def use_KeePass_sequence(kp_entry):
    """
    Use KeePass entry to send autotype sequence to active window.
    """
    k = get_credentials(kp_entry, return_entry=True)
    replacements = {
        "{USERNAME}": k.username,
        "{PASSWORD}": k.password,
        "{URL}": k.url or "",
        "{NOTES}": k.notes or "",
        "{TITLE}": k.title or "",
    }

    if not k.autotype_sequence:
        # Clear sensitive fields before raising
        replacements["{PASSWORD}"] = "\0" * len(replacements["{PASSWORD}"])
        replacements.clear()
        raise ValueError("Autotype-sequence is missing in KeePass entry.")

    send_autotype_sequence(k.autotype_sequence, replacements)

    # Clear KeePass entry password from memory
    if hasattr(k, "password") and k.password:
        k.password = "\0" * len(k.password)
