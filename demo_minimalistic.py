#!/usr/bin/env python3
"""
Minimal usage example for the `keepassfunctions` package.

This script demonstrates the intended context-manager based usage by opening a
KeePass database and printing the number of entries. It also includes a second
example that tries to use `KeePassFunctions` without a context manager to show
how that access pattern fails under the current API.

Author: Smorkster
GitHub: https://github.com/Smorkster/keepassfunctions
License: MIT
Version: 2.0
Created: 2025-08-11
"""

from keepassfunctions.keepassfunctions import KeePassFunctions

db_file = r'C:\Passwords.kdbx'

try:
    with KeePassFunctions( db_path = db_file, with_gui = False ) as kp1:
        print( f'Number of posts: { kp1.get_entry_count() } ' )

except Exception as e:
    print( f'Error when accessing database file with context manager\n{ e }' )

###
# This demonstrates using without a contextmanager
###

try:
    kp2 = KeePassFunctions( db_path = db_file, with_gui = False )
    print( f'Antal poster: { kp2.get_entry_count() }' )

except Exception as e:
    print( f'Error when accessing database file directly:\n{ e }' )
