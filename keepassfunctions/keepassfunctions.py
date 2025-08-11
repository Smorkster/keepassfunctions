import os
import sys
import time
import pykeepass

from pywinauto.application import Application
from pywinauto.findwindows import find_window
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
    Returns the password as a string.
    """
    entered_password = dynamic_input(
        title="KeePass Password",
        inputs=[ { 'label': 'Enter password to KeePass-database file', 'show': '*' } ]
    ).get( dictionary = True )
    
    keepass_password = list( entered_password.get( 'inputs', {}).values() )[ 0 ]

    if len( keepass_password ) == 0 or entered_password.get( 'button', None ) != 'OK':
        dynamic_input( "No password", "No password entered.\nExiting" )
        sys.exit()

    return keepass_password

# Load credentials from KeePass
def get_credentials( entry_title , return_entry = False , file = None , path = None ):
    """
    Get credential entry from KeePass database-file

    * entry_title - Name given to the entry to be retrieved
    * return_entry - Should the whole entry be returned, or only username and password
    * file - Name of the KeePass database file (default: 'Pwd_Db.kdbx')
    * path - Path to the KeePass database file (default: '~')
    """

    if file == None:
        file = 'Pwd_Db.kdbx'
    if path == None:
        path = '~'
    keepass_file = os.path.expanduser( os.sep.join( [ path, file ] ) )
    entered_password = _get_keepass_password()

    try:
        kp = pykeepass.PyKeePass( keepass_file, password = entered_password )
        pykeepass.PyKeePass( filename = '', )
    except pykeepass.exceptions.CredentialsError as e:
        dynamic_input( "Error when reading", f"Could not read KeePass-database file:\n{ e.args[0] }" )
        sys.exit()
    except FileNotFoundError as e:
        dynamic_input( "Error when reading", f"Could not find file:\n{ e.args[1] }" )
        sys.exit()
    except Exception as e:
        dynamic_input( "Error when reading", e.args[0] )
        sys.exit()

    entry = kp.find_entries( title = entry_title, first = True )
    if entry:
        if return_entry:
            return entry
        else:
            return entry.username, entry.password
    else:
        raise ValueError( f"Could not find entry with the given name '{ entry_title }'" )

def send_autotype_sequence( sequence: str, replacements: dict ):
    # Replace placeholders like {USERNAME}, {PASSWORD}, etc.
    for key, value in replacements.items():
        sequence = sequence.replace( key.upper(), value )

    i = 0
    output = ""
    while i < len( sequence ):
        if sequence[i] == '{':
            end = sequence.find( '}', i )
            if end == -1:
                raise ValueError( f"Unmatched curlybrace in sequence: { sequence[i:] }" )
            token = sequence[i + 1:end].strip().upper()
            i = end + 1

            # Handle {DELAY 1000}
            if token.startswith( "DELAY " ):
                if output:
                    send_keys( output, pause = 0.01 )
                    output = ""
                delay_ms = int( token.split()[1] )
                time.sleep( delay_ms / 1000 )
                continue

            # Handle {VKEY 0xXX}
            elif token.startswith( "VKEY " ):
                if output:
                    send_keys( output, pause = 0.01 )
                    output = ""
                vkey_hex = token.split()[1]
                try:
                    key = chr( int( vkey_hex, 16 ) )
                    send_keys( key )
                except Exception:
                    raise ValueError( f"Invalid VKEY: { token }" )
                continue

            # Handle modifier keys (toggle state)
            elif token in MODIFIER_KEYS.union( MODIFIER_RELEASE ):
                output += "{" + token + "}"
                continue

            # Handle special keys
            elif token in SPECIAL_KEYS:
                output += "{" + token + "}"
                continue

            # Default: send unknown token literally
            else:
                output += "{" + token + "}"
        else:
            output += sequence[i]
            i += 1

    if output:
        send_keys( output, pause = 0.01 )

def use_KeePass_sequence( kp_entry ):
    k = get_credentials( kp_entry, return_entry = True )
    replacements = {
        "{USERNAME}": k.username,
        "{PASSWORD}": k.password,
        "{URL}": k.url or "",
        "{NOTES}": k.notes or "",
        "{TITLE}": k.title or "",
    }

    if not k.autotype_sequence:
        raise ValueError( "Autotype-sequence is missing in KeePass entry." )
    send_autotype_sequence( k.autotype_sequence, replacements )
