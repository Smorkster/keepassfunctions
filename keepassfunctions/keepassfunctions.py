"""
A wrapper for retrieving entries from a KeePass-database.
This module provides a secure and minimalistic interface to interact with KeePass databases,
focusing on security and ease of use.

Author: Smorkster
GitHub: https://github.com/Smorkster/keepassfunctions
License: MIT
Version: 2.0
Created: 2025-08-11
"""

import logging
import os
import pykeepass
import sys
import time

from dynamicinputbox import dynamic_inputbox as dynamic_input
from getpass import getpass
from pywinauto.keyboard import send_keys
from typing import Any, Optional

class SecureKeePassProxy:
    """
    A secure proxy that wraps the PyKeePass object and restricts access to sensitive operations.
    Only allows specific, controlled access patterns.
    """
    def __init__(self, kp_instance):
        self._kp = kp_instance
        self._allowed_operations = {
            'find_entries_by_title',
            'get_entry_count',
            'validate_entry_exists'
        }

    def __enter__(self):
        """Proxy enter method for context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Proxy exit method for context manager protocol."""
        pass

    def __getattr__(self, name):
        """Block all other attribute access.

        Args:
            name (str): The attribute name being accessed.
        """
        if name in self._allowed_operations:
            return getattr(self, name)
        raise AttributeError(f"Access to '{name}' is restricted for security reasons. "
                           f"Use specific methods: {', '.join(self._allowed_operations)}")

    def find_entries_by_title(self, title: str, first: bool = True):
        """Find entries by exact title match only.

        Args:
            title (str): Entry title to search for
            first (bool): If true, return only the first match
        """
        return self._kp.find_entries(title=title, first=first)

    def get_entry_count(self) -> int:
        """
        Get the total number of entries in the database without exposing them.

        Returns:
            Number of entries in the database
        """
        if not self._kp:
            raise RuntimeError("KeePass database is not open. Use within a context manager.")

        return len(self._kp.entries)

    def validate_entry_exists(self, title: str) -> int:
        """Check if an entry exists without returning it.

        Args:
            title: Verify that an entry with this title exists

        Returns:
            Number of entries with the given title (0 or more)
        """
        ret = []
        ret.extend(self._kp.find_entries(title=title, first=False))
        return len(ret)

class KeePassFunctions:
    def __init__(self, db_path: str, with_gui: bool = False):
        self._db_path = db_path
        self._with_gui = with_gui
        self._contextmanager_used = False

        self._kp = None  # Private attribute
        self.kp_password = None
        self._sensitive_data_registry = set()

    def __enter__(self):
        """Context manager entry, open the KeePass database.

        Returns:
            KeePassFunctions: Wrapper-instance to work with
        """
        self._contextmanager_used = True
        self._kp = self._open_keepass_db()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point, close the KeePass database and clear all sensitive data."""
        self._contextmanager_used = False
        self._comprehensive_cleanup()

    def __setattr__(self, name, value):
        """Prevent direct assignment to the internal KeePass object.

        Args:
            name (str): The attribute name being set.
            value: The value to set the attribute to.
        """
        if name == 'kp' and hasattr(self, '_kp'):
            raise AttributeError("Direct assignment to KeePass object is not allowed.")
        super().__setattr__(name, value)

    SPECIAL_KEYS = {
        "ENTER", "TAB", "ESC", "ESCAPE", "BACKSPACE", "SPACE",
        "LEFT", "RIGHT", "UP", "DOWN", "DELETE", "INSERT",
        "HOME", "END", "PGUP", "PGDN", "F1", "F2", "F3", "F4",
        "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    }

    MODIFIER_KEYS = {"CTRL", "ALT", "SHIFT", "WIN"}
    MODIFIER_RELEASE = {"CTRLUP", "ALTUP", "SHIFTUP", "WINUP"}

    def _comprehensive_cleanup(self, error_msg: Optional[str] = None, exit_on_error: bool = False) -> None:
        """
        Comprehensive cleanup method that handles all sensitive data and error scenarios.

        Args:
            error_msg (str, optional): Error message to log and display
            exit_on_error (bool): Whether to exit the program after cleanup
        """
        cleanup_errors = []

        # Clear KeePass password
        if hasattr(self, 'kp_password') and self.kp_password is not None:
            try:
                self._secure_clear_data(self.kp_password)
                delattr(self, 'kp_password')
            except Exception as e:
                cleanup_errors.append(f"Failed to clear KeePass password: {e}")

        # Close KeePass database
        if hasattr(self, '_kp') and self._kp is not None:
            try:
                self._kp = None
            except Exception as e:
                cleanup_errors.append(f"Failed to close KeePass database: {e}")

        # Clear any registered sensitive data
        for data_ref in list(self._sensitive_data_registry):
            try:
                if hasattr(self, data_ref):
                    data = getattr(self, data_ref)
                    self._secure_clear_data(data)
                    if hasattr(self, data_ref):
                        delattr(self, data_ref)
            except Exception as e:
                cleanup_errors.append(f"Failed to clear {data_ref}: {e}")

        self._sensitive_data_registry.clear()

        # Log cleanup errors if any
        if cleanup_errors:
            logging.warning("Cleanup warnings: " + "; ".join(cleanup_errors))

        # Handle error message
        if error_msg:
            logging.error(error_msg)
            try:
                if self._with_gui:
                    dynamic_input('Error', error_msg)
                else:
                    print(f"Error: {error_msg}")
            except Exception as e:
                logging.error(f"Could not display error dialog: {e}")

            if exit_on_error:
                sys.exit(1)

    def _get_keepass_password(self) -> bytearray:
        """
        Prompt the user for the KeePass database password.

        Returns:
            Password as a bytearray so it can be securely cleared.
        """
        pw_str = None
        try:
            if self._with_gui:
                entered_password = dynamic_input(
                    title='KeePass Password',
                    inputs=[{'label': 'Enter password to KeePass-database file', 'show': '*'}]
                ).get(dictionary=True)

                pw_str = list(entered_password.get('inputs', {}).values())[0]
                if len(pw_str) == 0 or entered_password.get('button', None) != 'OK':
                    self._comprehensive_cleanup('No password entered.', exit_on_error=True)
            else:
                pw_str = getpass('Enter password to KeePass-database file: ')
                if not pw_str:
                    self._comprehensive_cleanup('No password entered.', exit_on_error=True)

            pw_bytes = bytearray(pw_str, 'utf-8')
            return pw_bytes
        finally:
            if pw_str:
                self._secure_clear_data(pw_str)

    def _open_keepass_db(self) -> pykeepass.PyKeePass:
        """
        Open the KeePass database and return as an object.

        Args:
            keepass_file (str): Path to the KeePass database file.

        Returns:
            pykeepass.PyKeePass: The opened KeePass database object.
        """

        if not self._validate_database_path():
            self._comprehensive_cleanup('Invalid database path.', exit_on_error=True)

        self.kp_password = self._get_keepass_password()
        self._register_sensitive_data('kp_password')

        if not self.kp_password:
            self._comprehensive_cleanup('No password entered. Stops execution.', exit_on_error=True)

        try:
            kp = pykeepass.PyKeePass(self._db_path, password=self.kp_password.decode())
            self._secure_clear_data(self.kp_password)
            self.kp_password = None
            return kp
        except pykeepass.exceptions.CredentialsError as e:
            self._comprehensive_cleanup(f'Could not read KeePass-database file:\n{e.args[0]}', exit_on_error=True)
        except FileNotFoundError as e:
            self._comprehensive_cleanup(f'Could not find file:\n{e.args[1]}', exit_on_error=True)
        except Exception as e:
            self._comprehensive_cleanup(f'Unexpected error: {e}', exit_on_error=True)

    def _register_sensitive_data(self, data_ref: str) -> None:
        """Register sensitive data for cleanup tracking.

        Args:
            data_ref (str): The attribute name of the sensitive data to register.
        """
        self._sensitive_data_registry.add(data_ref)

    def _secure_clear_data(self, data: Any) -> None:
        """
        Securely clear sensitive data from memory.

        Args:
            data: The data to clear (str, bytearray, dict, or any object with clearable attributes)
        """
        try:
            if isinstance(data, bytearray):
                data[:] = b"\0" * len(data)
            elif isinstance(data, str):
                data = "\0" * len(data)
            elif isinstance(data, dict):
                for key in list(data.keys()):
                    if isinstance(data[key], str):
                        data[key] = "\0" * len(data[key])
                    elif isinstance(data[key], bytearray):
                        data[key][:] = b"\0" * len(data[key])
                data.clear()
            elif hasattr(data, 'password') and data.password:
                data.password = "\0" * len(data.password)
        except Exception as e:
            logging.warning(f"Could not securely clear data: {e}")

    def _validate_database_path(self) -> bool:
        """
        Validate that the database path exists and is a file.
        Handles both absolute and relative paths, including user paths (e.g., ~).

        Returns:
            bool: True if the path is valid, otherwise exits with an error.
        """

        expanded_path = os.path.expanduser(self._db_path)
        absolute_path = os.path.abspath(expanded_path)
        normalized_path = os.path.normpath(absolute_path)

        # Check if the path exists and is a file
        if os.path.isfile(normalized_path):
            self._db_path = normalized_path
            return True
        else:
            logging.error(f"Error: Database file does not exist or is not a file: {normalized_path}")
            raise FileNotFoundError(f"Database file does not exist or is not a file: {normalized_path}")

    @property
    def kp(self):
        """
        Controlled access to KeePass database through secure proxy.
        This prevents direct access to all entries while allowing specific operations.
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")
        if self._kp is None:
            raise RuntimeError("KeePass database is not open. Use within a context manager.")
        return SecureKeePassProxy(self._kp)

    def entry_exists(self, title: str) -> bool:
        """
        Check if an entry with the given title exists.

        Args:
            title: Entry title to check

        Returns:
            True if entry exists
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")
        if not self._kp:
            raise RuntimeError("KeePass database is not open. Use within a context manager.")

        return self.kp.validate_entry_exists(title)

    def get_credentials(self, entry_title: str, return_entry: bool = False) -> tuple:
        """
        Get KeePass database entry by exact title match.

        Args:
            entry_title (str): Title of the entry
            return_entry (bool): Should the whole entry be returned

        Returns:
            Tuple of (username, password) or the whole entry if return_entry is True
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")

        with self.kp as kp_instance:
            entry = kp_instance.find_entries_by_title(entry_title, first=True)

        if entry:
            if return_entry:
                return entry
            else:
                return entry.username, entry.password
        else:
            raise ValueError(f'Could not find entry with the given name \'{entry_title}\'')

    def get_entry_count(self) -> int:
        """
        Get total number of entries

        Returns:
            Number of entries in the database
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")

        with self.kp as kp_instance:
            return kp_instance.get_entry_count()

    def send_autotype_sequence(self, sequence: str, replacements: dict) -> None:
        """
        Send an autotype sequence to the active window, replacing placeholders with actual values.

        Args:
            sequence (str): The autotype sequence containing placeholders
            replacements (dict): A dictionary mapping placeholders to their actual values
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")

        try:
            for key, value in replacements.items():
                sequence = sequence.replace(key.upper(), value)

            i = 0
            output = ""
            while i < len(sequence):
                if sequence[i] == '{':
                    end = sequence.find('}', i)
                    if end == -1:
                        raise ValueError("Unmatched curly brace in sequence")

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
                            raise ValueError(f"Invalid VKEY: {token}")
                        continue
                    elif token in self.MODIFIER_KEYS.union(self.MODIFIER_RELEASE):
                        output += "{" + token + "}"
                        continue
                    elif token in self.SPECIAL_KEYS:
                        output += "{" + token + "}"
                        continue
                    else:
                        output += "{" + token + "}"
                else:
                    output += sequence[i]
                    i += 1

            if output:
                send_keys(output, pause=0.01)

        finally:
            self._secure_clear_data(replacements)
            sequence = None

    def use_KeePass_sequence(self, kp_entry: str) -> None:
        """
        Use KeePass entry to send autotype sequence to active window.

        Args:
            kp_entry: Title of the entry
        
        Raises:
            ValueError: If entry is not found or autotype sequence is missing
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")

        k = None
        replacements = {}

        try:
            k = self.get_credentials(kp_entry, return_entry=True)
            
            if not k.autotype_sequence:
                raise ValueError('Autotype-sequence is missing in KeePass entry.')

            replacements = {
                '{USERNAME}': k.username or '',
                '{PASSWORD}': k.password or '',
                '{URL}': k.url or '',
                '{NOTES}': k.notes or '',
                '{TITLE}': k.title or '',
            }

            self.send_autotype_sequence(k.autotype_sequence, replacements)

        except ValueError as e:
            logging.error(e.args[0])
            raise e
        except Exception as e:
            logging.error(f"Unexpected error in use_KeePass_sequence: {e}")
            raise e
        finally:
            self._secure_clear_data(replacements)
            if k and hasattr(k, 'password'):
                self._secure_clear_data(k)

    def validate_autotype_available(self, entry_title: str) -> bool:
        """
        Check if an entry has an autotype sequence without exposing the entry.

        Args:
            entry_title: Title of the entry to check

        Returns:
            True if entry exists and has autotype sequence

        Raises:
            RuntimeError: If not used within a context manager or database is not open
            ValueError: If entry is not found
        """
        if not self._contextmanager_used:
            raise RuntimeError("KeePassFunctions must be used within a context manager (with statement).")

        if not self._kp:
            raise RuntimeError("KeePass database is not open. Use within a context manager.")

        entry = self._kp.find_entries(title=entry_title, first=True)
        return bool(entry and entry.autotype_sequence)

    # Block dangerous methods that could expose too much data
#    def __getattribute__(self, name):
#        # Block direct access to potentially dangerous methods/attributes
#        blocked_attributes = {
#            '_kp',  # Direct access to internal KeePass object
#        }

#        if name in blocked_attributes and name != '_KeePassFunctions__init__':
#            raise AttributeError(f"Direct access to '{name}' is restricted for security reasons.")

#        return super().__getattribute__(name)
