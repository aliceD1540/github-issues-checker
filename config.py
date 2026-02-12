import os
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    # GitHub App authentication (recommended for long-term operation)
    GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
    GITHUB_APP_PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    GITHUB_APP_INSTALLATION_ID = os.getenv("GITHUB_APP_INSTALLATION_ID")
    
    # Personal Access Token (fallback)
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    GITHUB_REPOS = os.getenv("GITHUB_REPOS", "").split(",")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    COPILOT_INSTRUCTIONS_FILE = os.getenv("COPILOT_INSTRUCTIONS_FILE", "copilot-instructions.md")
    
    # Disable Copilot SDK when running in cron (TTY issues)
    DISABLE_COPILOT = os.getenv("DISABLE_COPILOT", "false").lower() in ("true", "1", "yes")
    
    # Working directory for cloning repositories
    WORK_DIR = os.getenv("WORK_DIR", "/tmp/github-issues-checker")
    
    BOT_PROCESSED_LABEL = "bot-processed"
    
    @classmethod
    def has_github_app_auth(cls) -> bool:
        return all([cls.GITHUB_APP_ID, cls.GITHUB_APP_PRIVATE_KEY_PATH, cls.GITHUB_APP_INSTALLATION_ID])
    
    @classmethod
    def has_token_auth(cls) -> bool:
        return bool(cls.GITHUB_TOKEN)
    
    @classmethod
    def validate(cls) -> List[str]:
        errors = []
        
        # Check for GitHub authentication
        if not cls.has_github_app_auth() and not cls.has_token_auth():
            errors.append(
                "No GitHub authentication found. "
                "Please set either GITHUB_TOKEN or GitHub App credentials "
                "(GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_PATH, GITHUB_APP_INSTALLATION_ID)"
            )
        
        if cls.has_github_app_auth():
            if not os.path.exists(cls.GITHUB_APP_PRIVATE_KEY_PATH):
                errors.append(f"GitHub App private key file not found: {cls.GITHUB_APP_PRIVATE_KEY_PATH}")
        
        if not cls.GITHUB_REPOS or cls.GITHUB_REPOS == ['']:
            errors.append("GITHUB_REPOS environment variable is required")
        
        for repo in cls.GITHUB_REPOS:
            if repo and '/' not in repo:
                errors.append(f"Invalid repository format: {repo}. Expected format: owner/repo")
        
        return errors
    
    @classmethod
    def setup_logging(cls):
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
