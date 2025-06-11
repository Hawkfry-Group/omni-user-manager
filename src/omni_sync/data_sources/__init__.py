import json
import csv
from typing import List, Dict, Any
from .base import DataSource
from .csv_source import CSVDataSource
from .json_source import JSONDataSource
__all__ = ['DataSource', 'CSVDataSource', 'JSONDataSource']

class BaseDataSource:
    """Base class for data sources"""
    def get_users(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
        
    def get_groups(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

class CSVDataSource(BaseDataSource):
    """CSV data source implementation"""
    def __init__(self, users_file: str, groups_file: str):
        self.users_file = users_file
        self.groups_file = groups_file
    
    def get_users(self) -> List[Dict[str, Any]]:
        users = []
        with open(self.users_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse JSON fields
                row['groups'] = json.loads(row['groups'])
                row['userAttributes'] = json.loads(row['userAttributes'])
                users.append(row)
        return users
    
    def get_groups(self) -> List[Dict[str, Any]]:
        groups = []
        with open(self.groups_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse JSON fields
                row['members'] = json.loads(row['members'])
                groups.append(row)
        return groups

class JSONDataSource(BaseDataSource):
    """JSON data source implementation"""
    def __init__(self, users_file: str):
        self.users_file = users_file
        self._data = None
    
    @property
    def data(self):
        if self._data is None:
            with open(self.users_file, 'r') as f:
                self._data = json.load(f)
        return self._data
    
    def get_users(self) -> List[Dict[str, Any]]:
        return self.data.get('Resources', [])
    
    def get_groups(self) -> List[Dict[str, Any]]:
        # Extract unique groups from user data
        groups = {}
        for user in self.get_users():
            for group in user.get('groups', []):
                if group['value'] not in groups:
                    groups[group['value']] = {
                        'id': group['value'],
                        'displayName': group['display'],
                        'members': []
                    }
                groups[group['value']]['members'].append(user['id'])
        return list(groups.values())
