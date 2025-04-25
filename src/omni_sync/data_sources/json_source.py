import json
from typing import List, Dict, Any, Set
from .base import DataSource

class JSONDataSource(DataSource):
    """JSON data source implementation"""
    def __init__(self, users_file: str):
        self.users_file = users_file
        self._data = None
        self._users = None # Cache users

    @staticmethod
    def _extract_group_ids(groups_data: Any) -> Set[str]:
        """
        Extract group IDs from various group data formats within JSON.
        Handles list of group objects: [{"display": "name", "value": "group-id"}]
        Returns a set of group IDs.
        """
        if isinstance(groups_data, list):
            # Handle list of group objects from JSON format
            return {g.get('value') for g in groups_data if isinstance(g, dict) and 'value' in g}
        # Add handling for other potential formats if needed, otherwise return empty
        return set()

    def _load_data(self):
        if self._data is None:
            try:
                with open(self.users_file, 'r') as f:
                    self._data = json.load(f)
                    self._users = self._data.get('Resources', [])
            except FileNotFoundError:
                print(f"Error: Users file not found at {self.users_file}")
                self._data = {} # Prevent repeated load attempts
                self._users = []
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {self.users_file}")
                self._data = {} # Prevent repeated load attempts
                self._users = []

    @property
    def data(self):
        self._load_data()
        return self._data

    def get_users(self) -> List[Dict[str, Any]]:
        self._load_data()
        return self._users

    def get_groups(self) -> List[Dict[str, Any]]:
        """JSON source doesn't have separate groups; derive from users if needed."""
        # This method might not be strictly needed if groups are always derived from users.
        # Keep original logic for now if it was used elsewhere.
        self._load_data()
        groups = set()
        for user in self._users:
            user_groups = user.get('groups', [])
            for group in user_groups:
                if isinstance(group, dict) and 'value' in group and 'display' in group:
                    groups.add((group['value'], group['display']))

        # Represent as a list of dicts consistent with base class expectations
        return [{'id': gid, 'displayName': display} for gid, display in groups]

    def update_users(self, users: List[Dict[str, Any]]) -> None:
        """Update users in JSON file."""
        # Ensure data is loaded before attempting to write
        self._load_data()
        # Update the 'Resources' key in the loaded data structure
        self._data['Resources'] = users
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            # Update cache
            self._users = users
        except IOError as e:
            print(f"Error writing to users file {self.users_file}: {e}")

    def update_groups(self, groups: List[Dict[str, Any]]) -> None:
        """Update groups in JSON (Not directly applicable, groups are part of users)."""
        print("Warning: update_groups called on JSONDataSource. Group updates should be handled by updating users.")
        pass # Or raise NotImplementedError if this should never be called

    def get_desired_groups(self, user_data: Dict[str, Any], user_id_in_omni: str) -> Set[str]:
        """Extract desired group IDs from the user's data in the JSON source."""
        # user_id_in_omni is ignored here as groups are directly in user_data
        return self._extract_group_ids(user_data.get('groups', [])) 