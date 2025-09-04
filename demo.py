#!/usr/bin/env python3
"""
KeePass Functions Demo Script

This script demonstrates various ways to use the KeePassFunctions class from the terminal.
It supports both command-line arguments and interactive mode, with options for GUI or console input.

Usage examples:
    python demo.py --help
    python demo.py --db ~/passwords.kdbx --entry "My Website" --get-credentials
    python demo.py --db ~/passwords.kdbx --entry "My Website" --get-credentials --gui
    python demo.py --db ~/passwords.kdbx --entry "My Website" --autotype
    python demo.py --db ~/passwords.kdbx --list-entries --gui
    python demo.py --interactive
    python demo.py --interactive --gui

Author: Smorkster
GitHub: https://github.com/Smorkster/keepassfunctions
License: MIT
Version: 2.0
Created: 2025-08-11
"""

import argparse
import logging
import sys

try:
    from keepassfunctions.keepassfunctions import KeePassFunctions
except ImportError:
    print("Error: Could not import KeePassFunctions. Make sure the module is in your Python path.")
    sys.exit(1)

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_full_entry_demo(db_path, entry_title, with_gui=False):
    """Demo: Get full entry details for a specific entry."""
    input_method = "GUI" if with_gui else "console"
    print(f"Getting full entry details for: '{entry_title}' (using {input_method} input)")

    try:
        with KeePassFunctions(db_path, with_gui=with_gui) as kp:
            entry = kp.get_credentials(entry_title, return_entry=True)
            print(f"\n📋 Entry Details:")
            print(f"   Title: {entry.title}")
            print(f"   Username: {entry.username or 'N/A'}")
            print(f"   Password: {'*' * len(entry.password) if entry.password else 'N/A'}")
            print(f"   URL: {entry.url or 'N/A'}")
            print(f"   Notes: {entry.notes[:100] + '...' if entry.notes and len(entry.notes) > 100 else entry.notes or 'N/A'}")
            print(f"   Has Autotype: {'Yes' if entry.autotype_sequence else 'No'}")
            if entry.autotype_sequence:
                print(f"   Autotype Sequence: {entry.autotype_sequence}")

    except ValueError as e:
        print(f"❌ Entry not found: {e}")
    except Exception as e:
        print(f"❌ Error getting entry details: {e}")

def interactive_mode(with_gui=False):
    """Interactive mode for exploring KeePass database."""
    input_method = "GUI" if with_gui else "console"
    print(f"\n=== KeePass Interactive Mode (using {input_method} input) ===")

    # Get database path
    #db_path = input("Enter path to KeePass database file: ").strip()
    # TODO Remove
    db_path = '~\\Losenordslista_SD_Personlig.kdbx'
    if not db_path:
        print("No database path provided. Exiting.")
        return

    try:
        with KeePassFunctions(db_path, with_gui=with_gui) as kp:
            while True:
                print("\n" + "="*50)
                print("Available actions:")
                print("1. Search entries")
                print("2. Get credentials")
                print("3. Get full entry details")
                print("4. Execute autotype sequence")
                print("5. Compare GUI vs console")
                print("6. Exit")
                choice = input("\nEnter your choice (1-6): ").strip()

                # Search entry demo
                if choice == '1':
                    search_term = input("Enter search term: ").strip()
                    if search_term:
                        entries = kp.entry_exists(search_term)
                        if entries:
                            print(f"\n'{search_term}' was found as title for > {entries} < entries.")
                        else:
                            print(f"No entries found containing '{search_term}'.")

                # Get username and password demo
                elif choice == '2':
                    entry_title = input("Enter entry title: ").strip()
                    if entry_title:
                        try:
                            username, password = kp.get_credentials(entry_title)
                            print(f"Username: {username}")
                            print(f"Password: {'*' * len(password) if password else 'N/A'}")
                        except ValueError as e:
                            print(f"Error: {e}")

                # Get entry demo
                elif choice == '3':
                    entry_title = input("Enter entry title: ").strip()
                    if entry_title:
                        try:
                            entry = kp.get_credentials(entry_title, return_entry=True)
                            print(f"\nEntry Details:")
                            print(f"Title: {entry.title}")
                            print(f"Username: {entry.username}")
                            print(f"Password: {'*' * len(entry.password) if entry.password else 'N/A'}")
                            print(f"URL: {entry.url or 'N/A'}")
                            print(f"Notes: {entry.notes or 'N/A'}")
                            print(f"Autotype Sequence: {entry.autotype_sequence or 'N/A'}")
                        except ValueError as e:
                            print(f"Error: {e}")

                # Test autotype demo
                elif choice == '4':
                    entry_title = input("Enter entry title for autotype: ").strip()
                    if entry_title:
                        print("Make sure the target window is active!")
                        input("Press Enter when ready...")
                        try:
                            kp.use_KeePass_sequence(entry_title)
                            print("Autotype sequence executed!")
                        except ValueError as e:
                            print(f"Error: {e}")
                        except Exception as e:
                            print(f"Error executing autotype: {e}")

                elif choice == '5':
                    gui_comparison_demo()

                # Exit demo
                elif choice == '6':
                    print("Exiting interactive mode...")
                    break

                else:
                    print("Invalid choice. Please enter 1-6.")

    except Exception as e:
        print(f"Error in interactive mode: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="KeePass Functions Demo Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --db ~/passwords.kdbx --entry "My Website" --get-credentials
  %(prog)s --db ~/passwords.kdbx --entry "My Website" --get-credentials --gui
  %(prog)s --db ~/passwords.kdbx --entry "My Website" --autotype
  %(prog)s --db ~/passwords.kdbx --search "github"
  %(prog)s --interactive
  %(prog)s --interactive --gui
        """
    )

    # Database and GUI options
    parser.add_argument('--db', '--database', type=str, 
                       help='Path to KeePass database file')
    parser.add_argument('--gui', action='store_true', 
                       help='Use GUI for password input (default: console)')

    # Entry selection
    parser.add_argument('--entry', type=str, 
                       help='Entry title to work with')
    parser.add_argument('--search', type=str, 
                       help='Search term for finding entries')

    # Actions
    parser.add_argument('--get-credentials', action='store_true', 
                       help='Get username and password for specified entry')
    parser.add_argument('--get-full-entry', action='store_true', 
                       help='Get full entry details for specified entry')
    parser.add_argument('--autotype', action='store_true', 
                       help='Execute autotype sequence for specified entry')

    # Modes
    parser.add_argument('--interactive', action='store_true', 
                       help='Run in interactive mode')

    # Logging
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Interactive mode
    if args.interactive:
        interactive_mode(with_gui=args.gui)
        return

    # Validate required arguments for non-interactive mode
    if not args.db:
        print("Error: --db is required for non-interactive mode")
        print("Use --interactive for interactive mode or --help for usage information")
        sys.exit(1)

    # Validate database path
    db_path = args.db

    # Execute based on action
    action_count = sum([
        args.get_credentials,
        args.get_full_entry,
        args.autotype,
        args.list_entries,
        bool(args.search)
    ])

    if action_count == 0:
        print("Error: No action specified. Use --help for available actions.")
        sys.exit(1)
    elif action_count > 1:
        print("Error: Only one action can be specified at a time.")
        sys.exit(1)

    # Execute the requested action
    try:
        if args.search:
            search_entries_demo(db_path, args.search, with_gui=args.gui)

        elif args.get_credentials:
            if not args.entry:
                print("Error: --entry is required for --get-credentials")
                sys.exit(1)
            get_credentials_demo(db_path, args.entry, with_gui=args.gui)

        elif args.get_full_entry:
            if not args.entry:
                print("Error: --entry is required for --get-full-entry")
                sys.exit(1)
            get_full_entry_demo(db_path, args.entry, with_gui=args.gui)

        elif args.autotype:
            if not args.entry:
                print("Error: --entry is required for --autotype")
                sys.exit(1)
            autotype_demo(db_path, args.entry, with_gui=args.gui)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def get_credentials_demo(db_path, entry_title, with_gui=False):
    """Demo: Get credentials for a specific entry."""
    input_method = "GUI" if with_gui else "console"
    print(f"Getting credentials for entry: '{entry_title}' (using {input_method} input)")

    try:
        with KeePassFunctions(db_path, with_gui=with_gui) as kp:
            username, password = kp.get_credentials(entry_title)
            print(f"✓ Username: {username}")
            print(f"✓ Password: {'*' * len(password) if password else 'N/A'}")

    except ValueError as e:
        print(f"❌ Entry not found: {e}")
    except Exception as e:
        print(f"❌ Error getting credentials: {e}")

def autotype_demo(db_path, entry_title, with_gui=False):
    """Demo: Use autotype sequence for a specific entry."""
    input_method = "GUI" if with_gui else "console"
    print(f"Executing autotype sequence for entry: '{entry_title}' (using {input_method} input)")
    print("⚠️  Make sure the target application window is active!")

    # Give user time to switch to target window
    import time
    for i in range(5, 0, -1):
        print(f"⏱️  Starting autotype in {i} seconds...", end='\r')
        time.sleep(1)
    print("\n🚀 Executing autotype sequence...")

    try:
        with KeePassFunctions(db_path, with_gui=with_gui) as kp:
            kp.use_KeePass_sequence(entry_title)
            print("✓ Autotype sequence completed successfully!")

    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error executing autotype: {e}")

def search_entries_demo(db_path, search_term, with_gui=False):
    """Demo: Search for entries containing a specific term."""
    input_method = "GUI" if with_gui else "console"
    print(f"🔍 Searching for entries containing '{search_term}' (using {input_method} input):")

    try:
        with KeePassFunctions(db_path, with_gui=with_gui) as kp:
            # Search in title, username, and URL
            entries = kp.search_entries(title=search_term, max_results=10)

            # Remove duplicates
            unique_entries = list({entry.uuid: entry for entry in entries}.values())

            if not unique_entries:
                print(f"❌ No entries found containing '{search_term}'.")
                return

            print(f"\n✓ Found {len(unique_entries)} matching entries:")
            print("-" * 60)

            for i, entry in enumerate(unique_entries, 1):
                print(f"{i}. 📝 {entry.title}")
                if entry.username:
                    print(f"   👤 Username: {entry.username}")
                if entry.url:
                    print(f"   🌐 URL: {entry.url}")
                print()

    except Exception as e:
        print(f"❌ Error searching entries: {e}")

def gui_comparison_demo():
    """Demo: Show the difference between GUI and console input."""
    print("\n🔄 GUI vs Console Input Comparison Demo")
    print("="*50)

    db_path = input("Enter path to KeePass database file for comparison: ").strip()
    if not db_path:
        print("No database path provided. Skipping comparison demo.")
        return

    try:
        print("\n1️⃣  Testing with CONSOLE input:")
        print("   You'll be prompted for password in the terminal")
        try:
            with KeePassFunctions(db_path, with_gui=False) as kp:
                entries_count = kp.get_entry_count()
                print(f"   ✓ Successfully opened database with > {entries_count} < entries")
                logging.log(f"with KeePassFunctions(db_path, with_gui=False) as kp:\n\tentries_count = kp.get_entry_count()")
        except Exception as e:
            print(f"   ❌ Console input failed: {e}")
            return

        print("\n2️⃣  Testing with GUI input:")
        print("   You'll see a GUI dialog for password input")
        try:
            with KeePassFunctions(db_path, with_gui=True) as kp:
                entries_count = kp.get_entry_count()
                print(f"   ✓ Successfully opened database with > {entries_count} < entries")
                logging.log(f"with KeePassFunctions(db_path, with_gui=True) as kp:\n\tentries_count = kp.get_entry_count()")
        except Exception as e:
            print(f"   ❌ GUI input failed: {e}")

        print("\n🎉 Comparison complete! Both input methods work.")

    except Exception as e:
        print(f"❌ Comparison demo failed: {e}")

if __name__ == "__main__":
    print("🔐 KeePass Functions Demo Script")
    print("="*40)

    # Check if no arguments provided, show help
    if len(sys.argv) == 1:
        print("No arguments provided. Here are some quick examples:")
        print("\nQuick start options:")
        print("  python demo.py --interactive           # Interactive mode with console input")
        print("  python demo.py --interactive --gui     # Interactive mode with GUI input")
        print("  python demo.py --help                  # Show all options")
        print("\nFor GUI vs Console comparison:")
        print("  python demo.py --compare")
        print()

        choice = input("Would you like to start in interactive mode? (y/N): ").strip().lower()
        if choice in ('y', 'yes'):
            gui_choice = input("Use GUI for password input? (y/N): ").strip().lower()
            use_gui = gui_choice in ('y', 'yes')
            interactive_mode(with_gui=use_gui)
        else:
            print("Run with --help for full usage information.")
        sys.exit(0)

    # Handle special comparison mode
    if len(sys.argv) == 2 and sys.argv[1] == '--compare':
        gui_comparison_demo()
        sys.exit(0)

    # Normal argument parsing
    main()
