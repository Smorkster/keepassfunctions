"""
Context-managed helpers for opening a KeePass database safely.

This module wraps `pykeepass` behind a small, restricted API for password
prompting, exact-title entry lookup, entry counting, and KeePass-style
autotype execution. It also performs best-effort cleanup of sensitive values
after use.

Author: Smorkster
GitHub: https://github.com/Smorkster/keepassfunctions
License: MIT
Version: 2.1.0
Created: 2026-04-15
"""

import logging
import os
from types import TracebackType
import pykeepass
import pykeepass.exceptions
import sys
import time

from dynamicinputbox import ResultDict, ResultTuple, dynamic_inputbox
from getpass import getpass
from pykeepass import Entry, PyKeePass
from pywinauto.keyboard import send_keys
from typing import Any, Literal, Optional, overload

class SecureKeePassProxy:
    """ Restricted proxy around an open `PyKeePass` instance.

    Only a small whitelist of helper methods is exposed so callers cannot freely
    interact with the underlying database object.
    """


    def __init__( self, kp_instance: PyKeePass ) -> None:
        """ Store the wrapped database instance and configure the allowed operations

        Args:
            kp_instance (PyKeePass): The open KeePass database instance to wrap.
        """

        self._kp: PyKeePass = kp_instance
        self._allowed_operations: set[ str ] = {
            'find_entries_by_title',
            'get_entry_count',
            'validate_entry_exists'
        }


    def __enter__( self ) -> 'SecureKeePassProxy':
        """ Return the proxy itself for use in a `with` block

        Returns:
            SecureKeePassProxy: The current proxy instance.
        """

        return self


    def __exit__( self, exc_type: type[ BaseException ] | None, exc_val: BaseException | None, exc_tb: TracebackType | None ) -> None:
        """ No-op exit hook that leaves exception handling to the caller

        Args:
            exc_type (type[BaseException] | None): The exception type raised inside the
                `with` block, if any.
            exc_val (BaseException | None): The exception instance raised inside the
                `with` block, if any.
            exc_tb (TracebackType | None): The traceback associated with the exception,
                if any.
        """

        pass


    def __getattr__( self, name: str ) -> Any:
        """ Allow access only to whitelisted proxy methods.

        Args:
            name (str): The attribute name being requested.

        Returns:
            Any: The requested proxy method when access is allowed.

        Raises:
            AttributeError: If `name` is not one of the allowed proxy operations.
        """

        if name in self._allowed_operations:

            return getattr( self, name )

        raise AttributeError( f"Access to '{ name }' is restricted for security reasons. "
                           f"Use specific methods: { ', '.join( self._allowed_operations ) }" )


    def find_entries_by_title( self, title: str, first: bool = True ) -> list[ Entry ]:
        """ Look up entries by title and always return the result as a list.

        Args:
            title (str): The entry title to search for.
            first (bool): If True, return at most one match from the underlying
                `pykeepass` query.

        Returns:
            list[Entry]: A list of matching entries. The list is empty when no match is
            found.
        """

        ret = []
        found_entries = self._kp.find_entries( title = title, first = first )

        if found_entries is None:

            return ret

        try:
            ret.extend( found_entries )

        except:
            ret.append( found_entries )

        return ret


    def get_entry_count( self ) -> int:
        """ Return the number of entries without exposing the entry collection.

        Returns:
            int: The number of entries currently available in the open database.

        Raises:
            RuntimeError: If the wrapped database is not open.
        """

        if not self._kp:

            raise RuntimeError( "KeePass database is not open. Use within a context manager." )

        if self._kp.entries is None:

            return 0

        return len( self._kp.entries )


    def validate_entry_exists( self, title: str ) -> int:
        """ Count how many entries match a given title without returning them.

        Args:
            title (str): The entry title to validate.

        Returns:
            int: The number of matching entries, or `0` if no match is found.
        """

        if self._kp.entries is None:

            return 0


        found_entries: list | None = self._kp.find_entries( title = title, first = False )

        if found_entries is None:

            return 0

        ret = []
        ret.extend( found_entries )

        return len( ret )


class KeePassFunctions:
    """ Context-managed wrapper around `PyKeePass` with safer access patterns.

    The wrapper opens the database on entry, exposes a restricted proxy instead of
    the raw `PyKeePass` object, and provides helpers for credential lookup,
    autotype execution, and best-effort cleanup of sensitive data.
    """

    def __init__( self, db_path: str, with_gui: bool = False ) -> None:
        """ Initialize the wrapper without opening the database yet.

        Args:
            db_path (str): Path to the KeePass database file.
            with_gui (bool): If True, prompt for the database password with a GUI
                dialog. Otherwise, prompt in the console.
        """

        self._db_path: str = db_path
        self._with_gui: bool = with_gui
        self._contextmanager_used: bool = False

        self._kp: PyKeePass | None = None
        self.kp_password: bytearray | None = None
        self._sensitive_data_registry: set[ str ] = set()


    def __enter__( self ) -> 'KeePassFunctions':
        """ Open the KeePass database and return this wrapper instance.

        Returns:
            KeePassFunctions: The initialized wrapper instance.

        Raises:
            SystemExit: If the database path is invalid, credentials are missing, or
                the database cannot be opened.
        """

        self._contextmanager_used = True
        self._kp = self._open_keepass_db()

        return self


    def __exit__( self, exc_type: type[ BaseException ] | None, exc_val: BaseException | None, exc_tb: TracebackType | None ) -> None:
        """ Clear tracked sensitive data and release the open database reference

        Args:
            exc_type (type[BaseException] | None): The exception type raised inside the
                `with` block, if any.
            exc_val (BaseException | None): The exception instance raised inside the
                `with` block, if any.
            exc_tb (TracebackType | None): The traceback associated with the exception,
                if any.
        """

        self._contextmanager_used = False
        self._comprehensive_cleanup()


    def __setattr__( self, name: str, value: Any ) -> None:
        """ Block direct assignment to the public `kp` access path.

        Args:
            name (str): The attribute name being assigned.
            value (Any): The value to assign.

        Raises:
            AttributeError: If code attempts to assign directly to `kp`.
        """

        if name == 'kp' and hasattr( self, '_kp' ):

            raise AttributeError( "Direct assignment to KeePass object is not allowed." )

        super().__setattr__( name, value )


    SPECIAL_KEYS = {
        "ENTER", "TAB", "ESC", "ESCAPE", "BACKSPACE", "SPACE",
        "LEFT", "RIGHT", "UP", "DOWN", "DELETE", "INSERT",
        "HOME", "END", "PGUP", "PGDN", "F1", "F2", "F3", "F4",
        "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    }

    MODIFIER_KEYS = {"CTRL", "ALT", "SHIFT", "WIN"}
    MODIFIER_RELEASE = {"CTRLUP", "ALTUP", "SHIFTUP", "WINUP"}


    def _comprehensive_cleanup( self, error_msg: Optional[ str ] = None, exit_on_error: bool = False ) -> None:
        """ Perform best-effort cleanup of sensitive values and optional error handling.

        Args:
            error_msg (str | None): Optional error message to log and display.
            exit_on_error (bool): If True, terminate the process after cleanup.

        Raises:
            SystemExit: If `exit_on_error` is True.
        """

        cleanup_errors = []

        # Clear KeePass password
        if hasattr( self, 'kp_password' ) and self.kp_password is not None:
            try:
                self._secure_clear_data( self.kp_password )
                delattr( self, 'kp_password' )

            except Exception as e:
                cleanup_errors.append( f"Failed to clear KeePass password: { e }" )

        # Close KeePass database
        if hasattr( self, '_kp' ) and self._kp is not None:
            try:
                self._kp = None

            except Exception as e:
                cleanup_errors.append( f"Failed to close KeePass database: { e }" )

        # Clear any registered sensitive data
        for data_ref in list( self._sensitive_data_registry ):
            try:
                if hasattr( self, data_ref ):
                    data = getattr( self, data_ref )
                    self._secure_clear_data( data )

                    if hasattr( self, data_ref ):
                        delattr( self, data_ref )

            except Exception as e:
                cleanup_errors.append( f"Failed to clear { data_ref }: { e }" )

        self._sensitive_data_registry.clear()

        # Log cleanup errors if any
        if cleanup_errors:
            logging.warning( "Cleanup warnings: " + "; ".join( cleanup_errors ) )

        # Handle error message
        if error_msg:
            logging.error( error_msg )
            try:
                if self._with_gui:
                    dynamic_inputbox( title = 'Error', message = error_msg )

                else:
                    print( f"Error: { error_msg }" )

            except Exception as e:
                logging.error( f"Could not display error dialog: { e }" )

            if exit_on_error:
                sys.exit( 1 )


    def _get_keepass_password( self ) -> bytearray | None:
        """ Prompt for the database password and return it as a clearable bytearray.

        Returns:
            bytearray | None: The entered password encoded as UTF-8, or `None` if
            execution exits during error handling.

        Raises:
            SystemExit: If the user cancels the prompt or submits an empty password.
        """

        pw_str = None
        gui_value = ""

        try:
            if self._with_gui:
                d: dynamic_inputbox = dynamic_inputbox(
                    title = 'KeePass Password',
                    inputs=[ { 'label': 'Enter password to KeePass-database file', 'show': '*' } ]
                )
                d.show()
                entered_password: ResultDict | ResultTuple = d.get( dictionary = True )

                if isinstance( entered_password, dict ):
                    if entered_password.get( 'button', None ) != 'OK':

                        raise ValueError( 'No password entered' )

                    inputs: dict | str | None = entered_password.get( 'inputs', {} )

                    if isinstance( inputs, dict ):
                        gui_value = list( inputs.values() )[ 0 ]

                if isinstance( gui_value, str ):
                    pw_str = gui_value

                elif hasattr( gui_value, 'get' ):
                    raw_value = gui_value.get()

                    if isinstance( raw_value, bytes ):
                        pw_str = raw_value.decode()

                    else:
                        pw_str = str( raw_value )

                elif isinstance( gui_value, bytearray ):
                    pw_str = gui_value.decode()

                else:
                    pw_str = str( gui_value )

                if len( pw_str ) == 0:

                    raise ValueError( 'No password entered.' )

            else:
                pw_str = getpass( 'Enter password to KeePass-database file: ' )

                if not pw_str:
                    raise ValueError( 'No password entered.' )

            pw_bytes = bytearray( pw_str, 'utf-8' )

            return pw_bytes

        except ValueError as e:

            self._comprehensive_cleanup( error_msg = str( e ), exit_on_error = True )

        finally:
            if pw_str:
                self._secure_clear_data( pw_str )


    def _open_keepass_db( self ) -> PyKeePass | None:
        """ Validate the path, prompt for the password, and open the database.

        Returns:
            PyKeePass | None: The opened KeePass database instance, or `None` if
            execution exits during error handling.

        Raises:
            SystemExit: If the path is invalid, the password is missing, or the
                database cannot be opened.
        """

        try:
            if not self._validate_database_path():
                raise FileNotFoundError( 'Invalid database path.' )

            self.kp_password = self._get_keepass_password()
            self._register_sensitive_data( 'kp_password' )

            if not self.kp_password:

                raise pykeepass.exceptions.CredentialsError( 'No password entered. Stops execution' )

            kp: PyKeePass = PyKeePass( self._db_path, password = self.kp_password.decode() )
            self._secure_clear_data( self.kp_password )
            self.kp_password = None

            return kp

        except pykeepass.exceptions.CredentialsError as e:
            self._comprehensive_cleanup( f'Could not read KeePass-database file:\n{ e }', exit_on_error = True )

        except FileNotFoundError as e:
            self._comprehensive_cleanup( f'Could not find file:\n{ e }', exit_on_error = True )

        except Exception as e:
            self._comprehensive_cleanup( f'Unexpected error: { e }', exit_on_error = True )


    def _register_sensitive_data( self, data_ref: str ) -> None:
        """ Register an attribute name so its value can be cleared during cleanup

        Args:
            data_ref (str): The attribute name of the sensitive value to track.
        """

        self._sensitive_data_registry.add( data_ref )


    def _secure_clear_data( self, data: Any ) -> None:
        """ Best-effort wipe helper for known sensitive value types.

        Args:
            data (Any): The value to clear when possible. Supported cases include
                `bytearray`, `str`, `dict`, and objects with a `password` attribute.
        """

        try:
            if isinstance( data, bytearray ):
                data[ : ] = b"\0" * len( data )

            elif isinstance( data, str ):
                data = "\0" * len(data)

            elif isinstance( data, dict ):
                for key in list( data.keys() ):
                    if isinstance( data[ key ], str ):
                        data[ key ] = "\0" * len( data[ key ] )

                    elif isinstance( data[ key ], bytearray ):
                        data[ key ][ : ] = b"\0" * len( data[ key ] )

                data.clear()

            elif hasattr( data, 'password' ) and data.password:
                data.password = "\0" * len( data.password )

        except Exception as e:
            logging.warning( f"Could not securely clear data: { e }" )


    def _validate_database_path( self ) -> bool:
        """ Expand, normalize, and validate the configured database path.

        Returns:
            bool: True when the path exists and points to a file.

        Raises:
            FileNotFoundError: If the configured path does not exist or is not a file.
        """

        expanded_path = os.path.expanduser( self._db_path )
        absolute_path = os.path.abspath( expanded_path )
        normalized_path = os.path.normpath( absolute_path )

        # Check if the path exists and is a file
        if os.path.isfile( normalized_path ):
            self._db_path = normalized_path

            return True

        else:
            logging.error( f"Error: Database file does not exist or is not a file: { normalized_path }" )

            raise FileNotFoundError( f"Database file does not exist or is not a file: { normalized_path }" )


    @property
    def kp( self ) -> SecureKeePassProxy:
        """ Return a restricted proxy for the currently open KeePass database.

        Access to this property is allowed only while the wrapper is inside an active
        context manager.

        Returns:
            SecureKeePassProxy: A proxy exposing only allowed database operations.

        Raises:
            RuntimeError: If the wrapper is used outside a `with` block or if the
                database has not been opened.
        """

        if not self._contextmanager_used:

            raise RuntimeError( "KeePassFunctions must be used within a context manager (a 'with' statement)." )

        if self._kp is None:

            raise RuntimeError( "KeePass database is not open. Use within a context manager." )

        return SecureKeePassProxy( self._kp )


    def entry_exists( self, title: str ) -> bool:
        """ Return whether at least one entry matches the given title.

        Args:
            title (str): The entry title to check.

        Returns:
            bool: True if at least one matching entry exists, otherwise False.

        Raises:
            RuntimeError: If called outside an active context manager or before the
                database has been opened.
        """

        if not self._contextmanager_used:

            raise RuntimeError( "KeePassFunctions must be used within a context manager (a 'with' statement)." )

        if not self._kp:
            raise RuntimeError( "KeePass database is not open. Use within a context manager." )

        return bool( self.kp.validate_entry_exists( title ) )


    @overload
    def get_credentials( self, entry_title: str, return_entry: Literal[ True ] ) -> Entry:
        """ Return the full `Entry` when `return_entry` is `True`

        Args:
            entry_title (str): The entry title to look up.
            return_entry (Literal[ True ]): True, return the full `Entry` object
        """

        pass


    @overload
    def get_credentials( self, entry_title: str, return_entry: Literal[ False ] = False ) -> tuple[ str | None, str | None ]:
        """ Return `(username, password)` when `return_entry` is `False`

        Args:
            entry_title (str): The entry title to look up.
            return_entry (Literal[ False ]): False, return a `(username, password)` tuple
        """

        pass


    def get_credentials( self, entry_title: str, return_entry: bool = False ) -> Entry | tuple[ str | None, str | None ]:
        """ Return credentials or the first matching entry for a given title.

        Args:
            entry_title (str): The entry title to look up.
            return_entry (bool): If True, return the full `Entry` object. Otherwise,
                return a `(username, password)` tuple.

        Returns:
            Entry | tuple[str | None, str | None]: The first matching entry or its
            username/password pair.

        Raises:
            RuntimeError: If called outside an active context manager.
            ValueError: If no matching entry is found.
        """

        if not self._contextmanager_used:

            raise RuntimeError( "KeePassFunctions must be used within a context manager (a 'with' statement)." )

        with self.kp as kp_instance:
            found_entries = kp_instance.find_entries_by_title( entry_title, first = True )
            if len( found_entries ) == 0:

                raise ValueError( 'No entry found' )

            else:
                entry = found_entries[ 0 ]

        if entry:
            if return_entry:

                return entry

            else:

                return entry.username, entry.password

        else:

            raise ValueError( f'Could not find entry with the given name \'{ entry_title }\'' )


    def get_entry_count( self ) -> int:
        """ Return the total number of entries in the open database.

        Returns:
            int: The number of entries in the database.

        Raises:
            RuntimeError: If called outside an active context manager.
        """

        if not self._contextmanager_used:

            raise RuntimeError( 'KeePassFunctions must be used within a context manager (a \'with\' statement).' )

        with self.kp as kp_instance:

            return kp_instance.get_entry_count()


    def send_autotype_sequence( self, sequence: str, replacements: dict[ str, str ] ) -> None:
        """ Resolve placeholders in an AutoType sequence and send it to the active window.

        Args:
            sequence (str): The KeePass-style AutoType sequence to parse.
            replacements (dict[str, str]): Mapping of placeholders such as
                `{USERNAME}` and `{PASSWORD}` to their replacement values.

        Raises:
            RuntimeError: If called outside an active context manager.
            ValueError: If the sequence contains unmatched braces or an invalid
                `VKEY` token.
        """

        if not self._contextmanager_used:

            raise RuntimeError( 'KeePassFunctions must be used within a context manager (a \'with\' statement).' )

        try:
            for key, value in replacements.items():
                sequence = sequence.replace( key.upper(), value )

            i = 0
            output = ""

            while i < len( sequence ):
                if sequence[ i ] == '{':
                    end = sequence.find( '}', i )

                    if end == -1:

                        raise ValueError( 'Unmatched curly brace in sequence' )

                    token = sequence[ i + 1:end ].strip().upper()
                    i = end + 1

                    if token.startswith( 'DELAY ' ):

                        if output:
                            send_keys( output, pause = 0.01 )
                            output = ""

                        delay_ms = int( token.split()[ 1 ] )
                        time.sleep( delay_ms / 1000 )

                        continue

                    elif token.startswith( 'VKEY ' ):
                        if output:
                            send_keys( output, pause = 0.01 )
                            output = ""

                        vkey_hex = token.split()[ 1 ]

                        try:
                            key = chr( int( vkey_hex, 16 ) )
                            send_keys( key )

                        except Exception:

                            raise ValueError( f'Invalid VKEY: { token }' )

                        continue

                    elif token in self.MODIFIER_KEYS.union( self.MODIFIER_RELEASE ):
                        output += '{' + token + '}'

                        continue

                    elif token in self.SPECIAL_KEYS:
                        output += '{' + token + '}'

                        continue

                    else:
                        output += '{' + token + '}'

                else:
                    output += sequence[ i ]
                    i += 1

            if output:
                send_keys( output, pause = 0.01 )

        finally:
            self._secure_clear_data( replacements )


    def use_KeePass_sequence( self, kp_entry: str ) -> None:
        """ Load an entry's AutoType sequence and send it to the active window.

        Args:
            kp_entry (str): The title of the entry whose AutoType sequence should be
                used.

        Raises:
            RuntimeError: If called outside an active context manager.
            ValueError: If the matching entry is missing or has no AutoType sequence,
                or if the sequence is invalid.
            Exception: Propagates unexpected lookup or send errors.
        """

        if not self._contextmanager_used:

            raise RuntimeError( 'KeePassFunctions must be used within a context manager (a \'with\' statement).' )

        k: Entry | tuple = ()
        replacements = {}

        try:
            k = self.get_credentials( entry_title = kp_entry, return_entry = True )

            if isinstance( k, Entry ):
                if not k.autotype_sequence:
                    raise ValueError( 'Autotype-sequence is missing in KeePass entry.' )

                replacements = {
                    '{USERNAME}': k.username or '',
                    '{PASSWORD}': k.password or '',
                    '{URL}': k.url or '',
                    '{NOTES}': k.notes or '',
                    '{TITLE}': k.title or '',
                }

                self.send_autotype_sequence( k.autotype_sequence, replacements )

        except ValueError as e:
            logging.error( e.args[ 0 ] )

            raise e

        except Exception as e:
            logging.error( f'Unexpected error in use_KeePass_sequence: { e }' )

            raise e

        finally:
            self._secure_clear_data( replacements )
            self._secure_clear_data( k )


    def validate_autotype_available( self, entry_title: str ) -> bool:
        """ Return whether a matching entry has a non-empty AutoType sequence.

        Args:
            entry_title (str): The title of the entry to inspect.

        Returns:
            bool: True if the first matching entry exposes an AutoType sequence,
            otherwise False.

        Raises:
            RuntimeError: If called outside an active context manager or before the
                database has been opened.
        """

        if not self._contextmanager_used:

            raise RuntimeError( 'KeePassFunctions must be used within a context manager (a \'with\' statement).' )

        if not self._kp:

            raise RuntimeError( 'KeePass database is not open. Use within a context manager.' )

        with self.kp as kp_instance:
            found_entries = kp_instance.find_entries_by_title( entry_title, first = True )

        if not found_entries:

            return False

        entry: Entry = found_entries[ 0 ]

        return bool( entry.autotype_sequence )
