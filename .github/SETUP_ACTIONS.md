# GitHub Actions セットアップガイド

このリポジトリでGitHub Actionsを使用してissueの自動チェック・対応を行うための設定手順です。

## 必要なSecrets

リポジトリの Settings → Secrets and variables → Actions で以下のsecretsを設定してください。

### 1. GitHub App認証情報（推奨）

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `GH_APP_ID` | GitHub AppのID | GitHub App設定ページで確認 |
| `GH_APP_INSTALLATION_ID` | Installation ID | `get_installation_id.py`を実行して取得 |
| `GH_APP_PRIVATE_KEY` | GitHub Appの秘密鍵 | GitHub Appから生成した.pemファイルの内容全体 |

**秘密鍵の設定方法:**
```bash
# 秘密鍵ファイルの内容をコピー
cat /path/to/your-app-private-key.pem
# 上記の出力をGH_APP_PRIVATE_KEYに貼り付け（-----BEGIN RSA PRIVATE KEY----- から -----END RSA PRIVATE KEY----- まで）
```

### 2. リポジトリ設定

| Secret名 | 説明 | 例 |
|---------|------|-----|
| `GITHUB_REPOS` | 監視対象リポジトリ（カンマ区切り） | `owner/repo1,owner/repo2` |

## GitHub App権限の確認

GitHub Appに以下の権限が必要です：

### Repository permissions
- ✅ **Issues**: Read and write
- ✅ **Pull requests**: Read and write
- ✅ **Contents**: Read and write
- ✅ **Metadata**: Read-only

### Organization permissions（必要に応じて）
- ✅ **Members**: Read-only（組織リポジトリの場合）

## ワークフローの動作確認

### 1. 手動実行でテスト

1. リポジトリのActionsタブを開く
2. "GitHub Issues Auto Checker"を選択
3. "Run workflow"をクリック
4. デバッグモードを有効にする場合は"Enable debug logging"をチェック
5. "Run workflow"を実行

### 2. ログの確認

- 実行中: Actionsタブでリアルタイムログを確認
- 失敗時: Artifactsから`checker-logs`をダウンロード

### 3. スケジュール実行

- デフォルト: 毎時0分に実行（`0 * * * *`）
- 変更する場合: `.github/workflows/check-issues.yml`のcron式を編集

## トラブルシューティング

### Copilot認証エラー

GitHub Actionsでは自動的に`GITHUB_TOKEN`が提供されますが、Copilot CLIが認証できない場合：

1. リポジトリ設定でGitHub Copilotが有効か確認
2. Organization設定でGitHub Copilotの使用が許可されているか確認

### メモリ不足エラー

GitHub Actionsのランナーは7GBメモリです。不足する場合：

1. 処理するissue数を制限する
2. `timeout-minutes`を調整する
3. セルフホストランナーを検討する

### 実行時間超過

- デフォルトタイムアウト: 60分
- 必要に応じて`timeout-minutes`を変更

## セキュリティ注意事項

⚠️ **重要:**
- GitHub App秘密鍵は絶対にコミットしない
- Secretsは暗号化されますが、アクセス権限を適切に管理する
- ログに秘密情報が出力されないよう注意

## 料金について

- **パブリックリポジトリ**: 完全無料
- **プライベートリポジトリ**: 月2,000分まで無料（Freeプラン）
- 本ワークフローの想定実行時間: 1回あたり5-15分

**月間コスト試算:**
- 1時間に1回実行（24回/日）× 10分/回 = 240分/日
- 30日で約7,200分 → 有料プランが必要

スケジュールを調整して無料枠内に収めることを推奨します（例: 6時間に1回実行）。

## ローカルテストとの併用

GitHub Actionsと並行してローカル環境でもテストできます：

```bash
# ローカルで手動実行（Copilot有効）
python3 check_issues.py

# cronで定期実行（Copilot無効）
# 現在のcrontab設定を使用
```

## 次のステップ

1. ✅ Secretsを設定
2. ✅ GitHub App権限を確認
3. ✅ 手動実行でテスト
4. ✅ スケジュールを調整（必要に応じて）
5. ✅ 監視とメンテナンス
