# Omni User Manager

A tool for synchronizing users, groups, and user attributes with Omni.

## Installation

```bash
pip install omni-user-manager
```

## Configuration

Create a `.env` file with your Omni API credentials:

```env
OMNI_BASE_URL=your_omni_base_url/api
OMNI_API_KEY=your_omni_api_key
```

### Environment Variables Priority

The package prioritizes `.env` file values over global environment variables:

1. **.env file values** (highest priority)
2. **Global/System Environment Variables** (fallback when .env file doesn't exist or values are not set)

## Usage

You can use either `omni-um` or `omni-user-manager` as the CLI command. All examples below use `omni-um` for brevity, but both commands are fully supported and interchangeable.

The package uses a subcommand-based CLI structure for all major operations. Example usage:

### Common Commands

| Command | Description | Example |
|---------|-------------|---------|
| `sync` | Synchronize users, groups, and attributes | `omni-um sync --source csv --users data/users.csv --groups data/groups.csv` |
| `get-user-by-id [USER_ID]` | Get a user by ID (or all users if no ID) | `omni-um get-user-by-id` |
| `search-users --query QUERY` | Search users by email address (userName attribute, must be full email address) | `omni-um search-users --query "user@example.com"` |
| `get-user-attributes USER_ID` | Get a user's custom attributes by user ID | `omni-um get-user-attributes 123` |
| `get-group-by-id [GROUP_ID]` | Get a group by ID (or all groups if no ID) | `omni-um get-group-by-id` |
| `search-groups --query QUERY` | Search groups by displayName (must be full group name, exact match) | `omni-um search-groups --query "Admins"` |
| `get-group-members GROUP_ID` | Get all members of a group by group ID | `omni-um get-group-members 456` |
| `create-users USERS_FILE` | Create multiple users from a file (skips users that already exist) | `omni-um create-users data/users.json` |
| `update-user-attributes USERS_FILE` | Update user attributes only (not group memberships) | `omni-um update-user-attributes data/users.json` |
| `delete-user USER_ID [--yes]` | Delete a user by ID (with confirmation prompt unless --yes is provided) | `omni-um delete-user fb46d9ee-95e7-4256-abf0-832af6c27f6b` |
| `delete-users USERS_FILE [--yes]` | Delete multiple users by IDs from a file (CSV or JSON, with confirmation prompt unless --yes is provided) | `omni-um delete-users all_users.csv` |
| `export-users-json OUTPUT_FILE` | Export all users as JSON in SCIM 2.0 format | `omni-um export-users-json exported_users.json` |
| `export-users-csv OUTPUT_FILE` | Export all users as CSV (id, userName, displayName, active, email) | `omni-um export-users-csv all_users.csv` |
| `export-groups-json OUTPUT_FILE` | Export all groups as JSON | `omni-um export-groups-json all_groups.json` |

### User Operations vs Sync

**User Operations** (`create-users`, `update-user-attributes`, `delete-users`):
- **Purpose**: Individual user management operations
- **`update-user-attributes`**: Updates user attributes only (displayName, active, custom attributes)
- **Does NOT update**: Group memberships
- **Use when**: You need to update user properties without changing group assignments

**Sync Operations** (`sync`):
- **Purpose**: Comprehensive synchronization between data source and Omni
- **Updates**: Both user attributes AND group memberships
- **Modes**: Full sync, groups-only, or attributes-only
- **Use when**: You need to synchronize group memberships or perform comprehensive updates

> **Recommendation**: Use `sync` for most bulk update scenarios. Use `update-user-attributes` only when you specifically need to update user attributes without affecting group memberships.

### Sync Modes

The tool supports three sync modes:

1. **Full Sync** (default): Syncs both group memberships and user attributes
2. **Groups-only**: Only syncs group memberships
3. **Attributes-only**: Only syncs user attributes

### Using JSON Source

Use this when your user and group data is in a single JSON file following the SCIM 2.0 format:

```bash
# Full sync (groups and attributes)
omni-um sync --source json --users data/users.json

# Groups-only sync
omni-um sync --source json --users data/users.json --mode groups

# Attributes-only sync
omni-um sync --source json --users data/users.json --mode attributes
```

Example JSON format (`users.json`):
```json
{
  "Resources": [
    {
      "active": true,
      "displayName": "User Name",
      "emails": [
        {
          "primary": true,
          "value": "user@example.com"
        }
      ],
      "groups": [
        {
          "display": "group-name",
          "value": "group-id"
        }
      ],
      "id": "user-id",
      "userName": "user@example.com",
      "urn:omni:params:1.0:UserAttribute": {
        "gcp_project": ["project1", "project2"],
        "axel_user": "true",
        "omni_user_timezone": "America/New_York"
      }
    }
  ]
}
```

### Using CSV Source

Use this when your user data and group memberships are in separate CSV files:

```bash
# Full sync (groups and attributes)
omni-um sync --source csv --users data/users.csv --groups data/groups.csv

# Groups-only sync
omni-um sync --source csv --users data/users.csv --groups data/groups.csv --mode groups

# Attributes-only sync
omni-um sync --source csv --users data/users.csv --groups data/groups.csv --mode attributes
```

Example CSV formats:

`users.csv`:
```csv
id,userName,displayName,active,emails,userAttributes
user-id,user@example.com,User Name,true,{"primary": true, "value": "user@example.com"},{"gcp_project": ["project1", "project2"], "axel_user": "true", "omni_user_timezone": "America/New_York"}
```

`groups.csv`:
```csv
id,name,members
group-id,group-name,["user-id-1", "user-id-2"]
```

## Features

- Synchronize users, their group memberships, and attributes with Omni
- Support for both JSON and CSV data sources
- Three sync modes: full, groups-only, and attributes-only
- Detailed progress and error reporting
- Only updates when changes are needed
- Handles both adding and removing users from groups
- Updates user attributes using SCIM PUT operations
- Handles null values in user attributes appropriately
- Supports both single-value and multi-value attributes

## Development

To install in development mode:

```bash
git clone git@github.com:Hawkfry-Group/omni-user-manager.git
cd omni-user-manager
pip install -e .
```

## Notes

- User attributes are updated using SCIM PUT operations
- Null values in user attributes are handled by removing the attribute
- Multi-value attributes should be provided as arrays
- Single-value attributes should be provided as strings
- The tool will only update attributes that have changed from their current values in Omni

> **Important:** Omni assigns its own unique user IDs when users are created. Any update or delete operation (such as `update-user-attributes`) must use the Omni-assigned IDs, not placeholder or pre-specified IDs from your input files. To obtain the correct IDs, use the `search-users` or `export-users-json` command after creation and use those IDs for subsequent operations.

> **Note:** DELETE operations return 204 No Content on success. The CLI now handles this correctly and does not treat it as an error.

> **Note:** The `search-users` command requires the full email address (userName) for an exact match. Partial matches are not supported by the Omni API.

> **Note:** The `get-user-attributes` command returns the user's custom attributes (if any) as a JSON object. If the user has no custom attributes, an empty object is returned.

> **Note:** The `get-group-by-id` command returns a group by ID, or all groups if no ID is provided.

> **Note:** The `search-groups` command searches by group displayName and requires the full group name for an exact match.

> **Note:** The `get-group-members` command returns all members of a group by group ID as a JSON array.

> **Note:** The `create-users` command skips users that already exist (HTTP 409), reporting them in a 'skipped' list. The summary at the end shows succeeded, failed, and skipped counts.

> **Note:** The `update-user-attributes` command updates user attributes only (displayName, active, custom attributes) and does NOT modify group memberships. To update group memberships, use the `sync` command instead.

> **Note:** The `delete-user` and `delete-users` commands require confirmation before deleting users, unless the `--yes` flag is provided. This is to prevent accidental deletion. The CLI will prompt you to type 'yes' to confirm the operation.

> **Note:** The `export-groups-json` command exports all groups as a JSON array of group objects, each with fields such as id, displayName, and members.

> **Note:** The `export-users-json` command exports users in SCIM 2.0 format with a `Resources` array, making the exported file directly compatible with the `sync --source json` command for round-trip operations.

> **Note:** User and group history (audit) is not available via this CLI. To view audit history, please refer to the Omni platform's audit logs or logging dashboard.
