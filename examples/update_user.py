#!/usr/bin/env python3
"""
User Update Script
----------------
This can be used independently to the package itself as a standalone script.

Updates user group memberships based on data from CSV or JSON source.
Only updates users if their group memberships have changed.

Data Source Formats:
    CSV:
        - users.csv: Contains user information
        - groups.csv: Contains group memberships
        - Group memberships are determined by checking which groups list the user's ID
        - Example group members: ["user-id-1", "user-id-2"]
        - Invalid JSON in CSV fields will be reported and skipped
        - Malformed group data will not break the entire sync
    
    JSON:
        - users.json: Contains all user and group information
        - Group memberships are stored in each user's data
        - Example groups: [{"display": "group-name", "value": "group-id"}]

Usage:
    # Update using CSV data source (default)
    python -m examples.update_user

    # Update using JSON data source
    python -m examples.update_user --source json

Arguments:
    --source {csv|json}  Optional. Specify which data source to use (default: csv)
                        - csv: Reads from data/users.csv and data/groups.csv
                        - json: Reads from data/users.json

The script will:
1. Connect to the Omni API
2. Load user and group data from the specified source
3. Compare current group memberships with desired state
4. Update groups only when changes are needed
5. Provide detailed progress and error reporting
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv
import requests

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.omni_sync.api import OmniAPI
from src.omni_sync.data_sources import CSVDataSource, JSONDataSource

def check_files_exist(files):
    """Check if required files exist"""
    missing = []
    for file in files:
        if not os.path.exists(file):
            missing.append(file)
    return missing

def extract_group_ids(groups_data):
    """
    Extract group IDs from various group data formats.
    
    Handles:
    - JSON strings from CSV: ["group-id-1", "group-id-2"]
    - Group objects from JSON: [{"display": "name", "value": "group-id"}]
    - Direct list of IDs: ["group-id-1", "group-id-2"]
    
    Returns a set of group IDs.
    
    """
    if isinstance(groups_data, str):
        try:
            # Handle JSON string format from CSV
            # First unescape double quotes if present
            cleaned_str = groups_data.replace('""', '"').strip('"')
            groups = json.loads(cleaned_str)
            return set(groups) if isinstance(groups, list) else set()
        except json.JSONDecodeError:
            print(f"Warning: Could not parse groups data: {groups_data}")
            return set()
    elif isinstance(groups_data, list):
        # Handle list of group objects from JSON format
        return {g.get('value') for g in groups_data if isinstance(g, dict) and 'value' in g}
    return set()

def get_user_groups_from_csv(user_id, groups_data):
    """
    Get group IDs for a user based on groups.csv data.
    
    For CSV format, we look at each group's members list to find
    which groups the user belongs to. This is different from JSON
    format where group memberships are stored in the user data.
    
    Args:
        user_id: The ID of the user to look up
        groups_data: List of groups from groups.csv
    
    Returns:
        set: Group IDs that the user belongs to
    """
    user_groups = set()
    for group in groups_data:
        try:
            # The members field might already be parsed as a list
            members = group['members']
            if isinstance(members, str):
                # If it's a string, parse it
                members = json.loads(members.replace('""', '"').strip('"'))
            
            # Now members should be a list
            if isinstance(members, list) and user_id in members:
                user_groups.add(group['id'])
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not process group {group.get('id', 'unknown')}: {str(e)}")
            continue
    return user_groups

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Update user group memberships from data source')
    parser.add_argument('--source', choices=['csv', 'json'], default='csv',
                       help='Data source to use (csv or json)')
    args = parser.parse_args()
    
    # Load environment variables (.env file overrides global environment variables)
    # Use find_dotenv to ensure we load from current working directory
    from dotenv import find_dotenv
    env_file = find_dotenv(usecwd=True)
    load_dotenv(env_file, override=True)
    
    try:
        # Check required files exist
        if args.source == 'csv':
            required_files = ['data/users.csv', 'data/groups.csv']
        else:
            required_files = ['data/users.json']
            
        missing_files = check_files_exist(required_files)
        if missing_files:
            print("\n❌ Error: Required files not found:")
            for file in missing_files:
                print(f"- {file}")
            print("\nPlease ensure you have the correct data files in the data directory.")
            sys.exit(1)
        
        # Initialize API client
        try:
            api = OmniAPI()
            print("\n🔌 Connected to Omni API")
        except ValueError as e:
            print(f"\n❌ Error initializing API client: {str(e)}")
            sys.exit(1)
        
        # Initialize data source
        try:
            if args.source == 'csv':
                data_source = CSVDataSource(
                    users_file="data/users.csv",
                    groups_file="data/groups.csv"
                )
                print("📄 Using CSV data source")
                # Get groups data for CSV processing
                groups_data = data_source.get_groups()
            else:
                data_source = JSONDataSource(
                    users_file="data/users.json"
                )
                print("📄 Using JSON data source")
        except Exception as e:
            print(f"\n❌ Error initializing data source: {str(e)}")
            sys.exit(1)
            
        # Get all groups from Omni
        try:
            omni_groups = api.get_groups()
            print(f"\nFetched {len(omni_groups)} groups from Omni")
        except Exception as e:
            print("\n❌ Error fetching groups from Omni API:")
            print(str(e))
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            sys.exit(1)
            
        # Create a map of group IDs to groups for easier lookup
        group_map = {group['id']: group for group in omni_groups}
            
        # Get users from data source
        try:
            users = data_source.get_users()
            print(f"\n📊 Found {len(users)} users in data source")
        except Exception as e:
            print(f"\n❌ Error reading users from data source: {str(e)}")
            sys.exit(1)
            
        # Process each user
        updates_needed = 0
        group_updates_attempted = 0
        group_updates_succeeded = 0
        
        for user in users:
            try:
                # Get current user state from Omni
                current_user = api.get_user(user['userName'])
                if not current_user:
                    print(f"\n⚠️ User not found in Omni: {user['userName']}")
                    continue
                
                # Compare group memberships
                current_groups = set()
                for group in current_user.get('groups', []):
                    if isinstance(group, dict):
                        current_groups.add(group.get('value'))
                    else:
                        current_groups.add(group)
                
                # Get desired groups based on data source
                if args.source == 'csv':
                    # For CSV, look up user's groups from groups.csv
                    desired_groups = get_user_groups_from_csv(current_user['id'], groups_data)
                else:
                    # For JSON, use groups from user data
                    desired_groups = extract_group_ids(user.get('groups', []))
                
                if current_groups != desired_groups:
                    updates_needed += 1
                    print(f"\n🔄 Updating {user['userName']}")
                    print(f"  Current groups: {current_groups}")
                    print(f"  Desired groups: {desired_groups}")
                    
                    # Update each affected group
                    for group_id in current_groups.union(desired_groups):
                        if group_id not in group_map:
                            print(f"  ⚠️ Unknown group ID: {group_id}")
                            continue
                            
                        group = group_map[group_id]
                        current_members = group.get('members', [])
                        
                        # Remove user if they shouldn't be in this group
                        if group_id not in desired_groups:
                            updated_members = [m for m in current_members if m.get('value') != current_user['id']]
                        # Add user if they should be in this group
                        elif group_id not in current_groups:
                            updated_members = current_members + [{
                                "display": current_user['userName'],
                                "value": current_user['id']
                            }]
                        else:
                            continue
                            
                        # Update group with new members list
                        update_data = {
                            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                            "id": group_id,
                            "displayName": group['displayName'],
                            "members": updated_members
                        }
                        
                        try:
                            group_updates_attempted += 1
                            api.update_group(update_data)
                            print(f"  ✅ Updated group: {group['displayName']}")
                            group_updates_succeeded += 1
                        except Exception as e:
                            print(f"  ❌ Failed to update group {group['displayName']}: {str(e)}")
                            if hasattr(e, 'response') and e.response is not None:
                                print(f"  Response: {e.response.text}")
                
            except Exception as e:
                print(f"\n❌ Error processing user {user['userName']}: {str(e)}")
                continue
        
        # Print summary
        print("\n📊 Summary:")
        print(f"Total users processed: {len(users)}")
        print(f"Users needing updates: {updates_needed}")
        print(f"Group updates attempted: {group_updates_attempted}")
        print(f"Group updates succeeded: {group_updates_succeeded}")
        
        if group_updates_succeeded == group_updates_attempted:
            print("\n✅ All updates completed successfully!")
        else:
            failed_updates = group_updates_attempted - group_updates_succeeded
            print(f"\n⚠️ {failed_updates} group updates failed. Please check the logs above.")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        if isinstance(e, requests.exceptions.RequestException) and hasattr(e, 'response'):
            print(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main() 