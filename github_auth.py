import os
import logging
from typing import Optional
from github import Github, GithubIntegration

logger = logging.getLogger(__name__)

class GitHubAppAuth:
    """
    GitHub App authentication handler
    Use this for long-term operation with automatic token renewal
    """
    
    def __init__(self, app_id: str, private_key_path: str, installation_id: str):
        self.app_id = int(app_id)
        self.installation_id = int(installation_id)
        
        if not os.path.exists(private_key_path):
            raise FileNotFoundError(f"Private key file not found: {private_key_path}")
        
        with open(private_key_path, 'r') as key_file:
            self.private_key = key_file.read()
        
        self.integration = GithubIntegration(self.app_id, self.private_key)
        logger.info(f"GitHub App initialized (App ID: {self.app_id})")
    
    def get_access_token(self) -> str:
        """
        Get an installation access token
        This token is valid for 1 hour and automatically renewed
        """
        auth = self.integration.get_access_token(self.installation_id)
        token = auth.token
        logger.info(f"Generated new installation token (expires: {auth.expires_at})")
        return token
    
    def get_github_client(self) -> Github:
        """
        Get an authenticated GitHub client with auto-renewing token
        """
        token = self.get_access_token()
        return Github(token)

def get_github_client_from_env() -> Github:
    """
    Get GitHub client using environment variables
    Supports both PAT and GitHub App authentication
    """
    # Check for GitHub App credentials first (recommended)
    app_id = os.getenv("GITHUB_APP_ID")
    private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")
    
    if app_id and private_key_path and installation_id:
        logger.info("Using GitHub App authentication (recommended)")
        app_auth = GitHubAppAuth(app_id, private_key_path, installation_id)
        return app_auth.get_github_client()
    
    # Fall back to Personal Access Token
    token = os.getenv("GITHUB_TOKEN")
    if token:
        logger.info("Using Personal Access Token authentication")
        return Github(token)
    
    raise ValueError(
        "No GitHub authentication found. "
        "Please set either GITHUB_TOKEN or GitHub App credentials "
        "(GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_PATH, GITHUB_APP_INSTALLATION_ID)"
    )
