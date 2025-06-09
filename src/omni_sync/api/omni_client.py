import requests
from typing import List, Optional, Union, Dict, Any
import json
from ..models import User, Group
import csv

class OmniClient:
    """Client for interacting with the Omni API"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/scim+json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        """Make an HTTP request to the Omni API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=data)
            response.raise_for_status()
            if response.status_code == 204:
                return {}  # No content, but success
            try:
                return response.json()
            except json.JSONDecodeError as e:
                print(f"\n❌ API JSON Decode Error: {str(e)}")
                print(f"Response Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
                print(f"Response Text: {response.text if 'response' in locals() else 'N/A'}")
                raise
        except requests.exceptions.RequestException as e:
            print(f"\n❌ API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                print(f"Response Text: {e.response.text}")
            raise
    
    # User operations
    def create_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        return self._make_request('POST', '/scim/v2/users', user)
    
    def update_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing user"""
        if 'id' not in user:
            # Try to find the user by username
            users = self.get_users()
            for u in users:
                if u.get('userName') == user.get('userName'):
                    user['id'] = u['id']
                    break
            if 'id' not in user:
                raise ValueError(f"User {user.get('userName')} not found")
        
        return self._make_request('PUT', f'/scim/v2/users/{user["id"]}', user)
    
    def patch_user(self, user_id: str, patch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user using SCIM PATCH operation"""
        return self._make_request('PATCH', f'/scim/v2/users/{user_id}', patch_data)
    
    def delete_user(self, user_id: str) -> None:
        """Delete a user"""
        self._make_request('DELETE', f'/scim/v2/users/{user_id}')
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a user by username"""
        try:
            users = self.get_users()
            for user in users:
                if user.get('userName') == username:
                    return user
            return None
        except Exception as e:
            print(f"\n❌ Error getting user {username}: {str(e)}")
            return None
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        try:
            response = self._make_request('GET', '/scim/v2/users')
            return response.get('Resources', [])
        except Exception as e:
            print(f"\n❌ Error getting users: {str(e)}")
            return []
    
    def update_user_groups(self, user_id: str, username: str, groups: List[Dict[str, str]]) -> bool:
        """Update a user's group memberships"""
        try:
            data = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{
                    "op": "replace",
                    "path": "groups",
                    "value": groups
                }]
            }
            self._make_request('PATCH', f'/scim/v2/users/{user_id}', data)
            return True
        except Exception as e:
            print(f"\n❌ Error updating groups for user {username}: {str(e)}")
            return False
    
    # Group operations
    def create_group(self, group: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new group"""
        return self._make_request('POST', '/scim/v2/groups', group)
    
    def update_group(self, group: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing group"""
        if 'id' not in group:
            # Try to find the group by displayName
            groups = self.get_groups()
            for g in groups:
                if g.get('displayName') == group.get('displayName'):
                    group['id'] = g['id']
                    break
            if 'id' not in group:
                raise ValueError(f"Group {group.get('displayName')} not found")
        
        return self._make_request('PUT', f'/scim/v2/groups/{group["id"]}', group)
    
    def delete_group(self, group_id: str) -> None:
        """Delete a group"""
        self._make_request('DELETE', f'/scim/v2/groups/{group_id}')
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups"""
        try:
            response = self._make_request('GET', '/scim/v2/groups')
            return response.get('Resources', [])
        except Exception as e:
            print(f"\n❌ Error getting groups: {str(e)}")
            return []
    
    def update_group_members(self, group_id: str, group_name: str, members: List[Dict[str, str]]) -> bool:
        """Update a group's members list"""
        try:
            data = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [{
                    "op": "replace",
                    "path": "members",
                    "value": members
                }]
            }
            self._make_request('PATCH', f'/scim/v2/groups/{group_id}', data)
            return True
        except Exception as e:
            print(f"\n❌ Error updating members for group {group_name}: {str(e)}")
            return False

    def get_user_by_id(self, user_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
        """Get a user by ID, or all users if no ID is provided."""
        if not user_id:
            return self.get_users()
        try:
            response = self._make_request('GET', f'/scim/v2/users/{user_id}')
            return response
        except Exception as e:
            print(f"\n❌ Error getting user by ID {user_id}: {str(e)}")
            return None

    def search_users(self, query: str) -> List[Dict[str, Any]]:
        """
        Search users by email address (userName attribute).
        The query must be the full email address (exact match).
        Example: search_users('user@example.com')
        """
        try:
            filter_str = f'userName eq "{query}"'
            endpoint = f'/scim/v2/users?filter={requests.utils.quote(filter_str)}'
            response = self._make_request('GET', endpoint)
            return response.get('Resources', [])
        except Exception as e:
            print(f"\n❌ Error searching users with query '{query}': {str(e)}")
            return []

    def get_user_attributes(self, user_id: str) -> dict:
        """
        Get a user's custom attributes by user ID.
        Returns the 'urn:omni:params:1.0:UserAttribute' dict if present, else an empty dict.
        """
        try:
            user = self.get_user_by_id(user_id)
            if user and isinstance(user, dict):
                return user.get('urn:omni:params:1.0:UserAttribute', {})
            return {}
        except Exception as e:
            print(f"\n❌ Error getting attributes for user {user_id}: {str(e)}")
            return {}

    def get_group_by_id(self, group_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
        """
        Get a group by ID, or all groups if no ID is provided.
        If group_id is None or empty, returns all groups.
        """
        if not group_id:
            return self.get_groups()
        try:
            response = self._make_request('GET', f'/scim/v2/groups/{group_id}')
            return response
        except Exception as e:
            print(f"\n❌ Error getting group by ID {group_id}: {str(e)}")
            return None

    def search_groups(self, query: str) -> List[Dict[str, Any]]:
        """
        Search groups by displayName (exact match).
        The query must be the full group name (exact match).
        Example: search_groups('Admins')
        """
        try:
            filter_str = f'displayName eq "{query}"'
            # _make_request does not support query params, so add support here
            endpoint = f'/scim/v2/groups?filter={requests.utils.quote(filter_str)}'
            response = self._make_request('GET', endpoint)
            return response.get('Resources', [])
        except Exception as e:
            print(f"\n❌ Error searching groups with query '{query}': {str(e)}")
            return []

    def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """
        Get all members of a group by group ID.
        Returns the 'members' list if present, else an empty list.
        """
        try:
            group = self.get_group_by_id(group_id)
            if group and isinstance(group, dict):
                return group.get('members', [])
            return []
        except Exception as e:
            print(f"\n❌ Error getting members for group {group_id}: {str(e)}")
            return []

    def bulk_create_users(self, users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple users in a single request (one by one).
        Returns a summary with lists of successes, failures, and skipped (already exists).
        """
        results = {"success": [], "failure": [], "skipped": []}
        for user in users:
            try:
                created = self.create_user(user)
                results["success"].append(created)
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 409:
                    # User already exists
                    results["skipped"].append({"user": user, "error": "User already exists (409)"})
                else:
                    results["failure"].append({"user": user, "error": str(e)})
            except Exception as e:
                results["failure"].append({"user": user, "error": str(e)})
        return results

    def bulk_update_users(self, users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update multiple users in a single request (one by one).
        Returns a summary with lists of successes and failures.
        """
        results = {"success": [], "failure": []}
        for user in users:
            try:
                updated = self.update_user(user)
                results["success"].append(updated)
            except Exception as e:
                results["failure"].append({"user": user, "error": str(e)})
        return results

    def bulk_delete_users(self, user_ids: List[str]) -> Dict[str, Any]:
        """
        Delete multiple users in a single request (one by one).
        Returns a summary with lists of successes and failures.
        """
        results = {"success": [], "failure": []}
        for user_id in user_ids:
            try:
                self.delete_user(user_id)
                results["success"].append(user_id)
            except Exception as e:
                results["failure"].append({"user_id": user_id, "error": str(e)})
        return results

    def export_users_csv(self, file_path: str) -> None:
        """
        Export all users to a CSV file with columns: id, userName, displayName, active, email
        """
        fieldnames = ['id', 'userName', 'displayName', 'active', 'email']
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for user in self.get_users():
                row = {
                    'id': user.get('id', ''),
                    'userName': user.get('userName', ''),
                    'displayName': user.get('displayName', ''),
                    'active': str(user.get('active', '')),
                    'email': ''
                }
                emails = user.get('emails', [])
                if emails and isinstance(emails, list):
                    row['email'] = emails[0].get('value', '')
                writer.writerow(row)

    def export_groups_json(self, file_path: str) -> None:
        """Export all groups to a JSON file at the given path."""
        groups = self.get_groups()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(groups, f, indent=2)