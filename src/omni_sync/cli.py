"""
Omni User Manager CLI
-------------------
Command-line interface for Omni User Manager.

A tool for synchronizing users, groups, and user attributes with Omni.

Usage:
    # Full sync (groups and attributes)
    omni-user-manager --source json --users <path>
    omni-user-manager --source csv --users <path> --groups <path>

    # Groups-only sync
    omni-user-manager --source json --users <path> --mode groups
    omni-user-manager --source csv --users <path> --groups <path> --mode groups

    # Attributes-only sync
    omni-user-manager --source json --users <path> --mode attributes
    omni-user-manager --source csv --users <path> --groups <path> --mode attributes

Sync Modes:
    all (default)     Sync both group memberships and user attributes
    groups           Only sync group memberships
    attributes       Only sync user attributes

Data Sources:
    json            Single JSON file containing user and group data
    csv             Separate CSV files for users and groups
"""

import argparse
import sys
from typing import Optional
from dotenv import load_dotenv
import os

from .api.omni_client import OmniClient
from .data_sources.csv_source import CSVDataSource
from .data_sources.json_source import JSONDataSource
from .main import OmniSync

def main() -> int:
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        description='Omni User Manager - Synchronize users, groups, and attributes with Omni',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add arguments
    parser.add_argument('--source', choices=['csv', 'json'], required=True,
                       help='Data source type (csv or json)')
    parser.add_argument('--users', required=True,
                       help='Path to users file')
    parser.add_argument('--groups',
                       help='Path to groups CSV file (required for CSV source)')
    parser.add_argument('--mode', choices=['all', 'groups', 'attributes'], default='all',
                       help='Sync mode: all (default) syncs both groups and attributes, groups-only, or attributes-only')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    base_url = os.getenv('OMNI_BASE_URL')
    api_key = os.getenv('OMNI_API_KEY')
    
    if not base_url or not api_key:
        print("Error: OMNI_BASE_URL and OMNI_API_KEY must be set in .env file")
        return 1

    # Initialize Omni client
    omni_client = OmniClient(base_url, api_key)

    # Initialize data source
    if args.source == 'csv':
        if not args.groups:
            print("Error: --groups is required when using CSV source")
            return 1
        data_source = CSVDataSource(args.users, args.groups)
        print("📄 Using CSV data source")
    elif args.source == 'json':
        data_source = JSONDataSource(args.users)
        print("📄 Using JSON data source")
    else:
        print("Error: Invalid source type")
        return 1

    # Create sync instance and run
    sync = OmniSync(data_source, omni_client)
    
    if args.mode == 'all':
        print("🔄 Running full sync (groups and attributes)")
        results = sync.sync_all()
    elif args.mode == 'groups':
        print("🔄 Running groups-only sync")
        results = sync.sync_groups()
    elif args.mode == 'attributes':
        print("🔄 Running attributes-only sync")
        results = sync.sync_attributes()
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 