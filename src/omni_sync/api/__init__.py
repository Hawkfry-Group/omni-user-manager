import os
from .omni_client import OmniClient

class OmniAPI:
    """High-level API wrapper for Omni operations"""
    
    def __init__(self):
        base_url = os.getenv('OMNI_BASE_URL')
        api_key = os.getenv('OMNI_API_KEY')
        
        if not base_url or not api_key:
            raise ValueError("OMNI_BASE_URL and OMNI_API_KEY must be set in environment variables")
        
        self.client = OmniClient(base_url, api_key)
    
    def update_user(self, user_data: dict) -> dict:
        """Update a user's attributes"""
        return self.client.update_user(user_data)
    
    def patch_user(self, user_id: str, patch_data: dict) -> dict:
        """Update a user using SCIM PATCH operation"""
        return self.client.patch_user(user_id, patch_data)
    
    def get_user(self, username: str) -> dict:
        """Get a user by username"""
        return self.client.get_user_by_username(username)
    
    def get_users(self) -> list:
        """Get all users"""
        return self.client.get_users()
    
    def get_groups(self) -> list:
        """Get all groups"""
        return self.client.get_groups()
    
    def update_group(self, group_data: dict) -> dict:
        """Update a group's attributes and members"""
        return self.client.update_group(group_data)
    
    def get_user_by_id(self, user_id: str = None):
        """Get a user by ID, or all users if no ID is provided."""
        return self.client.get_user_by_id(user_id)
    
    def search_users(self, query: str) -> list:
        """
        Search users by email address (userName attribute).
        The query must be the full email address (exact match).
        Example: search_users('user@example.com')
        """
        return self.client.search_users(query)
    
    def get_user_attributes(self, user_id: str) -> dict:
        """
        Get a user's custom attributes by user ID.
        Returns the 'urn:omni:params:1.0:UserAttribute' dict if present, else an empty dict.
        """
        return self.client.get_user_attributes(user_id)
    
    def get_group_by_id(self, group_id: str = None):
        """
        Get a group by ID, or all groups if no ID is provided.
        If group_id is None or empty, returns all groups.
        """
        return self.client.get_group_by_id(group_id)
    
    def search_groups(self, query: str) -> list:
        """
        Search groups by displayName (exact match).
        The query must be the full group name (exact match).
        Example: search_groups('Admins')
        """
        return self.client.search_groups(query)
    
    def get_group_members(self, group_id: str) -> list:
        """
        Get all members of a group by group ID.
        Returns the 'members' list if present, else an empty list.
        """
        return self.client.get_group_members(group_id)
    
    def bulk_create_users(self, users: list) -> dict:
        """
        Create multiple users in a single request (one by one).
        Returns a summary with lists of successes and failures.
        """
        return self.client.bulk_create_users(users)
    
    def bulk_update_users(self, users: list) -> dict:
        """
        Update multiple users in a single request (one by one).
        Returns a summary with lists of successes and failures.
        """
        return self.client.bulk_update_users(users)
    
    def delete_user(self, user_id: str) -> None:
        """Delete a user by Omni-assigned ID."""
        return self.client.delete_user(user_id)
    
    def bulk_delete_users(self, user_ids: list) -> dict:
        """Delete multiple users by Omni-assigned IDs."""
        return self.client.bulk_delete_users(user_ids)
    
    def export_users_csv(self, file_path: str) -> None:
        """Export all users to a CSV file with columns: id, userName, displayName, active, email"""
        return self.client.export_users_csv(file_path)
    
    def export_groups_json(self, file_path: str) -> None:
        """Export all groups to a JSON file at the given path."""
        return self.client.export_groups_json(file_path)
    
    def export_users_json(self, file_path: str) -> None:
        """Export all users to a JSON file in SCIM 2.0 format."""
        return self.client.export_users_json(file_path)
    
    def bulk_patch_user_attributes(self, users: list) -> dict:
        """
        Patch user attributes for multiple users (one by one) using SCIM PATCH.
        Only updates custom attributes, not group memberships.
        Expects each user dict to have 'id' and 'urn:omni:params:1.0:UserAttribute'.
        Returns a summary with lists of successes and failures.
        """
        results = {"success": [], "failure": []}
        for user in users:
            user_id = user.get("id")
            attrs = user.get("urn:omni:params:1.0:UserAttribute")
            if not user_id or attrs is None:
                results["failure"].append({"user": user, "error": "Missing 'id' or 'urn:omni:params:1.0:UserAttribute' in user data"})
                continue
            patch_data = {
                "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                "Operations": [
                    {
                        "op": "replace",
                        "path": "urn:omni:params:1.0:UserAttribute",
                        "value": attrs
                    }
                ]
            }
            try:
                updated = self.patch_user(user_id, patch_data)
                results["success"].append(updated)
            except Exception as e:
                results["failure"].append({"user": user, "error": str(e)})
        return results
