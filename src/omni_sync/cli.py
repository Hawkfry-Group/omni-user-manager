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
import os
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
    parser.add_argument('--debug-env', action='store_true', help='Enable debug print statements for .env loading (applies to all commands)')
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

    # User Management Operations subcommands
    create_users_parser = subparsers.add_parser('create-users', help='Create multiple users from a file')
    create_users_parser.add_argument('users_file', help='Path to users file (JSON or CSV)')

    update_user_attributes_parser = subparsers.add_parser('update-user-attributes', help='Update user attributes only (not group memberships)')
    update_user_attributes_parser.add_argument('users_file', help='Path to users file (JSON or CSV)')

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

    delete_users_parser = subparsers.add_parser('delete-users', help='Delete multiple users by IDs from a file (JSON or CSV)')
    delete_users_parser.add_argument('user_ids_file', help='Path to file containing user IDs (JSON array or CSV with id column)')
    delete_users_parser.add_argument('--yes', action='store_true', help='Confirm deletion without prompting')

    args = parser.parse_args()

    # --- .env loading logic (applies to all commands) ---
    debug_env = getattr(args, 'debug_env', False)
    env_file_path_found = dotenv.find_dotenv(usecwd=True)
    if debug_env:
        print(f"DEBUG: dotenv.find_dotenv(usecwd=True) result: '{env_file_path_found}'")
    loaded_dotenv = load_dotenv(env_file_path_found, verbose=debug_env, override=True)
    if debug_env:
        print(f"DEBUG: load_dotenv(verbose={debug_env}, override=True) result: {loaded_dotenv}")
        print(f"DEBUG: This allows .env file values to override global environment variables")
    if not loaded_dotenv or not os.getenv('OMNI_BASE_URL') or not os.getenv('OMNI_API_KEY'):
        if debug_env:
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
                        if debug_env:
                            print(f"DEBUG: Manually set os.environ['{key}'] = '{value}'")
                if os.getenv('OMNI_BASE_URL') and os.getenv('OMNI_API_KEY'):
                    if debug_env:
                        print("DEBUG: Variables successfully set by manual parse.")
                elif debug_env:
                    print("DEBUG: Variables NOT set even after manual parse.")
            except Exception as e:
                if debug_env:
                    print(f"DEBUG: Manual parse FAILED: {e}")
        elif debug_env:
            print("DEBUG: .env file not found by find_dotenv for manual parse, or path doesn't exist.")
    # --- End .env loading logic ---
    
    # For commands that require API access, check env vars before proceeding
    api_required_commands = [
        'get-user-by-id', 'search-users', 'get-user-attributes', 'get-group-by-id', 'search-groups', 'get-group-members',
        'create-users', 'update-user-attributes', 'delete-user', 'delete-users',
        'export-users-csv', 'export-groups-json', 'export-users-json', 'sync'
    ]
    if args.command in api_required_commands:
        base_url = os.getenv('OMNI_BASE_URL')
        api_key = os.getenv('OMNI_API_KEY')
        if not base_url or not api_key:
            print("Error: OMNI_BASE_URL and OMNI_API_KEY must be set in .env file or environment.")
            return 1

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
    elif args.command == 'create-users':
        from .api import OmniAPI
        import json
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
    elif args.command == 'update-user-attributes':
        from .api import OmniAPI
        import json
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
        # Ensure each user has 'id' and 'urn:omni:params:1.0:UserAttribute'
        processed_users = []
        for user in users:
            # If 'id' is missing, try to fetch by userName
            if 'id' not in user or not user['id']:
                userName = user.get('userName')
                if not userName:
                    print(f"Skipping user missing both 'id' and 'userName': {user}")
                    continue
                omni_user = api.search_users(userName)
                if omni_user and isinstance(omni_user, list) and len(omni_user) > 0:
                    user['id'] = omni_user[0].get('id')
                else:
                    print(f"Could not find user in Omni for userName '{userName}', skipping.")
                    continue
            # Only keep id and custom attributes
            processed_users.append({
                'id': user['id'],
                'urn:omni:params:1.0:UserAttribute': user.get('urn:omni:params:1.0:UserAttribute', {})
            })
        result = api.bulk_patch_user_attributes(processed_users)
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
    elif args.command == 'delete-users':
        from .api import OmniAPI
        import json
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
        api.export_users_json(args.output_file)
        print(f"✅ Exported all users to JSON in SCIM 2.0 format: {args.output_file}")
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