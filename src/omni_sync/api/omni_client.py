import requests
from typing import List, Optional, Union, Dict, Any
import json
from ..models import User, Group

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
            return response.json()
        except requests.exceptions.JSONDecodeError as e:
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
