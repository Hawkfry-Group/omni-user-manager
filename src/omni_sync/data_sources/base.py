from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
from ..models import User, Group

class DataSource(ABC):
    """Base interface for all data sources"""
    
    @abstractmethod
    def get_users(self) -> List[User]:
        """Get all users from the data source"""
        pass
    
    @abstractmethod
    def get_groups(self) -> List[Group]:
        """Get all groups from the data source"""
        pass
    
    @abstractmethod
    def update_users(self, users: List[User]) -> None:
        """Update users in the data source"""
        pass
    
    @abstractmethod
    def update_groups(self, groups: List[Group]) -> None:
        """Update groups in the data source"""
        pass

    @abstractmethod
    def get_desired_groups(self, user_data: Dict[str, Any], user_id_in_omni: str) -> Set[str]:
        """Get the set of group IDs a user should belong to based on the source data."""
        pass
