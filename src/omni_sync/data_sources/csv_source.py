import csv
from pathlib import Path
from typing import List, Dict, Any, Set
import json
from .base import DataSource
from ..models import User, Group

class CSVDataSource(DataSource):
    """Data source implementation for CSV files"""
    
    def __init__(self, users_file: str, groups_file: str):
        self.users_file = users_file
        self.groups_file = groups_file
        self._groups_data = None # Cache for groups data
        self._users_data = None # Cache for users data
        
        # Create files if they don't exist
        if not Path(users_file).exists():
            Path(users_file).write_text("userName,displayName,active,userAttributes\n")
        if not Path(groups_file).exists():
            Path(groups_file).write_text("displayName,members\n")
    
    def _load_users(self):
        if self._users_data is None:
            self._users_data = []
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    # Check for essential columns (adjust as needed)
                    if not all(col in reader.fieldnames for col in ['id', 'userName', 'displayName', 'active', 'email', 'userAttributes']):
                         print(f"Warning: Missing expected columns in {self.users_file}. Required: id, userName, displayName, active, email, userAttributes")
                         # Decide how to handle: return empty, raise error, etc.

                    for row in reader:
                        try:
                            user_attributes = {}
                            ua_raw = row.get('userAttributes', '{}')
                            if ua_raw and ua_raw != '{}':
                                try:
                                    user_attributes = json.loads(ua_raw.replace('""', '"'))
                                except json.JSONDecodeError:
                                    print(f"Warning: Could not parse user attributes for user {row.get('userName', 'UNKNOWN')}")

                            user = {
                                'id': row.get('id'), # Ensure ID is present
                                'userName': row.get('userName'),
                                'displayName': row.get('displayName'),
                                'active': str(row.get('active', '')).lower() == 'true',
                                'emails': [{'value': row.get('email'), 'type': 'work'}], # Assuming one email
                                'userAttributes': user_attributes
                                # Note: CSV format doesn't store 'groups' directly in user row
                            }
                            self._users_data.append(user)
                        except KeyError as e:
                            print(f"Warning: Missing key {e} in user row: {row}")
                            continue # Skip problematic row
            except FileNotFoundError:
                print(f"Error: Users file not found at {self.users_file}")
            except Exception as e:
                print(f"Error reading users file {self.users_file}: {e}")
        return self._users_data

    def _load_groups(self):
        if self._groups_data is None:
            self._groups_data = []
            try:
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    if not all(col in reader.fieldnames for col in ['id', 'displayName', 'members']):
                         print(f"Warning: Missing expected columns in {self.groups_file}. Required: id, displayName, members")
                         # Decide how to handle

                    for row in reader:
                        try:
                            members = []
                            members_raw = row.get('members', '[]')
                            if members_raw and members_raw != '[]':
                                try:
                                    # Handle JSON string format from CSV
                                    cleaned_str = members_raw.replace('""', '"').strip('"')
                                    members = json.loads(cleaned_str)
                                    if not isinstance(members, list):
                                        print(f"Warning: Parsed members is not a list for group {row.get('displayName', 'UNKNOWN')}")
                                        members = [] # Reset to empty list if parse result isn't a list
                                except json.JSONDecodeError:
                                    print(f"Warning: Could not parse members for group {row.get('displayName', 'UNKNOWN')}: {members_raw}")

                            group = {
                                'id': row.get('id'), # Ensure ID is present
                                'displayName': row.get('displayName'),
                                'members': members # Parsed list or empty list
                            }
                            self._groups_data.append(group)
                        except KeyError as e:
                             print(f"Warning: Missing key {e} in group row: {row}")
                             continue # Skip problematic row
            except FileNotFoundError:
                print(f"Error: Groups file not found at {self.groups_file}")
                # No groups loaded, functions relying on it will get empty data
            except Exception as e:
                print(f"Error reading groups file {self.groups_file}: {e}")
        return self._groups_data

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users from CSV"""
        return self._load_users()
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups from CSV"""
        return self._load_groups()
    
    def _get_user_groups_from_csv(self, user_id_in_omni: str) -> Set[str]:
        """
        Get group IDs for a user based on cached groups.csv data.
        Uses the Omni user ID for matching against the members list.
        """
        user_groups = set()
        groups_data = self._load_groups() # Ensure groups are loaded
        if not groups_data:
             return set()
             
        for group in groups_data:
            try:
                # Members should be a list after _load_groups parsing
                members = group.get('members', [])
                if isinstance(members, list) and user_id_in_omni in members:
                     # We assume members list contains Omni User IDs
                    user_groups.add(group.get('id')) # Add the group's ID
            except KeyError as e:
                # Should be caught by _load_groups, but defensively check here too
                print(f"Warning: Issue processing group {group.get('id', 'unknown')} for user {user_id_in_omni}: {str(e)}")
                continue
        return user_groups

    def get_desired_groups(self, user_data: Dict[str, Any], user_id_in_omni: str) -> Set[str]:
        """Determine desired groups for a user using the loaded groups CSV data."""
        # user_data from the CSV source is ignored here, as group membership
        # is determined by the groups file, matched by user_id_in_omni.
        return self._get_user_groups_from_csv(user_id_in_omni)

    def update_users(self, users: List[Dict[str, Any]]) -> None:
        """Update users in CSV"""
        # Define headers expected by the writer
        # Ensure email is extracted correctly if needed
        fieldnames = ['id', 'userName', 'displayName', 'active', 'email', 'userAttributes']
        try:
            with open(self.users_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for user in users:
                    row = {
                        'id': user.get('id'),
                        'userName': user.get('userName'),
                        'displayName': user.get('displayName'),
                        'active': str(user.get('active', False)).lower(),
                        'email': user.get('emails', [{}])[0].get('value', ''), # Assuming first email
                        'userAttributes': json.dumps(user.get('userAttributes', {}))
                    }
                    writer.writerow(row)
            # Update cache
            self._users_data = users
        except IOError as e:
            print(f"Error writing to users file {self.users_file}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred during user update: {e}")

    def update_groups(self, groups: List[Dict[str, Any]]) -> None:
        """Update groups in CSV"""
        fieldnames=['id', 'displayName', 'members']
        try:
            with open(self.groups_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for group in groups:
                     row = {
                        'id': group.get('id'),
                        'displayName': group.get('displayName'),
                        # Ensure members are stored as JSON strings
                        'members': json.dumps(group.get('members', []))
                    }
                     writer.writerow(row)
             # Update cache
            self._groups_data = groups
        except IOError as e:
            print(f"Error writing to groups file {self.groups_file}: {e}")
        except Exception as e:
             print(f"An unexpected error occurred during group update: {e}")
