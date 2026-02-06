#!/usr/bin/env python3
"""
Helper script to list GitHub App installations
Usage: python get_installation_id.py
"""
import os
from github import GithubIntegration
from dotenv import load_dotenv

load_dotenv()

def main():
    app_id = os.getenv("GITHUB_APP_ID")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    
    if not app_id or not private_key_path:
        print("Error: GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY_PATH must be set in .env")
        return
    
    if not os.path.exists(private_key_path):
        print(f"Error: Private key file not found: {private_key_path}")
        return
    
    with open(private_key_path, 'r') as key_file:
        private_key = key_file.read()
    
    integration = GithubIntegration(int(app_id), private_key)
    
    print("GitHub App Installations:")
    print("-" * 60)
    
    installations = list(integration.get_installations())
    
    if not installations:
        print("No installations found. Please install the GitHub App first.")
        return
    
    for installation in installations:
        print(f"\nInstallation ID: {installation.id}")
        print(f"Account: {installation.account.login}")
        print(f"Account Type: {installation.account.type}")
        print(f"Target Type: {installation.target_type}")
        
        # Get repositories for this installation
        auth = integration.get_access_token(installation.id)
        from github import Github
        g = Github(auth.token)
        
        try:
            repos = list(installation.get_repos())
            print(f"Repositories ({len(repos)}):")
            for repo in repos[:10]:  # Show first 10
                print(f"  - {repo.full_name}")
            if len(repos) > 10:
                print(f"  ... and {len(repos) - 10} more")
        except Exception as e:
            print(f"  Could not fetch repositories: {e}")
        
        print("-" * 60)
    
    print("\n✅ Add this to your .env file:")
    if len(installations) == 1:
        print(f"GITHUB_APP_INSTALLATION_ID={installations[0].id}")
    else:
        print("# Choose one of the Installation IDs above:")
        for installation in installations:
            print(f"# GITHUB_APP_INSTALLATION_ID={installation.id}  # {installation.account.login}")

if __name__ == "__main__":
    main()
