import logging
from typing import List, Optional
from datetime import datetime, timezone
from github import Github, GithubException
from github.Issue import Issue

logger = logging.getLogger(__name__)

class GitHubHandler:
    def __init__(self, token: str):
        self.client = Github(token)
        try:
            self.user = self.client.get_user()
            logger.info(f"Authenticated as: {self.user.login}")
        except GithubException as e:
            # GitHub App may not have access to /user endpoint
            if e.status == 403:
                logger.info("Authenticated as GitHub App")
                self.user = None
            else:
                raise
        self._check_token_expiration()
    
    def _check_token_expiration(self):
        """Check if the GitHub token is about to expire"""
        try:
            # For GitHub App, just verify we can make API calls
            # Don't try to get user info as it may not have that permission
            rate_limit = self.client.rate_limiting
            logger.info(f"Rate limit: {rate_limit[0]}/{rate_limit[1]} (remaining/limit)")
            logger.info("✅ GitHub authentication successful")
            
        except GithubException as e:
            logger.error(f"Failed to check token status: {e}")
            if e.status == 401:
                logger.error("❌ Token is invalid or expired! Please update authentication.")
                raise
        except Exception as e:
            logger.warning(f"Could not check token details: {e}")
    
    def get_unprocessed_issues(self, repo_name: str, processed_label: str) -> List[Issue]:
        try:
            repo = self.client.get_repo(repo_name)
            all_issues = repo.get_issues(state='open')
            
            unprocessed = []
            for issue in all_issues:
                if issue.pull_request:
                    continue
                
                label_names = [label.name for label in issue.labels]
                if processed_label not in label_names:
                    unprocessed.append(issue)
            
            logger.info(f"Found {len(unprocessed)} unprocessed issues in {repo_name}")
            return unprocessed
        
        except GithubException as e:
            logger.error(f"Failed to get issues from {repo_name}: {e}")
            return []
    
    def get_existing_analysis(self, issue: Issue) -> Optional[dict]:
        """
        Check if the bot has already posted an analysis comment
        Returns dict with 'analysis' and 'suggested_labels' if found, None otherwise
        """
        try:
            comments = issue.get_comments()
            
            for comment in comments:
                # Check if this is a bot analysis comment
                if "## 🤖 自動分析結果" in comment.body:
                    logger.info(f"Found existing analysis comment in issue #{issue.number}")
                    
                    # Extract analysis text (between header and footer)
                    body = comment.body
                    
                    # Remove header
                    if "## 🤖 自動分析結果" in body:
                        body = body.split("## 🤖 自動分析結果", 1)[1]
                    
                    # Remove footer
                    if "---" in body:
                        body = body.split("---")[0]
                    
                    analysis_text = body.strip()
                    
                    # Parse labels from analysis
                    suggested_labels = []
                    lines = analysis_text.split('\n')
                    in_labels_section = False
                    
                    for line in lines:
                        if "## 提案ラベル" in line or "##提案ラベル" in line:
                            in_labels_section = True
                            continue
                        elif line.startswith("##"):
                            in_labels_section = False
                        
                        if in_labels_section and line.strip().startswith("-"):
                            label = line.strip()[1:].strip()
                            if label:
                                label = label.replace('**', '')
                                if '（' in label:
                                    label = label.split('（')[0].strip()
                                elif '(' in label:
                                    label = label.split('(')[0].strip()
                                if label:
                                    suggested_labels.append(label)
                    
                    return {
                        "analysis": analysis_text,
                        "suggested_labels": suggested_labels
                    }
            
            return None
            
        except GithubException as e:
            logger.error(f"Failed to get comments from issue #{issue.number}: {e}")
            return None
    
    def add_comment(self, issue: Issue, comment: str) -> bool:
        try:
            issue.create_comment(comment)
            logger.info(f"Added comment to issue #{issue.number}")
            return True
        except GithubException as e:
            logger.error(f"Failed to add comment to issue #{issue.number}: {e}")
            return False
    
    def get_repository_labels(self, repo_name: str) -> List[str]:
        """Get list of all labels in the repository"""
        try:
            repo = self.client.get_repo(repo_name)
            labels = [label.name for label in repo.get_labels()]
            logger.info(f"Found {len(labels)} labels in {repo_name}")
            return labels
        except GithubException as e:
            logger.error(f"Failed to get labels from {repo_name}: {e}")
            return []
    
    def add_label(self, issue: Issue, label: str) -> bool:
        try:
            repo = issue.repository
            try:
                repo.get_label(label)
            except GithubException:
                if label == "bot-processed":
                    logger.info(f"Label 'bot-processed' does not exist - creating it")
                    try:
                        repo.create_label("bot-processed", "d4c5f9", "Issues processed by bot")
                        logger.info(f"Created label 'bot-processed'")
                    except GithubException as create_error:
                        logger.error(f"Failed to create label 'bot-processed': {create_error}")
                        return False
                else:
                    logger.warning(f"Label '{label}' does not exist in repository - skipping")
                    return False
            
            issue.add_to_labels(label)
            logger.info(f"Added label '{label}' to issue #{issue.number}")
            return True
        except GithubException as e:
            logger.error(f"Failed to add label to issue #{issue.number}: {e}")
            return False
    
    def create_branch(self, repo_name: str, branch_name: str, from_branch: str = "main") -> Optional[str]:
        try:
            repo = self.client.get_repo(repo_name)
            
            try:
                base_branch = repo.get_branch(from_branch)
            except GithubException:
                base_branch = repo.get_branch(repo.default_branch)
            
            base_sha = base_branch.commit.sha
            ref = f"refs/heads/{branch_name}"
            
            try:
                repo.create_git_ref(ref, base_sha)
                logger.info(f"Created branch: {branch_name}")
                return branch_name
            except GithubException as e:
                if e.status == 422:
                    logger.warning(f"Branch {branch_name} already exists")
                    return branch_name
                raise
        
        except GithubException as e:
            logger.error(f"Failed to create branch {branch_name}: {e}")
            return None
    
    def create_pull_request(self, repo_name: str, title: str, body: str, 
                          head_branch: str, base_branch: str = "main") -> Optional[str]:
        try:
            repo = self.client.get_repo(repo_name)
            
            try:
                base = base_branch
                repo.get_branch(base)
            except GithubException:
                base = repo.default_branch
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base
            )
            
            logger.info(f"Created PR #{pr.number}: {pr.html_url}")
            return pr.html_url
        
        except GithubException as e:
            logger.error(f"Failed to create PR: {e}")
            return None
