from typing import List
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .base import DataSource
from ..models import User, Group

class GoogleSheetsDataSource(DataSource):
    """Data source implementation for Google Sheets"""
    
    def __init__(self, spreadsheet_id: str, credentials: Credentials):
        self.spreadsheet_id = spreadsheet_id
        self.service = build('sheets', 'v4', credentials=credentials)
        self.sheet = self.service.spreadsheets()
        
        # Ensure sheets exist
        self._ensure_sheets_exist()
    
    def _ensure_sheets_exist(self) -> None:
        """Ensure required sheets exist in the spreadsheet"""
        try:
            spreadsheet = self.sheet.get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = {sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])}
            
            if 'Users' not in sheets:
                self._create_sheet('Users', ['userName', 'displayName', 'active', 'userAttributes'])
            if 'Groups' not in sheets:
                self._create_sheet('Groups', ['displayName', 'members'])
        except HttpError as error:
            raise Exception(f"Error ensuring sheets exist: {error}")
    
    def _create_sheet(self, title: str, headers: List[str]) -> None:
        """Create a new sheet with headers"""
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': title
                    }
                }
            }]
        }
        self.sheet.batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()
        
        # Add headers
        range_name = f"{title}!A1:{chr(65 + len(headers) - 1)}1"
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={'values': [headers]}
        ).execute()
    
    def get_users(self) -> List[User]:
        """Get all users from Google Sheets"""
        try:
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Users!A2:D'
            ).execute()
            values = result.get('values', [])
            
            users = []
            for row in values:
                if len(row) >= 4:  # Ensure row has all required fields
                    user_attrs = json.loads(row[3] if len(row) > 3 else '{}')
                    users.append(User(
                        userName=row[0],
                        displayName=row[1],
                        active=row[2].lower() == 'true',
                        userAttributes=user_attrs
                    ))
            return users
        except HttpError as error:
            raise Exception(f"Error getting users: {error}")
    
    def get_groups(self) -> List[Group]:
        """Get all groups from Google Sheets"""
        try:
            result = self.sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Groups!A2:B'
            ).execute()
            values = result.get('values', [])
            
            groups = []
            for row in values:
                if len(row) >= 2:  # Ensure row has all required fields
                    members = json.loads(row[1] if len(row) > 1 else '[]')
                    groups.append(Group(
                        displayName=row[0],
                        members=members
                    ))
            return groups
        except HttpError as error:
            raise Exception(f"Error getting groups: {error}")
    
    def update_users(self, users: List[User]) -> None:
        """Update users in Google Sheets"""
        try:
            values = []
            for user in users:
                values.append([
                    user.userName,
                    user.displayName,
                    str(user.active),
                    json.dumps(user.userAttributes)
                ])
            
            self.sheet.values().update(
                spreadsheetId=self.spreadsheet_id,
                range='Users!A2',
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
        except HttpError as error:
            raise Exception(f"Error updating users: {error}")
    
    def update_groups(self, groups: List[Group]) -> None:
        """Update groups in Google Sheets"""
        try:
            values = []
            for group in groups:
                values.append([
                    group.displayName,
                    json.dumps(group.members)
                ])
            
            self.sheet.values().update(
                spreadsheetId=self.spreadsheet_id,
                range='Groups!A2',
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
        except HttpError as error:
            raise Exception(f"Error updating groups: {error}")
