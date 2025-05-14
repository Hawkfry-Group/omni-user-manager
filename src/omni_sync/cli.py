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
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print("ERROR: The 'python-dotenv' library is not found in the current Python environment.")
    print("This is a required dependency for 'omni-user-manager' to load configuration from .env files.")
    print("\\nPlease ensure 'omni-user-manager' and its dependencies are correctly installed.")
    print("If you are using a virtual environment, make sure it is activated.")
    print("You can try reinstalling the package or installing the dependency manually:")
    print("  pip install omni-user-manager  (or pip install --upgrade omni-user-manager)")
    print("  Alternatively, to install only python-dotenv: pip install python-dotenv")
    sys.exit(1)
import os
from pathlib import Path
import dotenv # For find_dotenv

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
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug print statements for .env loading')
    
    # Parse arguments
    args = parser.parse_args()
    
    # --- Manual .env read test (conditional) ---
    if args.debug:
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        print("DEBUG: Attempting manual read of .env file...")
        manual_env_path = os.path.join(os.getcwd(), ".env")
        try:
            with open(manual_env_path, 'r') as f:
                lines = [f.readline().strip() for _ in range(2)] # Read first 2 lines
                print(f"DEBUG: Manual read SUCCESS. First 2 lines: {lines}")
        except Exception as e:
            print(f"DEBUG: Manual read FAILED: {e}")
    # --- End manual .env read test ---
    
    env_file_path_found = dotenv.find_dotenv(usecwd=True) 
    if args.debug:
        print(f"DEBUG: dotenv.find_dotenv(usecwd=True) result: '{env_file_path_found}'")

    # Use verbose in load_dotenv only if debug is enabled
    loaded_dotenv = load_dotenv(verbose=args.debug, override=True) 
    if args.debug:
        print(f"DEBUG: load_dotenv(verbose={args.debug}) result: {loaded_dotenv}") 

    # Fallback to manual parsing if load_dotenv fails or variables aren't set
    if not loaded_dotenv or not os.getenv('OMNI_BASE_URL') or not os.getenv('OMNI_API_KEY'):
        if args.debug:
            print("DEBUG: load_dotenv failed or variables not set, attempting manual parse...")
        if env_file_path_found and os.path.exists(env_file_path_found):
            try:
                with open(env_file_path_found, 'r') as f:
                    for line_number, line in enumerate(f):
                        line = line.strip()
                        if not line or line.startswith('#') or '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        key = key.strip()
                        if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))):
                            value = value[1:-1]
                        os.environ[key] = value
                        if args.debug:
                            print(f"DEBUG: Manually set os.environ['{key}'] = '{value}'")
                if os.getenv('OMNI_BASE_URL') and os.getenv('OMNI_API_KEY'):
                    if args.debug:
                        print("DEBUG: Variables successfully set by manual parse.")
                elif args.debug: # only print if debug is on and variables still not set
                    print("DEBUG: Variables NOT set even after manual parse.")        
            except Exception as e:
                if args.debug:
                    print(f"DEBUG: Manual parse FAILED: {e}")
        elif args.debug: # only print if debug is on and file not found for manual parse
            print("DEBUG: .env file not found by find_dotenv for manual parse, or path doesn't exist.")

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