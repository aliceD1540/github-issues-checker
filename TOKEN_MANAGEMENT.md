# GitHub Token Management for Long-term Operation

本ツールを長期間運用するためのトークン管理の推奨方法

## オプション1: GitHub App（最も推奨）⭐

### メリット
- トークンが自動的に更新される（1時間有効）
- より細かい権限制御が可能
- **複数リポジトリに対して1つのAppで対応可能**
- Organization全体で管理しやすい
- セキュリティ監査がしやすい
- レート制限が緩い（15,000リクエスト/時間 vs PAT: 5,000リクエスト/時間）

### 複数リポジトリの扱い

GitHub Appをインストールする際に以下の選択が可能です：

1. **All repositories** - Organization/アカウントのすべてのリポジトリ
2. **Only select repositories** - 特定のリポジトリのみ

どちらの場合も、**1つのINSTALLATION_IDですべての対象リポジトリにアクセス可能**です。

```bash
# .envの設定例（複数リポジトリ対応）
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_APP_INSTALLATION_ID=78901234

# これだけで以下のすべてのリポジトリにアクセス可能
GITHUB_REPOS=myorg/repo1,myorg/repo2,myorg/repo3,anotherorg/repo4
```

**重要**: GITHUB_REPOSに記載したリポジトリが、GitHub Appのインストール対象に含まれている必要があります。

### セットアップ手順

1. **GitHub Appの作成**
   - GitHub Settings → Developer settings → GitHub Apps → New GitHub App
   - App name: `GitHub Issues Checker Bot`
   - Homepage URL: リポジトリのURL
   - Webhook: 無効化
   
2. **権限の設定**
   - Repository permissions:
     - Issues: Read & Write
     - Pull requests: Read & Write
     - Contents: Read & Write
     - Metadata: Read-only

3. **インストール**
   - Install App で対象リポジトリにインストール
   - **Repository access** を選択：
     - "All repositories" - すべてのリポジトリ（推奨）
     - "Only select repositories" - 特定のリポジトリのみ
   - インストール後、Installation IDを確認
     - URL: `https://github.com/settings/installations/{INSTALLATION_ID}`
     - または: `https://github.com/organizations/{ORG}/settings/installations/{INSTALLATION_ID}`

4. **認証情報の取得**
   - App ID を取得
   - Private Key を生成してダウンロード

5. **.envに設定**
   ```bash
   # GitHub App認証（PATの代わり）
   GITHUB_APP_ID=123456
   GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
   GITHUB_APP_INSTALLATION_ID=78901234
   
   # チェック対象リポジトリ（GitHub Appがインストールされている必要あり）
   GITHUB_REPOS=myorg/repo1,myorg/repo2,myorg/repo3
   ```

### Installation IDの確認方法

GitHub Appをインストールした後、以下の方法でInstallation IDを確認できます：

**方法1: URLから確認**
- 個人アカウント: `https://github.com/settings/installations`
- Organization: `https://github.com/organizations/{ORG_NAME}/settings/installations`
- 各Appをクリックして、URLの末尾の数字がInstallation IDです

**方法2: API経由で確認**
```bash
# GitHub CLIを使用
gh api /users/{USERNAME}/installation | jq .id
# または
gh api /orgs/{ORG_NAME}/installation | jq .id
```

**方法3: プログラムで取得**
```python
# github_auth.pyに追加可能なヘルパー関数
from github import GithubIntegration

integration = GithubIntegration(app_id, private_key)
for installation in integration.get_installations():
    print(f"Installation ID: {installation.id}")
    print(f"Account: {installation.account.login}")
```

## オプション2: Fine-grained Personal Access Token

### メリット
- 最大1年の有効期限
- リポジトリごとに権限を制限可能
- 従来のPATより安全

### セットアップ
1. Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Token name: `github-issues-checker`
3. Expiration: 1 year (365 days)
4. Repository access: Only select repositories
5. Permissions:
   - Issues: Read & Write
   - Pull requests: Read & Write
   - Contents: Read & Write

### 運用
- カレンダーに更新リマインダーを設定
- 有効期限1ヶ月前に通知を受け取る（本ツールの機能で実装可能）

## オプション3: 専用ボットアカウント

### メリット
- 人間のアカウントと分離
- チーム管理がしやすい
- トークンが誰のものか明確

### セットアップ
1. 新しいGitHubアカウントを作成（例: `myorg-issues-bot`）
2. Organization に招待してメンバーに追加
3. そのアカウントでPATを発行
4. 必要最小限の権限のみ付与

## オプション4: トークン有効期限の監視

本ツールに組み込んだトークン有効期限チェック機能を使用：
- 起動時に有効期限をチェック
- 30日以内に期限切れの場合は警告
- ログに記録して管理者に通知

## 推奨構成（本番環境）

### 個人プロジェクトの場合
```
Fine-grained PAT（1年有効）
    ↓
定期更新リマインダー設定
```

### Organizationや複数リポジトリの場合（推奨）⭐
```
GitHub App（自動更新、複数リポジトリ対応）
    ↓
Organization全体で管理
    ↓
必要に応じてリポジトリを追加/削除
```

### エンタープライズ環境
```
GitHub App（自動更新）
    ↓
専用ボットアカウント（管理用）
    ↓
有効期限監視機能（バックアップ）
    ↓
監査ログとアラート
```

## GitHub App vs PAT 比較表

| 項目 | GitHub App | Fine-grained PAT | Classic PAT |
|------|-----------|-----------------|-------------|
| **複数リポジトリ対応** | ✅ 1つのAppで複数対応 | ✅ 個別選択 | ✅ すべてアクセス可 |
| **自動トークン更新** | ✅ 1時間ごと | ❌ 手動更新 | ❌ 手動更新 |
| **有効期限** | なし（自動更新） | 最大1年 | 最大1年 |
| **レート制限** | 15,000/時間 | 5,000/時間 | 5,000/時間 |
| **権限の細かさ** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **セキュリティ** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **セットアップの簡単さ** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Organization管理** | ✅ 優秀 | ⚠️ 個人ごと | ⚠️ 個人ごと |
| **監査ログ** | ✅ 詳細 | ✅ あり | ⚠️ 限定的 |

**結論**: 複数リポジトリの長期運用なら GitHub App が最適！

## セキュリティのベストプラクティス

1. **環境変数の保護**
   - `.env`ファイルのパーミッションを600に設定
   - 本番サーバーでは環境変数を直接設定

2. **最小権限の原則**
   - 必要な権限のみを付与
   - パブリックリポジトリへのアクセスは制限

3. **トークンのローテーション**
   - 定期的にトークンを更新
   - 古いトークンは即座に無効化

4. **監査ログ**
   - トークンの使用状況を定期的に確認
   - 不審なアクティビティを監視
