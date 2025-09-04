#!/usr/bin/env python3
"""
This is a minimalistic demo of how to use keepassfunctions.

Author: Smorkster
GitHub: https://github.com/Smorkster/keepassfunctions
License: MIT
Version: 2.0
Created: 2025-08-11
"""

from keepassfunctions.keepassfunctions import KeePassFunctions

db_file = r'C:\Passwords.kdbx'

try:
    with KeePassFunctions(db_file, with_gui = False) as kp1:
        print(f'Antal poster: {kp1.get_entry_count()}')
except Exception as e:
    print(f'Error when accessing database file with context manager\n{e}')

try:
    kp2 = KeePassFunctions(db_file, with_gui = False)
    print(f'Antal poster: {kp2.get_entry_count()}')
except Exception as e:
    print(f'Error when accessing database file directly:\n{e}')
