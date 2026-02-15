import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from copilot import CopilotClient

logger = logging.getLogger(__name__)

class CopilotHandler:
    def __init__(self, instructions_file: Optional[str] = None):
        self.client = None
        self.instructions_file = instructions_file or "copilot-instructions.md"
        self.custom_instructions = self._load_instructions()
        self.copilot_cli_path = self._find_copilot_cli_path()
    
    def _find_copilot_cli_path(self) -> Optional[str]:
        """Find the full path to copilot CLI command"""
        import shutil
        
        # Try to find copilot in PATH
        copilot_path = shutil.which('copilot')
        if copilot_path:
            logger.info(f"Found copilot CLI at: {copilot_path}")
            return copilot_path
        
        # Common installation paths to check
        common_paths = [
            os.path.expanduser("~/.nvm/versions/node/*/bin/copilot"),
            "/usr/local/bin/copilot",
            "/usr/bin/copilot",
        ]
        
        import glob
        for pattern in common_paths:
            matches = glob.glob(pattern)
            if matches:
                # Sort to get the latest version if multiple exist
                matches.sort(reverse=True)
                logger.info(f"Found copilot CLI at: {matches[0]}")
                return matches[0]
        
        logger.warning("Could not find copilot CLI path. Using default 'copilot' command.")
        return None
    
    def _load_instructions(self) -> Optional[str]:
        if not os.path.exists(self.instructions_file):
            logger.warning(f"Instructions file not found: {self.instructions_file}")
            return None
        
        try:
            with open(self.instructions_file, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded custom instructions from {self.instructions_file}")
            return content
        except Exception as e:
            logger.error(f"Failed to load instructions file: {e}")
            return None
    
    def _load_repo_instructions(self, repo_path: str) -> Optional[str]:
        """Load repository-specific instructions from .github/copilot-instructions.md"""
        repo_instructions_path = os.path.join(repo_path, ".github", "copilot-instructions.md")
        
        if not os.path.exists(repo_instructions_path):
            logger.debug(f"No repository-specific instructions found at {repo_instructions_path}")
            return None
        
        try:
            with open(repo_instructions_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Loaded repository-specific instructions from {repo_instructions_path}")
            return content
        except Exception as e:
            logger.error(f"Failed to load repository instructions: {e}")
            return None
    
    async def start(self):
        # Configure CopilotClient with explicit CLI path if found
        client_options = {}
        if self.copilot_cli_path:
            client_options["cli_path"] = self.copilot_cli_path
        
        self.client = CopilotClient(client_options if client_options else None)
        await self.client.start()
        logger.info("Copilot client started")
    
    async def stop(self):
        if self.client:
            await self.client.stop()
            logger.info("Copilot client stopped")
    
    async def analyze_issue(self, issue_data: Dict[str, Any], available_labels: List[str] = None) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Copilot client not started")
        
        session_config = {"model": "claude-sonnet-4.5"}
        
        if self.custom_instructions:
            session_config["system_message"] = {
                "content": self.custom_instructions
            }
        
        result = {
            "analysis": "",
            "suggested_labels": [],
            "action_plan": "",
            "completed": False,
            "insufficient_info": False
        }
        
        try:
            session = await self.client.create_session(session_config)
            
            prompt = self._build_analysis_prompt(issue_data, available_labels)
            logger.info(f"Sending analysis prompt for issue #{issue_data['number']}")
            
            # Use send_and_wait for simpler response handling
            # Increase timeout for GitHub Actions environment (slower response)
            response = await session.send_and_wait({"prompt": prompt}, timeout=300)
            
            await session.destroy()
            
            if response and hasattr(response.data, 'content'):
                result["analysis"] = response.data.content
                result["completed"] = True
                logger.info(f"Analysis completed: {len(result['analysis'])} characters")
                
                # Check for insufficient information
                if "INSUFFICIENT_INFO" in result["analysis"]:
                    result["insufficient_info"] = True
                    result["completed"] = False
                    logger.warning(f"Issue #{issue_data['number']} has insufficient information")
            else:
                logger.warning("No analysis content received")
                result["analysis"] = "分析結果を取得できませんでした。Copilot SDKの応答がありませんでした。"
                result["completed"] = False
            
            self._parse_analysis(result)
            
        except asyncio.TimeoutError:
            logger.error("Analysis timed out after 300 seconds")
            result["analysis"] = "分析がタイムアウトしました。issueが複雑すぎる可能性があります。"
            result["completed"] = False
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            result["analysis"] = f"分析中にエラーが発生しました: {str(e)}"
            result["completed"] = False
        
        return result
    
    def _build_analysis_prompt(self, issue_data: Dict[str, Any], available_labels: List[str] = None) -> str:
        labels_section = ""
        if available_labels:
            labels_section = f"""
# 利用可能なラベル
このリポジトリで使用可能なラベルは以下の通りです。**必ずこのリストから選択してください**：
{', '.join(available_labels)}
"""
        
        return f"""以下のGitHub issueを分析し、対応方針を提案してください。

# Issue情報
- タイトル: {issue_data['title']}
- 本文:
{issue_data['body']}

# リポジトリ情報
- リポジトリ: {issue_data['repo']}
{labels_section}
# 依頼内容
1. **まず、issueの情報が十分かを確認してください**
   - タイトルや本文が不明確で、具体的な情報が不足している場合は「情報不足」と判定
   - 例: 「エラーが発生する」「動かない」「バグ」のみで、詳細が記載されていない
   - 例: 再現手順、環境情報、エラーメッセージなど必要な情報が不足している

2. 情報が不足している場合は、**必ず「INSUFFICIENT_INFO」** というキーワードを含めて回答してください

3. 情報が十分な場合のみ、以下を実施してください:
   - issueの内容を分析し、問題の性質を特定
   - **上記の利用可能なラベルリストから**適切なラベルを3つまで提案
   - **リストにないラベルは絶対に提案しないでください**
   - 対応方針を具体的に提案

# 出力形式

## 情報不足の場合:
INSUFFICIENT_INFO

## 分析結果
[情報が不足している旨と、追加で必要な情報のリスト]

## 情報が十分な場合:
## 分析結果
[issueの内容分析]

## 提案ラベル
- label1
- label2
- label3

## 対応方針
[具体的な対応手順]
"""
    
    def _parse_analysis(self, result: Dict[str, Any]):
        analysis = result.get("analysis", "")
        
        labels = []
        lines = analysis.split('\n')
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
                    # Remove markdown bold markers (**text**)
                    label = label.replace('**', '')
                    
                    # Remove Japanese explanation in parentheses (（説明）)
                    if '（' in label:
                        label = label.split('（')[0].strip()
                    elif '(' in label:
                        label = label.split('(')[0].strip()
                    
                    # Only add non-empty labels
                    if label:
                        labels.append(label)
        
        result["suggested_labels"] = labels
    
    async def implement_fix(self, issue_data: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """
        Use Copilot to implement the actual fix for the issue
        This runs Copilot in the cloned repository directory
        """
        if not self.client:
            raise RuntimeError("Copilot client not started")
        
        session_config = {
            "model": "claude-sonnet-4.5",
            "cwd": repo_path  # Set working directory to cloned repo
        }
        
        # Check for repository-specific instructions (.github/copilot-instructions.md)
        repo_instructions = self._load_repo_instructions(repo_path)
        instructions_to_use = repo_instructions or self.custom_instructions
        
        if instructions_to_use:
            session_config["system_message"] = {
                "content": instructions_to_use
            }
            if repo_instructions:
                logger.info(f"Using repository-specific instructions from {repo_path}/.github/copilot-instructions.md")
        
        result = {
            "success": False,
            "message": "",
            "files_modified": []
        }
        
        # Check if issue body indicates that implementation is needed
        implementation_needed = self._check_if_implementation_needed(issue_data)
        
        prompt = f"""あなたはGitHub issueの修正を担当する開発者です。以下のissueに対応するコードを実装してください。

# Issue情報
- リポジトリ: {issue_data['repo']}
- Issue番号: #{issue_data['number']}
- タイトル: {issue_data['title']}
- 内容:
{issue_data['body']}

# 作業ディレクトリ
現在のディレクトリ: {repo_path}

# 指示
1. まずリポジトリの構造を把握してください（ls -la, tree, view など使用）
2. 関連するファイルを特定してください
3. {"**必ず具体的なコード変更を実装してください（ファイルの編集・作成が必須です）**" if implementation_needed else "必要な変更を実装してください"}
4. テストが必要な場合は、テストも更新してください
5. すべての変更が完了したら、変更内容を要約してください

# 重要な注意事項
{"- **このissueには実装が必要です。必ずファイルを編集・作成してください**" if implementation_needed else ""}
{"- **ただし、情報が不足している場合（エラー内容、再現手順、環境情報などが不明な場合）は編集を行わないでください**" if implementation_needed else ""}
- 既存のコードスタイルに従ってください
- 破壊的な変更は避けてください
- コメントは適切に追加してください
- エラーハンドリングを忘れないでください
{"- 分析だけで終わらせず、実際にコードを変更してください" if implementation_needed else ""}

それでは、issue #{issue_data['number']} の修正を開始してください。{"**必ずファイルを編集してください。**" if implementation_needed else ""}"""
        
        try:
            session = await self.client.create_session(session_config)
            
            logger.info(f"Sending implementation request to Copilot")
            
            # Use send_and_wait for simpler response handling  
            response = await session.send_and_wait({"prompt": prompt}, timeout=600)  # 10 minutes
            
            await session.destroy()
            
            if response and hasattr(response.data, 'content'):
                result["message"] = response.data.content
                result["success"] = True
                logger.info(f"Implementation completed: {len(result['message'])} characters")
            else:
                logger.warning("No implementation content received")
                result["message"] = "実装は試行されましたが、詳細メッセージを取得できませんでした。"
                result["success"] = False
                
        except asyncio.TimeoutError:
            logger.error("Implementation timed out after 600 seconds")
            result["message"] = "実装がタイムアウトしました。"
            result["success"] = False
        except Exception as e:
            logger.error(f"Error during implementation: {e}")
            result["message"] = f"実装中にエラーが発生しました: {str(e)}"
            result["success"] = False
        
        return result
    
    def _check_if_implementation_needed(self, issue_data: Dict[str, Any]) -> bool:
        """
        Check if the issue likely requires code implementation based on keywords
        Returns False if information is insufficient
        """
        body = (issue_data.get('body') or '').lower()
        title = (issue_data.get('title') or '').lower()
        combined = body + ' ' + title
        
        # Check for insufficient information indicators
        insufficient_indicators = [
            'エラーが発生する' in combined and 'エラー内容' not in combined and 'error' not in combined,
            '動かない' in combined and len(body) < 50,  # Too short description
            'bug' in combined and len(body) < 30,
            combined.strip() == '' or len(combined.strip()) < 20  # Extremely short
        ]
        
        # If any insufficient indicator is true, return False
        if any(insufficient_indicators):
            logger.info("Issue appears to have insufficient information for implementation")
            return False
        
        # Keywords that suggest implementation is needed
        implementation_keywords = [
            '実装', '追加', '機能', 'feature', 'add', 'implement', 'create',
            '修正', 'fix', 'bug', 'エラー', 'error', '動かない', 'not working',
            '変更', 'change', 'modify', '改善', 'improve', 'enhance',
            '対応', '処理', 'handle', 'として扱', 'として処理'
        ]
        
        return any(keyword in combined for keyword in implementation_keywords)
    
    async def implement_fix_with_retry(self, issue_data: Dict[str, Any], repo_path: str, 
                                       additional_context: str = "") -> Dict[str, Any]:
        """
        Retry implementation with more explicit instructions
        """
        if not self.client:
            raise RuntimeError("Copilot client not started")
        
        session_config = {
            "model": "claude-sonnet-4.5",
            "cwd": repo_path
        }
        
        repo_instructions = self._load_repo_instructions(repo_path)
        instructions_to_use = repo_instructions or self.custom_instructions
        
        if instructions_to_use:
            session_config["system_message"] = {
                "content": instructions_to_use
            }
        
        result = {
            "success": False,
            "message": "",
            "files_modified": []
        }
        
        prompt = f"""**重要: 前回の試行で失敗しました。今回は必ずファイルを変更してください。**

{additional_context}

# Issue情報
- リポジトリ: {issue_data['repo']}
- Issue番号: #{issue_data['number']}
- タイトル: {issue_data['title']}
- 内容:
{issue_data['body']}

# 作業ディレクトリ
現在のディレクトリ: {repo_path}

# 必須の手順
1. まず関連ファイルを特定
2. **issue内容が十分に具体的で実装可能な場合のみ、edit または create コマンドでファイルを変更**
3. 変更後に git diff で確認
4. 変更内容を報告

# 重要な条件
- **情報が不足している場合（エラー内容、再現手順、環境情報などが不明な場合）は編集を行わないでください**
- issueに具体的な実装内容が含まれている場合のみファイルを編集してください
- 不明確な要求に対して推測で実装することは避けてください"""
        
        try:
            session = await self.client.create_session(session_config)
            response = await session.send_and_wait({"prompt": prompt}, timeout=600)
            await session.destroy()
            
            if response and hasattr(response.data, 'content'):
                result["message"] = response.data.content
                result["success"] = True
                logger.info(f"Retry implementation completed: {len(result['message'])} characters")
            else:
                logger.warning("No implementation content received on retry")
                result["message"] = "リトライ実装でもメッセージを取得できませんでした。"
                result["success"] = False
                
        except asyncio.TimeoutError:
            logger.error("Retry implementation timed out")
            result["message"] = "リトライ実装がタイムアウトしました。"
            result["success"] = False
        except Exception as e:
            logger.error(f"Error during retry implementation: {e}")
            result["message"] = f"リトライ実装中にエラーが発生しました: {str(e)}"
            result["success"] = False
        
        return result
