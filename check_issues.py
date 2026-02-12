#!/usr/bin/env python3
import asyncio
import logging
from typing import List
from pathlib import Path
from github.Issue import Issue

from config import Config
from github_handler import GitHubHandler
from github_auth import get_github_client_from_env
from git_handler import GitHandler
from copilot_handler import CopilotHandler

logger = logging.getLogger(__name__)

async def process_issue(issue: Issue, github_handler: GitHubHandler, git_handler: GitHandler,
                       copilot_handler: CopilotHandler | None, repo_name: str, github_token: str) -> bool:
    logger.info(f"Processing issue #{issue.number}: {issue.title}")
    
    issue_data = {
        "title": issue.title,
        "body": issue.body or "",
        "number": issue.number,
        "repo": repo_name,
        "url": issue.html_url
    }
    
    try:
        # Step 1: Analyze issue
        if not copilot_handler:
            logger.info(f"Copilot disabled - adding label only for issue #{issue.number}")
            github_handler.add_label(issue, Config.BOT_PROCESSED_LABEL)
            github_handler.add_comment(issue, 
                "👀 このissueは検出されましたが、自動分析・実装機能は現在無効です。手動で対応してください。")
            return False
        
        logger.info(f"Analyzing issue #{issue.number} with Copilot...")
        analysis_result = await copilot_handler.analyze_issue(issue_data)
        
        # Check for insufficient information
        if analysis_result.get("insufficient_info", False):
            logger.warning(f"Issue #{issue.number} has insufficient information - stopping processing")
            
            # Clean up the analysis text by removing the INSUFFICIENT_INFO marker
            analysis_text = analysis_result["analysis"].replace("INSUFFICIENT_INFO", "").strip()
            
            comment_body = f"""## ⚠️ 情報不足により処理を中断しました

{analysis_text}

---
**次のステップ**: 上記の情報を追加していただければ、再度自動処理を試みます。

*この分析は GitHub Copilot SDK により自動生成されました*
"""
            
            logger.info(f"Adding insufficient info comment to issue #{issue.number}...")
            if not github_handler.add_comment(issue, comment_body):
                logger.error(f"Failed to add comment to issue #{issue.number}")
            
            # Add "needs-more-info" label
            github_handler.add_label(issue, "needs-more-info")
            
            # Mark as processed to avoid re-processing the same incomplete issue
            github_handler.add_label(issue, Config.BOT_PROCESSED_LABEL)
            
            return False
        
        if not analysis_result["completed"]:
            logger.error(f"Failed to analyze issue #{issue.number}")
            return False
        
        analysis_text = analysis_result["analysis"]
        suggested_labels = analysis_result["suggested_labels"]
        
        logger.info(f"Analysis text length: {len(analysis_text)}")
        logger.info(f"Analysis text preview: {analysis_text[:200]}...")
        logger.info(f"Suggested labels: {suggested_labels}")
        
        # Step 2: Add comment with analysis
        comment_body = f"""## 🤖 自動分析結果

{analysis_text}

---
*この分析は GitHub Copilot SDK により自動生成されました*
"""
        
        logger.info(f"Adding analysis comment to issue #{issue.number}...")
        if not github_handler.add_comment(issue, comment_body):
            logger.error(f"Failed to add comment to issue #{issue.number}")
            return False
        
        # Step 3: Add labels
        logger.info(f"Adding labels to issue #{issue.number}...")
        for label in suggested_labels:
            github_handler.add_label(issue, label)
        
        # Step 4: Clone repository
        logger.info(f"Cloning repository {repo_name}...")
        repo_path = git_handler.clone_repository(repo_name)
        
        if not repo_path:
            logger.error(f"Failed to clone repository {repo_name}")
            return False
        
        try:
            # Step 5: Create and checkout branch
            branch_name = f"fix/issue-{issue.number}"
            logger.info(f"Creating branch: {branch_name}")
            
            if not git_handler.checkout_branch(repo_path, branch_name, create=True):
                logger.error(f"Failed to create branch {branch_name}")
                return False
            
            # Also create remote branch
            github_handler.create_branch(repo_name, branch_name)
            
            # Step 6: Implement fix using Copilot
            logger.info(f"Implementing fix for issue #{issue.number} with Copilot...")
            logger.info(f"This may take several minutes as Copilot analyzes and modifies code...")
            
            implementation_result = await copilot_handler.implement_fix(issue_data, str(repo_path))
            
            if not implementation_result["success"]:
                logger.error(f"Failed to implement fix for issue #{issue.number}")
                return False
            
            logger.info(f"Implementation completed: {implementation_result['message'][:200]}...")
            
            # Step 7: Commit changes
            commit_message = f"""Fix: {issue.title} (#{issue.number})

{analysis_text[:500]}

Closes #{issue.number}
"""
            
            logger.info(f"Committing changes for issue #{issue.number}...")
            if not git_handler.commit_changes(repo_path, commit_message):
                logger.warning(f"No changes to commit for issue #{issue.number}")
                github_handler.add_comment(issue, 
                    "⚠️ Copilotによる分析は完了しましたが、コードの変更は必要ありませんでした。")
                return False
            
            # Step 8: Push changes
            logger.info(f"Pushing branch {branch_name}...")
            if not git_handler.push_branch(repo_path, branch_name):
                logger.error(f"Failed to push branch {branch_name}")
                return False
            
            # Step 9: Create PR
            pr_title = f"Fix: {issue.title} (#{issue.number})"
            pr_body = f"""## 概要
このPRはissue #{issue.number} に対する自動対応です。

## 関連Issue
Closes #{issue.number}

## 分析結果
{analysis_text}

## 実装内容
{implementation_result['message']}

---
⚠️ **重要**: このPRは自動生成されました。**必ずコードレビューを行ってください。**

### レビュー時の確認ポイント
- [ ] 実装が要件を満たしているか
- [ ] コードの品質は適切か
- [ ] テストは必要か、テストは含まれているか
- [ ] セキュリティ上の問題はないか
- [ ] パフォーマンスへの影響はないか

*Generated by GitHub Copilot SDK*
"""
            
            logger.info(f"Creating PR for issue #{issue.number}...")
            pr_url = github_handler.create_pull_request(
                repo_name=repo_name,
                title=pr_title,
                body=pr_body,
                head_branch=branch_name
            )
            
            if pr_url:
                logger.info(f"Successfully created PR: {pr_url}")
                github_handler.add_comment(issue, f"✅ 修正を実装してプルリクエストを作成しました: {pr_url}")
                github_handler.add_label(issue, Config.BOT_PROCESSED_LABEL)
                return True
            else:
                logger.error(f"Failed to create PR for issue #{issue.number}")
                return False
        
        finally:
            # Cleanup: Remove cloned repository
            logger.info(f"Cleaning up repository {repo_name}...")
            git_handler.cleanup_repository(repo_path)
    
    except Exception as e:
        logger.error(f"Error processing issue #{issue.number}: {e}", exc_info=True)
        return False

async def process_repository(repo_name: str, github_handler: GitHubHandler, git_handler: GitHandler,
                            copilot_handler: CopilotHandler | None, github_token: str):
    logger.info(f"=== Processing repository: {repo_name} ===")
    
    issues = github_handler.get_unprocessed_issues(repo_name, Config.BOT_PROCESSED_LABEL)
    
    if not issues:
        logger.info(f"No unprocessed issues found in {repo_name}")
        return
    
    success_count = 0
    for issue in issues:
        try:
            if await process_issue(issue, github_handler, git_handler, copilot_handler, repo_name, github_token):
                success_count += 1
            
            await asyncio.sleep(5)  # Increased delay between issues
        
        except Exception as e:
            logger.error(f"Unexpected error processing issue #{issue.number}: {e}", exc_info=True)
    
    logger.info(f"Completed {repo_name}: {success_count}/{len(issues)} issues processed successfully")

async def main():
    Config.setup_logging()
    logger.info("Starting GitHub Issues Checker (with auto-implementation)")
    
    errors = Config.validate()
    if errors:
        for error in errors:
            logger.error(error)
        logger.error("Configuration validation failed. Exiting.")
        return 1
    
    # Initialize GitHub authentication
    try:
        github_client = get_github_client_from_env()
        github_handler = GitHubHandler.__new__(GitHubHandler)
        github_handler.client = github_client
        try:
            github_handler.user = github_client.get_user()
            logger.info(f"Authenticated as: {github_handler.user.login}")
        except Exception:
            github_handler.user = None
            logger.info("Authenticated as GitHub App")
        github_handler._check_token_expiration()
    except Exception as e:
        logger.error(f"GitHub authentication failed: {e}")
        return 1
    
    # Get GitHub token for git operations
    github_token = None
    if Config.has_github_app_auth():
        from github_auth import GitHubAppAuth
        app_auth = GitHubAppAuth(
            Config.GITHUB_APP_ID,
            Config.GITHUB_APP_PRIVATE_KEY_PATH,
            Config.GITHUB_APP_INSTALLATION_ID
        )
        github_token = app_auth.get_access_token()
    elif Config.has_token_auth():
        github_token = Config.GITHUB_TOKEN
    
    # Initialize handlers
    git_handler = GitHandler(Config.WORK_DIR, github_token)
    
    # Skip Copilot SDK initialization if disabled (e.g., when running in cron)
    copilot_handler = None
    if not Config.DISABLE_COPILOT:
        copilot_handler = CopilotHandler(Config.COPILOT_INSTRUCTIONS_FILE)
    
    try:
        if copilot_handler:
            await copilot_handler.start()
        else:
            logger.info("Copilot SDK disabled - running in analysis-only mode")
        
        repos = [repo.strip() for repo in Config.GITHUB_REPOS if repo.strip()]
        
        for repo_name in repos:
            try:
                await process_repository(repo_name, github_handler, git_handler, copilot_handler, github_token)
            except Exception as e:
                logger.error(f"Error processing repository {repo_name}: {e}", exc_info=True)
    
    finally:
        if copilot_handler:
            await copilot_handler.stop()
    
    logger.info("GitHub Issues Checker completed")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
