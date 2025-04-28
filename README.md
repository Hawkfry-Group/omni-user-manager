# Omni User Manager

A tool for synchronizing users, groups, and user attributes with Omni.

## Installation

```bash
pip install omni-user-manager
```

## Configuration

Create a `.env` file with your Omni API credentials:

```env
OMNI_BASE_URL=your_omni_base_url
OMNI_API_KEY=your_omni_api_key
```

## Usage

The package provides a command-line interface for syncing users, their group memberships, and attributes:

```bash
# Show available commands and options
omni-user-manager --help
```

### Sync Modes

The tool supports three sync modes:

1. **Full Sync** (default): Syncs both group memberships and user attributes
2. **Groups-only**: Only syncs group memberships
3. **Attributes-only**: Only syncs user attributes

### Using JSON Source

Use this when your user and group data is in a single JSON file following the SCIM 2.0 format:

```bash
# Full sync (groups and attributes)
omni-user-manager --source json --users data/users.json

# Groups-only sync
omni-user-manager --source json --users data/users.json --mode groups

# Attributes-only sync
omni-user-manager --source json --users data/users.json --mode attributes
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
omni-user-manager --source csv --users data/users.csv --groups data/groups.csv

# Groups-only sync
omni-user-manager --source csv --users data/users.csv --groups data/groups.csv --mode groups

# Attributes-only sync
omni-user-manager --source csv --users data/users.csv --groups data/groups.csv --mode attributes
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
- Multi-value attributes (like `gcp_project`) should be provided as arrays
- Single-value attributes (like `axel_user`) should be provided as strings
- The tool will only update attributes that have changed from their current values in Omni
