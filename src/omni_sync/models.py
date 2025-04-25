from typing import List, Dict, Optional, Any, TypedDict

class Email(TypedDict, total=False):
    primary: bool
    value: str

class Group(TypedDict, total=False):
    id: str
    displayName: str
    members: List[Dict[str, str]]

class UserAttributes(TypedDict, total=False):
    gcp_project: Optional[List[str]]
    axel_user: Optional[str]
    omni_user_timezone: Optional[str]
    test_attribute: Optional[str]
    pii_access: Optional[str]

class User(TypedDict, total=False):
    id: str
    userName: str
    displayName: str
    active: bool
    emails: Optional[List[Email]]
    groups: List[Dict[str, str]]
    userAttributes: Dict[str, Any]
