from typing import List, Dict, Any
from .api.omni_client import OmniClient
from .data_sources.base import DataSource
# These specific imports might not be needed anymore directly here
# from .data_sources.csv_source import CSVDataSource
# from .data_sources.json_source import JSONDataSource
import json
import time

class OmniSync:
    """Main class for synchronizing data between a data source and Omni"""

    def __init__(self, data_source: DataSource, omni_client: OmniClient, dry_run: bool = False):
        self.data_source = data_source
        self.omni_client = omni_client
        self.dry_run = dry_run

    def _fetch_data(self, fetch_func, description: str):
        """Helper function to fetch data and handle errors."""
        try:
            data = fetch_func()
            # Handle potential None return from fetch_func before len()
            if data is None:
                print(f"\nℹ️ No data returned when fetching {description}.")
                return None
            print(f"\n✅ Fetched {len(data)} {description}")
            return data
        except Exception as e:
            print(f"\n❌ Error fetching {description}: {str(e)}")
            return None # Indicate failure

    def _process_user_groups(self, user: Dict[str, Any], current_user: Dict[str, Any], group_map: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """Process group updates for a single user"""
        results = {'attempted': 0, 'succeeded': 0}
        
        # Extract current groups from Omni user data
        current_groups = set()
        for group in current_user.get('groups', []):
            if isinstance(group, dict):
                current_groups.add(group.get('value'))
            else:
                current_groups.add(group)
        
        # Get desired groups
        omni_user_id = current_user.get('id')
        if not omni_user_id:
            print(f"\n⚠️ Skipping user {user.get('userName')} because Omni user data lacks an 'id'.")
            return results
            
        desired_groups = self.data_source.get_desired_groups(user, omni_user_id)

        # Check if updates are needed
        if current_groups != desired_groups:
            print(f"\n🔄 Updating groups for {user.get('userName')}")
            print(f"  Current groups: {sorted(list(current_groups))}")
            print(f"  Desired groups: {sorted(list(desired_groups))}")

            groups_to_add = desired_groups - current_groups
            groups_to_remove = current_groups - desired_groups

            # Process removals first
            for group_id in groups_to_remove:
                if group_id not in group_map:
                    print(f"  ⚠️ Cannot remove user from unknown/inaccessible group ID: {group_id}")
                    continue

                group = group_map[group_id]
                group_name = group.get('displayName', group_id)
                print(f"  ➖ Removing user from group: {group_name} ({group_id})")
                
                current_members = group.get('members', [])
                updated_members = [m for m in current_members if m.get('value') != omni_user_id]

                if len(updated_members) < len(current_members):
                    update_data = {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                        "id": group_id,
                        "displayName": group_name,
                        "members": updated_members
                    }
                    try:
                        results['attempted'] += 1
                        if self.dry_run:
                            print(f"    🔍 [DRY RUN] Would update group: {group_name}")
                            results['succeeded'] += 1
                        else:
                            self.omni_client.update_group(update_data)
                            print(f"    ✅ Successfully updated group: {group_name}")
                            results['succeeded'] += 1
                    except Exception as e:
                        print(f"    ❌ Failed to update group {group_name}: {str(e)}")
                        if hasattr(e, 'response') and e.response is not None:
                            print(f"    Response: {e.response.text}")
                else:
                    print(f"    ℹ️ User {omni_user_id} was not found in current members list for group {group_name}. No removal needed.")
                    
            # Process additions
            for group_id in groups_to_add:
                if group_id not in group_map:
                    print(f"  ⚠️ Cannot add user to unknown/inaccessible group ID: {group_id}")
                    continue

                group = group_map[group_id]
                group_name = group.get('displayName', group_id)
                print(f"  ➕ Adding user to group: {group_name} ({group_id})")
                
                current_members = group.get('members', [])
                current_member_ids = {m.get('value') for m in current_members if isinstance(m, dict) and m.get('value')}
                
                if omni_user_id not in current_member_ids:
                    updated_members = current_members + [{
                        "display": user.get('userName'),
                        "value": omni_user_id
                    }]
                    
                    update_data = {
                        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                        "id": group_id,
                        "displayName": group_name,
                        "members": updated_members
                    }
                    try:
                        results['attempted'] += 1
                        if self.dry_run:
                            print(f"    🔍 [DRY RUN] Would update group: {group_name}")
                            results['succeeded'] += 1
                        else:
                            self.omni_client.update_group(update_data)
                            print(f"    ✅ Successfully updated group: {group_name}")
                            results['succeeded'] += 1
                    except Exception as e:
                        print(f"    ❌ Failed to update group {group_name}: {str(e)}")
                        if hasattr(e, 'response') and e.response is not None:
                            print(f"    Response: {e.response.text}")
                else:
                    print(f"    ℹ️ User {omni_user_id} is already in members list for group {group_name}. No addition needed.")
        
        return results

    def _process_user_attributes(self, user: Dict[str, Any], current_user: Dict[str, Any]) -> Dict[str, int]:
        """Process attribute updates for a single user"""
        results = {'attempted': 0, 'succeeded': 0}
        
        # Get current and desired attributes
        current_attrs = current_user.get('urn:omni:params:1.0:UserAttribute', {})
        desired_attrs = user.get('urn:omni:params:1.0:UserAttribute', {})
        
        # Check if updates are needed
        if current_attrs != desired_attrs:
            print(f"\n🔄 Updating attributes for {user.get('userName')}")
            print(f"  Current attributes: {json.dumps(current_attrs, indent=2)}")
            print(f"  Desired attributes: {json.dumps(desired_attrs, indent=2)}")
            
            try:
                results['attempted'] += 1

                # Filter out null values from desired attributes
                filtered_attrs = {k: v for k, v in desired_attrs.items() if v is not None}
                print(f"  Filtered attributes: {json.dumps(filtered_attrs, indent=2)}")

                # Create the update data with the filtered attributes
                update_data = {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "id": current_user['id'],
                    "userName": current_user['userName'],
                    "displayName": current_user['displayName'],
                    "urn:omni:params:1.0:UserAttribute": filtered_attrs
                }

                if self.dry_run:
                    print(f"  🔍 [DRY RUN] Would send update data: {json.dumps(update_data, indent=2)}")
                    print(f"    🔍 [DRY RUN] Would update attributes")
                    results['succeeded'] += 1
                else:
                    print(f"  Sending update data: {json.dumps(update_data, indent=2)}")
                    self.omni_client.update_user(update_data)
                    print(f"    ✅ Successfully updated attributes")
                    results['succeeded'] += 1
            except Exception as e:
                print(f"    ❌ Failed to update attributes: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"    Response: {e.response.text}")
        
        return results

    def sync_groups(self) -> Dict[str, Dict[str, int]]:
        """Synchronize only group memberships"""
        error_result = {'groups': {'attempted': 0, 'succeeded': 0}}

        omni_groups = self._fetch_data(self.omni_client.get_groups, "groups from Omni")
        if omni_groups is None:
            print("\n❌ Failed to fetch groups from Omni. Cannot proceed with sync.")
            return error_result
        group_map = {group['id']: group for group in omni_groups}

        # Fetch all users from Omni once and cache them
        omni_users = self._fetch_data(self.omni_client.get_users, "users from Omni")
        if omni_users is None:
            print("\n❌ Failed to fetch users from Omni. Cannot proceed with sync.")
            return error_result
        omni_user_map = {user['userName']: user for user in omni_users}

        users = self._fetch_data(self.data_source.get_users, f"users from {type(self.data_source).__name__}")
        if users is None:
            print("\n❌ Failed to fetch users from data source. Cannot proceed with sync.")
            return error_result

        for user in users:
            try:
                user_name = user.get('userName')
                if not user_name:
                    print(f"\n⚠️ Skipping user record with missing 'userName': {user}")
                    continue

                # Look up user from cache instead of API call
                current_user = omni_user_map.get(user_name)
                if not current_user:
                    print(f"\n⚠️ User not found in Omni: {user_name}")
                    continue

                group_results = self._process_user_groups(user, current_user, group_map)
                error_result['groups']['attempted'] += group_results['attempted']
                error_result['groups']['succeeded'] += group_results['succeeded']

                # Add delay to avoid rate limiting
                time.sleep(0.2)

            except Exception as e:
                user_name_for_error = user.get('userName', '[UNKNOWN USERNAME]')
                print(f"\n❌ An unexpected error occurred processing user {user_name_for_error}: {str(e)}")
                # Add delay even on error to avoid rate limiting
                time.sleep(0.2)
                continue

        print("\n📊 Groups Sync Summary:")
        print(f"Total users processed: {len(users)}")
        print(f"Group updates attempted: {error_result['groups']['attempted']}")
        print(f"Group updates succeeded: {error_result['groups']['succeeded']}")
        
        return error_result

    def sync_attributes(self) -> Dict[str, Dict[str, int]]:
        """Synchronize only user attributes"""
        error_result = {'attributes': {'attempted': 0, 'succeeded': 0}}

        # Fetch all users from Omni once and cache them
        omni_users = self._fetch_data(self.omni_client.get_users, "users from Omni")
        if omni_users is None:
            print("\n❌ Failed to fetch users from Omni. Cannot proceed with sync.")
            return error_result
        omni_user_map = {user['userName']: user for user in omni_users}

        users = self._fetch_data(self.data_source.get_users, f"users from {type(self.data_source).__name__}")
        if users is None:
            print("\n❌ Failed to fetch users from data source. Cannot proceed with sync.")
            return error_result

        for user in users:
            try:
                user_name = user.get('userName')
                if not user_name:
                    print(f"\n⚠️ Skipping user record with missing 'userName': {user}")
                    continue

                # Look up user from cache instead of API call
                current_user = omni_user_map.get(user_name)
                if not current_user:
                    print(f"\n⚠️ User not found in Omni: {user_name}")
                    continue

                attr_results = self._process_user_attributes(user, current_user)
                error_result['attributes']['attempted'] += attr_results['attempted']
                error_result['attributes']['succeeded'] += attr_results['succeeded']

                # Add delay to avoid rate limiting
                time.sleep(0.2)

            except Exception as e:
                user_name_for_error = user.get('userName', '[UNKNOWN USERNAME]')
                print(f"\n❌ An unexpected error occurred processing user {user_name_for_error}: {str(e)}")
                # Add delay even on error to avoid rate limiting
                time.sleep(0.2)
                continue

        print("\n📊 Attributes Sync Summary:")
        print(f"Total users processed: {len(users)}")
        print(f"Attribute updates attempted: {error_result['attributes']['attempted']}")
        print(f"Attribute updates succeeded: {error_result['attributes']['succeeded']}")
        
        return error_result

    def sync_all(self) -> Dict[str, Dict[str, int]]:
        """Synchronize both groups and attributes"""
        error_result = {
            'groups': {'attempted': 0, 'succeeded': 0},
            'attributes': {'attempted': 0, 'succeeded': 0}
        }

        # First sync groups
        group_results = self.sync_groups()
        error_result['groups'] = group_results['groups']

        # Then sync attributes
        attr_results = self.sync_attributes()
        error_result['attributes'] = attr_results['attributes']

        print("\n📊 Full Sync Summary:")
        print(f"Group updates attempted: {error_result['groups']['attempted']}")
        print(f"Group updates succeeded: {error_result['groups']['succeeded']}")
        print(f"Attribute updates attempted: {error_result['attributes']['attempted']}")
        print(f"Attribute updates succeeded: {error_result['attributes']['succeeded']}")
        
        return error_result
