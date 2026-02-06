import os
import shutil
import subprocess
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class GitHandler:
    """Handle git operations for repository cloning and committing"""
    
    def __init__(self, work_dir: str, github_token: Optional[str] = None):
        self.work_dir = Path(work_dir)
        self.github_token = github_token
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_git_command(self, command: list, cwd: Optional[Path] = None) -> tuple[int, str, str]:
        """Run a git command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.work_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(command)}")
            return 1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Failed to run git command: {e}")
            return 1, "", str(e)
    
    def clone_repository(self, repo_name: str, branch: str = "main") -> Optional[Path]:
        """Clone a repository to the work directory"""
        repo_path = self.work_dir / repo_name.replace("/", "_")
        
        # Clean up if already exists
        if repo_path.exists():
            shutil.rmtree(repo_path)
        
        # Build clone URL with authentication
        if self.github_token:
            clone_url = f"https://x-access-token:{self.github_token}@github.com/{repo_name}.git"
        else:
            clone_url = f"https://github.com/{repo_name}.git"
        
        logger.info(f"Cloning {repo_name} to {repo_path}")
        
        exit_code, stdout, stderr = self._run_git_command(
            ["git", "clone", "--depth", "1", "--branch", branch, clone_url, str(repo_path)]
        )
        
        if exit_code != 0:
            # Try with default branch if specified branch doesn't exist
            logger.warning(f"Failed to clone branch {branch}, trying default branch")
            exit_code, stdout, stderr = self._run_git_command(
                ["git", "clone", "--depth", "1", clone_url, str(repo_path)]
            )
            
            if exit_code != 0:
                logger.error(f"Failed to clone repository: {stderr}")
                return None
        
        logger.info(f"Successfully cloned {repo_name}")
        return repo_path
    
    def checkout_branch(self, repo_path: Path, branch: str, create: bool = True) -> bool:
        """Checkout a branch, optionally creating it"""
        if create:
            exit_code, stdout, stderr = self._run_git_command(
                ["git", "checkout", "-b", branch],
                cwd=repo_path
            )
        else:
            exit_code, stdout, stderr = self._run_git_command(
                ["git", "checkout", branch],
                cwd=repo_path
            )
        
        if exit_code != 0:
            logger.error(f"Failed to checkout branch {branch}: {stderr}")
            return False
        
        logger.info(f"Checked out branch: {branch}")
        return True
    
    def commit_changes(self, repo_path: Path, message: str, author_name: str = "GitHub Issues Checker Bot", 
                      author_email: str = "bot@github-issues-checker.local") -> bool:
        """Commit all changes in the repository"""
        # Configure git user
        self._run_git_command(["git", "config", "user.name", author_name], cwd=repo_path)
        self._run_git_command(["git", "config", "user.email", author_email], cwd=repo_path)
        
        # Add all changes
        exit_code, stdout, stderr = self._run_git_command(
            ["git", "add", "-A"],
            cwd=repo_path
        )
        
        if exit_code != 0:
            logger.error(f"Failed to stage changes: {stderr}")
            return False
        
        # Check if there are changes to commit
        exit_code, stdout, stderr = self._run_git_command(
            ["git", "diff", "--staged", "--quiet"],
            cwd=repo_path
        )
        
        if exit_code == 0:
            logger.warning("No changes to commit")
            return False
        
        # Commit changes
        exit_code, stdout, stderr = self._run_git_command(
            ["git", "commit", "-m", message],
            cwd=repo_path
        )
        
        if exit_code != 0:
            logger.error(f"Failed to commit changes: {stderr}")
            return False
        
        logger.info(f"Committed changes: {message}")
        return True
    
    def push_branch(self, repo_path: Path, branch: str) -> bool:
        """Push a branch to remote"""
        exit_code, stdout, stderr = self._run_git_command(
            ["git", "push", "-u", "origin", branch],
            cwd=repo_path
        )
        
        if exit_code != 0:
            logger.error(f"Failed to push branch {branch}: {stderr}")
            return False
        
        logger.info(f"Pushed branch: {branch}")
        return True
    
    def cleanup_repository(self, repo_path: Path):
        """Remove cloned repository"""
        if repo_path.exists():
            shutil.rmtree(repo_path)
            logger.info(f"Cleaned up repository: {repo_path}")
