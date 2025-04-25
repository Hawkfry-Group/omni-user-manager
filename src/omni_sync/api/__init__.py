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
