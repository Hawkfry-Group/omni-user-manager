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
        """Synchronize group memberships using group-centric approach (PUT to groups endpoint)"""
        error_result = {'groups': {'attempted': 0, 'succeeded': 0}}

        # Fetch all groups from Omni
        omni_groups = self._fetch_data(self.omni_client.get_groups, "groups from Omni")
        if omni_groups is None:
            print("\n❌ Failed to fetch groups from Omni. Cannot proceed with sync.")
            return error_result

        # Fetch all users from Omni and create username->id and id->username mappings
        omni_users = self._fetch_data(self.omni_client.get_users, "users from Omni")
        if omni_users is None:
            print("\n❌ Failed to fetch users from Omni. Cannot proceed with sync.")
            return error_result
        username_to_id = {user['userName']: user['id'] for user in omni_users}
        id_to_username = {user['id']: user['userName'] for user in omni_users}

        # Fetch desired state from data source
        desired_users = self._fetch_data(self.data_source.get_users, f"users from {type(self.data_source).__name__}")
        if desired_users is None:
            print("\n❌ Failed to fetch users from data source. Cannot proceed with sync.")
            return error_result

        # Build desired group memberships: {group_id: set of user_ids}
        desired_group_members = {}
        for user in desired_users:
            username = user.get('userName')
            if not username:
                continue

            user_id = username_to_id.get(username)
            if not user_id:
                print(f"\n⚠️ User {username} from data source not found in Omni, skipping")
                continue

            # Get desired groups for this user
            user_groups = user.get('groups', [])
            for group in user_groups:
                group_id = group.get('value') if isinstance(group, dict) else group
                if group_id:
                    if group_id not in desired_group_members:
                        desired_group_members[group_id] = set()
                    desired_group_members[group_id].add(user_id)

        # Build set of managed user IDs (users we have in our source data)
        managed_user_ids = set(username_to_id.values())

        # Process each group
        for group in omni_groups:
            group_id = group['id']
            group_name = group.get('displayName', group_id)

            # Get current members and separate into managed vs unmanaged
            current_managed = set()  # Users in our source data
            current_unmanaged = set()  # Embed users, external users, etc.
            current_member_details = {}  # Keep display names

            for member in group.get('members', []):
                member_id = member.get('value') if isinstance(member, dict) else member
                if member_id:
                    current_member_details[member_id] = member
                    if member_id in managed_user_ids:
                        current_managed.add(member_id)
                    else:
                        current_unmanaged.add(member_id)

            # Get desired managed members from source data
            desired_managed = desired_group_members.get(group_id, set())

            # Check if managed members need updating
            if current_managed != desired_managed:
                print(f"\n🔄 Updating group: {group_name} ({group_id})")
                print(f"  Current managed members: {len(current_managed)}")
                print(f"  Desired managed members: {len(desired_managed)}")
                if current_unmanaged:
                    print(f"  ⚠️  Preserving {len(current_unmanaged)} unmanaged members (embed users, external users, etc.)")

                members_to_add = desired_managed - current_managed
                members_to_remove = current_managed - desired_managed

                if members_to_add:
                    print(f"  ➕ Adding {len(members_to_add)} managed members")
                if members_to_remove:
                    print(f"  ➖ Removing {len(members_to_remove)} managed members")

                # Build final member list: unmanaged (preserved) + desired managed
                final_members = current_unmanaged | desired_managed

                # Build members list for API (needs both display and value fields)
                members_list = []

                # Add unmanaged members (preserve their existing display names)
                for user_id in current_unmanaged:
                    if user_id in current_member_details:
                        members_list.append(current_member_details[user_id])
                    else:
                        members_list.append({"value": user_id})

                # Add managed members from our source
                for user_id in desired_managed:
                    members_list.append({
                        "display": id_to_username.get(user_id, user_id),
                        "value": user_id
                    })

                try:
                    error_result['groups']['attempted'] += 1
                    if self.dry_run:
                        print(f"  🔍 [DRY RUN] Would update group membership")
                        error_result['groups']['succeeded'] += 1
                    else:
                        success = self.omni_client.update_group_members(
                            group_id,
                            group_name,
                            members_list,
                            display_name=group.get('displayName', group_name)
                        )
                        if success:
                            print(f"  ✅ Successfully updated group membership")
                            error_result['groups']['succeeded'] += 1
                        else:
                            print(f"  ❌ Failed to update group membership")
                except Exception as e:
                    print(f"  ❌ Failed to update group: {str(e)}")

                # Add delay to avoid rate limiting
                time.sleep(0.5)

        print("\n📊 Groups Sync Summary:")
        print(f"Total groups processed: {len(omni_groups)}")
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
                time.sleep(0.3)

            except Exception as e:
                user_name_for_error = user.get('userName', '[UNKNOWN USERNAME]')
                print(f"\n❌ An unexpected error occurred processing user {user_name_for_error}: {str(e)}")
                # Add delay even on error to avoid rate limiting
                time.sleep(0.3)
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
