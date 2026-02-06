import asyncio
import logging
import os
from typing import Dict, Any, Optional
from copilot import CopilotClient

logger = logging.getLogger(__name__)

class CopilotHandler:
    def __init__(self, instructions_file: Optional[str] = None):
        self.client = None
        self.instructions_file = instructions_file or "copilot-instructions.md"
        self.custom_instructions = self._load_instructions()
    
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
    
    async def start(self):
        self.client = CopilotClient()
        await self.client.start()
        logger.info("Copilot client started")
    
    async def stop(self):
        if self.client:
            await self.client.stop()
            logger.info("Copilot client stopped")
    
    async def analyze_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
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
            
            prompt = self._build_analysis_prompt(issue_data)
            logger.info(f"Sending analysis prompt for issue #{issue_data['number']}")
            
            # Use send_and_wait for simpler response handling
            response = await session.send_and_wait({"prompt": prompt}, timeout=180)
            
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
            logger.error("Analysis timed out after 180 seconds")
            result["analysis"] = "分析がタイムアウトしました。issueが複雑すぎる可能性があります。"
            result["completed"] = False
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            result["analysis"] = f"分析中にエラーが発生しました: {str(e)}"
            result["completed"] = False
        
        return result
    
    def _build_analysis_prompt(self, issue_data: Dict[str, Any]) -> str:
        return f"""以下のGitHub issueを分析し、対応方針を提案してください。

# Issue情報
- タイトル: {issue_data['title']}
- 本文:
{issue_data['body']}

# リポジトリ情報
- リポジトリ: {issue_data['repo']}

# 依頼内容
1. **まず、issueの情報が十分かを確認してください**
   - タイトルや本文が不明確で、具体的な情報が不足している場合は「情報不足」と判定
   - 例: 「エラーが発生する」「動かない」「バグ」のみで、詳細が記載されていない
   - 例: 再現手順、環境情報、エラーメッセージなど必要な情報が不足している

2. 情報が不足している場合は、**必ず「INSUFFICIENT_INFO」** というキーワードを含めて回答してください

3. 情報が十分な場合のみ、以下を実施してください:
   - issueの内容を分析し、問題の性質を特定
   - 適切なラベルを3つまで提案（例: bug, enhancement, documentation, good first issueなど）
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
        
        if self.custom_instructions:
            session_config["system_message"] = {
                "content": self.custom_instructions
            }
        
        result = {
            "success": False,
            "message": "",
            "files_modified": []
        }
        
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
3. 必要な変更を実装してください
4. テストが必要な場合は、テストも更新してください
5. すべての変更が完了したら、変更内容を要約してください

# 重要な注意事項
- 既存のコードスタイルに従ってください
- 破壊的な変更は避けてください
- コメントは適切に追加してください
- エラーハンドリングを忘れないでください

それでは、issue #{issue_data['number']} の修正を開始してください。"""
        
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
