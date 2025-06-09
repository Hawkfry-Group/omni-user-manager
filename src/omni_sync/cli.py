"""
Omni User Manager CLI
-------------------
Command-line interface for Omni User Manager.

A tool for synchronizing users, groups, and user attributes with Omni.

Usage:
    # Full sync (groups and attributes)
    omni-user-manager --source json --users <path>
    omni-user-manager --source csv --users <path> --groups <path>

    # Groups-only sync
    omni-user-manager --source json --users <path> --mode groups
    omni-user-manager --source csv --users <path> --groups <path> --mode groups

    # Attributes-only sync
    omni-user-manager --source json --users <path> --mode attributes
    omni-user-manager --source csv --users <path> --groups <path> --mode attributes

Sync Modes:
    all (default)     Sync both group memberships and user attributes
    groups           Only sync group memberships
    attributes       Only sync user attributes

Data Sources:
    json            Single JSON file containing user and group data
    csv             Separate CSV files for users and groups
"""

import argparse
import sys
from typing import Optional
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print("ERROR: The 'python-dotenv' library is not found in the current Python environment.")
    print("This is a required dependency for 'omni-user-manager' to load configuration from .env files.")
    print("\nPlease ensure 'omni-user-manager' and its dependencies are correctly installed.")
    print("If you are using a virtual environment, make sure it is activated.")
    print("You can try reinstalling the package or installing the dependency manually:")
    print("  pip install omni-user-manager  (or pip install --upgrade omni-user-manager)")
    print("  Alternatively, to install only python-dotenv: pip install python-dotenv")
    sys.exit(1)
import os
from pathlib import Path
import dotenv # For find_dotenv

from .api.omni_client import OmniClient
from .data_sources.csv_source import CSVDataSource
from .data_sources.json_source import JSONDataSource
from .main import OmniSync

def main() -> int:
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        description='Omni User Manager - Synchronize users, groups, and attributes with Omni',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Sync subcommand
    sync_parser = subparsers.add_parser('sync', help='Synchronize users, groups, and attributes with Omni')
    sync_parser.add_argument('--source', choices=['csv', 'json'], required=True,
                            help='Data source type (csv or json)')
    sync_parser.add_argument('--users', required=True,
                            help='Path to users file')
    sync_parser.add_argument('--groups',
                            help='Path to groups CSV file (required for CSV source)')
    sync_parser.add_argument('--mode', choices=['all', 'groups', 'attributes'], default='all',
                            help='Sync mode: all (default) syncs both groups and attributes, groups-only, or attributes-only')
    sync_parser.add_argument('--debug', action='store_true', 
                            help='Enable debug print statements for .env loading')

    # User Management subcommands
    get_user_by_id_parser = subparsers.add_parser('get-user-by-id', help='Get a user by ID (or all users if no ID is provided)')
    get_user_by_id_parser.add_argument('user_id', nargs='?', default=None, help='User ID (optional)')

    search_users_parser = subparsers.add_parser('search-users', help='Search users by query string')
    search_users_parser.add_argument('--query', required=True, help='Query string to search users')

    get_user_attributes_parser = subparsers.add_parser('get-user-attributes', help="Get a user's custom attributes")
    get_user_attributes_parser.add_argument('user_id', help='User ID')

    # Group Management subcommands
    get_group_by_id_parser = subparsers.add_parser('get-group-by-id', help='Get a group by ID (or all groups if no ID is provided)')
    get_group_by_id_parser.add_argument('group_id', nargs='?', default=None, help='Group ID (optional)')

    search_groups_parser = subparsers.add_parser('search-groups', help='Search groups by query string')
    search_groups_parser.add_argument('--query', required=True, help='Query string to search groups')

    get_group_members_parser = subparsers.add_parser('get-group-members', help='Get all members of a group')
    get_group_members_parser.add_argument('group_id', help='Group ID')

    # Bulk Operations subcommands
    bulk_create_users_parser = subparsers.add_parser('bulk-create-users', help='Create multiple users in a single request')
    bulk_create_users_parser.add_argument('users_file', help='Path to users file (JSON or CSV)')

    bulk_update_users_parser = subparsers.add_parser('bulk-update-users', help='Update multiple users in a single request')
    bulk_update_users_parser.add_argument('users_file', help='Path to users file (JSON or CSV)')

    # Export/Import subcommands
    export_users_json_parser = subparsers.add_parser('export-users-json', help='Export all users as JSON')
    export_users_json_parser.add_argument('output_file', help='Path to output JSON file')
    export_groups_json_parser = subparsers.add_parser('export-groups-json', help='Export all groups as JSON')
    export_users_csv_parser = subparsers.add_parser('export-users-csv', help='Export all users as CSV')
    export_users_csv_parser.add_argument('output_file', help='Path to output CSV file')
    export_groups_json_parser.add_argument('output_file', help='Path to output JSON file')

    # Audit/History subcommands
    get_user_history_parser = subparsers.add_parser('get-user-history', help='Get history of changes for a user')
    get_user_history_parser.add_argument('user_id', help='User ID')

    get_group_history_parser = subparsers.add_parser('get-group-history', help='Get history of changes for a group')
    get_group_history_parser.add_argument('group_id', help='Group ID')

    # User Deletion subcommands
    delete_user_parser = subparsers.add_parser('delete-user', help='Delete a user by ID')
    delete_user_parser.add_argument('user_id', help='User ID to delete')
    delete_user_parser.add_argument('--yes', action='store_true', help='Confirm deletion without prompting')

    bulk_delete_users_parser = subparsers.add_parser('bulk-delete-users', help='Delete multiple users by IDs from a file (JSON or CSV)')
    bulk_delete_users_parser.add_argument('user_ids_file', help='Path to file containing user IDs (JSON array or CSV with id column)')
    bulk_delete_users_parser.add_argument('--yes', action='store_true', help='Confirm deletion without prompting')

    args = parser.parse_args()

    # Handle subcommands
    if args.command == 'get-user-by-id':
        from .api import OmniAPI
        api = OmniAPI()
        result = api.get_user_by_id(args.user_id)
        import json
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == 'search-users':
        from .api import OmniAPI
        api = OmniAPI()
        result = api.search_users(args.query)
        import json
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == 'get-user-attributes':
        from .api import OmniAPI
        api = OmniAPI()
        result = api.get_user_attributes(args.user_id)
        import json
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == 'sync':
        # --- Manual .env read test (conditional) ---
        if args.debug:
            print(f"DEBUG: Current working directory: {os.getcwd()}")
            print("DEBUG: Attempting manual read of .env file...")
            manual_env_path = os.path.join(os.getcwd(), ".env")
            try:
                with open(manual_env_path, 'r') as f:
                    lines = [f.readline().strip() for _ in range(2)] # Read first 2 lines
                    print(f"DEBUG: Manual read SUCCESS. First 2 lines: {lines}")
            except Exception as e:
                print(f"DEBUG: Manual read FAILED: {e}")
        # --- End manual .env read test ---
        env_file_path_found = dotenv.find_dotenv(usecwd=True) 
        if args.debug:
            print(f"DEBUG: dotenv.find_dotenv(usecwd=True) result: '{env_file_path_found}'")
        loaded_dotenv = load_dotenv(verbose=args.debug, override=True) 
        if args.debug:
            print(f"DEBUG: load_dotenv(verbose={args.debug}) result: {loaded_dotenv}") 
        if not loaded_dotenv or not os.getenv('OMNI_BASE_URL') or not os.getenv('OMNI_API_KEY'):
            if args.debug:
                print("DEBUG: load_dotenv failed or variables not set, attempting manual parse...")
            if env_file_path_found and os.path.exists(env_file_path_found):
                try:
                    with open(env_file_path_found, 'r') as f:
                        for line_number, line in enumerate(f):
                            line = line.strip()
                            if not line or line.startswith('#') or '=' not in line:
                                continue
                            key, value = line.split('=', 1)
                            key = key.strip()
                            if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))):
                                value = value[1:-1]
                            os.environ[key] = value
                            if args.debug:
                                print(f"DEBUG: Manually set os.environ['{key}'] = '{value}'")
                    if os.getenv('OMNI_BASE_URL') and os.getenv('OMNI_API_KEY'):
                        if args.debug:
                            print("DEBUG: Variables successfully set by manual parse.")
                    elif args.debug: # only print if debug is on and variables still not set
                        print("DEBUG: Variables NOT set even after manual parse.")        
                except Exception as e:
                    if args.debug:
                        print(f"DEBUG: Manual parse FAILED: {e}")
            elif args.debug: # only print if debug is on and file not found for manual parse
                print("DEBUG: .env file not found by find_dotenv for manual parse, or path doesn't exist.")
        base_url = os.getenv('OMNI_BASE_URL')
        api_key = os.getenv('OMNI_API_KEY')
        if not base_url or not api_key:
            print("Error: OMNI_BASE_URL and OMNI_API_KEY must be set in .env file")
            return 1
        omni_client = OmniClient(base_url, api_key)
        if args.source == 'csv':
            if not args.groups:
                print("Error: --groups is required when using CSV source")
                return 1
            data_source = CSVDataSource(args.users, args.groups)
            print("📄 Using CSV data source")
        elif args.source == 'json':
            data_source = JSONDataSource(args.users)
            print("📄 Using JSON data source")
        else:
            print("Error: Invalid source type")
            return 1
        sync = OmniSync(data_source, omni_client)
        if args.mode == 'all':
            print("🔄 Running full sync (groups and attributes)")
            results = sync.sync_all()
        elif args.mode == 'groups':
            print("🔄 Running groups-only sync")
            results = sync.sync_groups()
        elif args.mode == 'attributes':
            print("🔄 Running attributes-only sync")
            results = sync.sync_attributes()
        return 0
    elif args.command == 'get-group-by-id':
        from .api import OmniAPI
        api = OmniAPI()
        result = api.get_group_by_id(args.group_id)
        import json
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == 'search-groups':
        from .api import OmniAPI
        api = OmniAPI()
        result = api.search_groups(args.query)
        import json
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == 'get-group-members':
        from .api import OmniAPI
        api = OmniAPI()
        result = api.get_group_members(args.group_id)
        import json
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == 'bulk-create-users':
        from .api import OmniAPI
        import os, json
        api = OmniAPI()
        # Determine file type by extension
        if args.users_file.endswith('.json'):
            with open(args.users_file, 'r') as f:
                data = json.load(f)
                users = data["Resources"] if "Resources" in data else data
        elif args.users_file.endswith('.csv'):
            import csv
            users = []
            with open(args.users_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    users.append(row)
        else:
            print("Unsupported file type. Please provide a .json or .csv file.")
            return 1
        result = api.bulk_create_users(users)
        print(json.dumps(result, indent=2))
        print(f"\nSummary: {len(result['success'])} succeeded, {len(result['failure'])} failed, {len(result['skipped'])} skipped (already exists).")
        return 0
    elif args.command == 'bulk-update-users':
        from .api import OmniAPI
        import os, json
        api = OmniAPI()
        # Determine file type by extension
        if args.users_file.endswith('.json'):
            with open(args.users_file, 'r') as f:
                data = json.load(f)
                users = data["Resources"] if "Resources" in data else data
        elif args.users_file.endswith('.csv'):
            import csv
            users = []
            with open(args.users_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    users.append(row)
        else:
            print("Unsupported file type. Please provide a .json or .csv file.")
            return 1
        result = api.bulk_update_users(users)
        print(json.dumps(result, indent=2))
        print(f"\nSummary: {len(result['success'])} succeeded, {len(result['failure'])} failed.")
        return 0
    elif args.command == 'delete-user':
        from .api import OmniAPI
        api = OmniAPI()
        user_id = args.user_id
        if not args.yes:
            confirm = input(f"⚠️  Are you sure you want to delete user with ID '{user_id}'? This operation cannot be undone. Type 'yes' to confirm: ")
            if confirm.strip().lower() != 'yes':
                print("Aborted. No users were deleted.")
                return 0
        try:
            api.delete_user(user_id)
            print(f"✅ User '{user_id}' deleted successfully.")
        except Exception as e:
            print(f"❌ Failed to delete user '{user_id}': {e}")
        return 0
    elif args.command == 'bulk-delete-users':
        from .api import OmniAPI
        import os, json
        api = OmniAPI()
        user_ids = []
        if args.user_ids_file.endswith('.json'):
            with open(args.user_ids_file, 'r') as f:
                data = json.load(f)
                user_ids = data if isinstance(data, list) else data.get('user_ids', [])
        elif args.user_ids_file.endswith('.csv'):
            import csv
            with open(args.user_ids_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'id' in row:
                        user_ids.append(row['id'])
        else:
            print("Unsupported file type. Please provide a .json or .csv file.")
            return 1
        if not user_ids:
            print("No user IDs found in the provided file.")
            return 1
        if not args.yes:
            confirm = input(f"⚠️  Are you sure you want to delete {len(user_ids)} users? This operation cannot be undone. Type 'yes' to confirm: ")
            if confirm.strip().lower() != 'yes':
                print("Aborted. No users were deleted.")
                return 0
        result = api.bulk_delete_users(user_ids)
        print(json.dumps(result, indent=2))
        print(f"\nSummary: {len(result['success'])} succeeded, {len(result['failure'])} failed.")
        return 0
    elif args.command == 'export-users-csv':
        from .api import OmniAPI
        api = OmniAPI()
        api.export_users_csv(args.output_file)
        print(f"✅ Exported all users to CSV: {args.output_file}")
        return 0
    elif args.command == 'export-groups-json':
        from .api import OmniAPI
        api = OmniAPI()
        api.export_groups_json(args.output_file)
        print(f"✅ Exported all groups to JSON: {args.output_file}")
        return 0
    elif args.command == 'export-users-json':
        from .api import OmniAPI
        api = OmniAPI()
        users = api.get_users()
        import json
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2)
        print(f"✅ Exported all users to JSON: {args.output_file}")
        return 0
    elif args.command == 'get-user-history':
        print("User history (audit) is not available via this CLI. Please refer to the Omni platform's audit logs or logging dashboard.")
        return 0
    elif args.command == 'get-group-history':
        print("Group history (audit) is not available via this CLI. Please refer to the Omni platform's audit logs or logging dashboard.")
        return 0
    # TODO: Implement other subcommands as the corresponding API methods are added
    print(f"Unknown or unimplemented command: {args.command}")
    return 1

if __name__ == '__main__':
    sys.exit(main()) 