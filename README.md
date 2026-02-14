# GitHub Issues Checker

GitHub Copilot SDKを使用して、GitHubリポジトリのissuesを自動チェック・対応するツールです。

## 機能

- 指定したGitHubリポジトリのopenなissueを定期的にチェック
- GitHub Copilot SDKを使用してissueの内容を自動分析
- 分析結果をissueにコメントとして追加
- 適切なラベルを自動付与
- 対応用のブランチとプルリクエストを自動作成

## 必要要件

- Python 3.9以上
- GitHub Copilot CLI がインストール済みであること
- GitHub認証:
  - **Personal Access Token** (repo権限が必要) または
  - **GitHub App** (推奨: 複数リポジトリの長期運用に最適)

### GitHub認証について

#### Personal Access Token（簡単、短期運用向け）
- 個人プロジェクトや開発・テスト用に最適
- 複数リポジトリにも対応可能
- 有効期限あり（最大1年）

#### GitHub App（推奨、複数リポジトリ・長期運用向け）⭐
- **1つのAppで複数リポジトリに対応**
- トークンが自動更新（1時間ごと）
- レート制限が緩い（15,000 vs 5,000リクエスト/時間）
- Organization全体で管理しやすい
- 詳細: [TOKEN_MANAGEMENT.md](TOKEN_MANAGEMENT.md)

### GitHub Copilot CLIのインストール

```bash
# GitHub Copilot CLIをインストール
# 詳細: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli

# 例: npmでインストールする場合
npm install -g @githubnext/github-copilot-cli

# CLIが正しくインストールされているか確認
copilot --version
```

## セットアップ

### 1. リポジトリのクローンと依存関係のインストール

```bash
cd github-issues-checker
pip install -r requirements.txt
```

### 2. 認証方法の選択

#### オプションA: Personal Access Token（簡単）

`.env.example`をコピーして`.env`ファイルを作成：

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```bash
# Personal Access Token
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPOS=owner1/repo1,owner2/repo2
```

#### オプションB: GitHub App（長期運用に推奨）⭐

詳細は [TOKEN_MANAGEMENT.md](TOKEN_MANAGEMENT.md) を参照してください。

```bash
# GitHub App認証
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_APP_INSTALLATION_ID=78901234
GITHUB_REPOS=owner1/repo1,owner2/repo2
```

**GitHub Appのメリット:**
- トークンが自動更新される（1時間ごと）
- より細かい権限制御
- 有効期限切れの心配なし
- セキュリティ監査がしやすい
- **複数リポジトリに1つのAppで対応可能**
- レート制限が緩い（15,000/時間）

**Installation IDの確認方法:**

```bash
# ヘルパースクリプトを使用（最も簡単）
python get_installation_id.py

# または、Settings → Installations のURLから確認
# https://github.com/settings/installations/{INSTALLATION_ID}
```

### 3. GitHub Personal Access Tokenの取得（オプションAの場合）

1. GitHubの設定 → Developer settings → Personal access tokens → Tokens (classic) にアクセス
2. "Generate new token (classic)" をクリック
3. 以下の権限を付与：
   - `repo` (フルアクセス)
4. トークンを生成してコピー
5. `.env`ファイルの`GITHUB_TOKEN`に貼り付け

## 使用方法

### 手動実行

```bash
python check_issues.py
```

### カスタム指示の編集

Copilotの動作をカスタマイズする方法は2つあります：

#### 1. グローバル指示（すべてのリポジトリに適用）

`copilot-instructions.md`ファイルを編集：

```bash
# デフォルトの指示ファイルを編集
vim copilot-instructions.md

# または別の指示ファイルを使用
# .envファイルに以下を追加
COPILOT_INSTRUCTIONS_FILE=custom-instructions.md
```

#### 2. リポジトリ固有の指示（推奨）⭐

対象リポジトリに `.github/copilot-instructions.md` を配置すると、そのリポジトリの処理時に自動的に読み込まれます：

```bash
# 対象リポジトリで
mkdir -p .github
vim .github/copilot-instructions.md
```

**優先順位**: リポジトリ固有 > グローバル

**使い分けの例**:
- グローバル: 基本的な動作方針、一般的なルール
- リポジトリ固有: プロジェクト特有の命名規則、アーキテクチャ、テストフレームワーク

指示ファイルには以下の内容を含めることができます：
- Copilotの役割と目的
- Issue分類の基準
- 分析時の注意点
- 出力形式のテンプレート
- トーンとスタイルのガイドライン
- プロジェクト固有のコーディング規約

### systemdサービスとして定期実行

systemdを使用して、確実な定期実行とログ管理を行います。

**1. systemdサービスファイルを作成**

`/etc/systemd/system/github-issues-checker.service`を作成：

```ini
[Unit]
Description=GitHub Issues Checker Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/github-issues-checker
Environment="PATH=/home/your-username/.nvm/versions/node/v20.18.0/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 /path/to/github-issues-checker/check_issues.py
StandardOutput=append:/path/to/github-issues-checker/logs/checker.log
StandardError=append:/path/to/github-issues-checker/logs/checker.log

[Install]
WantedBy=multi-user.target
```

**設定のポイント:**
- `User`: 実行するユーザー名に置き換えてください
- `WorkingDirectory`: このリポジトリの絶対パスに置き換えてください
- `Environment="PATH=..."`: `which copilot`コマンドで確認したcopilotのパスを含めてください
- `ExecStart`: check_issues.pyの絶対パスを指定してください

**2. systemdタイマーファイルを作成**

`/etc/systemd/system/github-issues-checker.timer`を作成（1時間ごとに実行）：

```ini
[Unit]
Description=GitHub Issues Checker Timer
Requires=github-issues-checker.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Unit=github-issues-checker.service

[Install]
WantedBy=timers.target
```

**タイマー設定の説明:**
- `OnBootSec=5min`: システム起動から5分後に初回実行
- `OnUnitActiveSec=1h`: 前回の実行完了から1時間後に次回実行

**3. サービスを有効化して開始**

```bash
# ログディレクトリを作成
mkdir -p /path/to/github-issues-checker/logs

# systemdをリロード
sudo systemctl daemon-reload

# タイマーを有効化して開始
sudo systemctl enable github-issues-checker.timer
sudo systemctl start github-issues-checker.timer

# タイマーの状態を確認
sudo systemctl status github-issues-checker.timer
sudo systemctl list-timers --all | grep github-issues-checker
```

**4. ログの確認**

```bash
# サービスのログを確認（journald経由）
sudo journalctl -u github-issues-checker.service -f

# または、ファイルログを確認
tail -f /path/to/github-issues-checker/logs/checker.log
```

**5. サービスの管理コマンド**

```bash
# 手動で即座に実行
sudo systemctl start github-issues-checker.service

# タイマーを停止
sudo systemctl stop github-issues-checker.timer

# タイマーを無効化
sudo systemctl disable github-issues-checker.timer

# 設定変更後のリロード
sudo systemctl daemon-reload
sudo systemctl restart github-issues-checker.timer
```

**systemdのメリット:**
- システム起動時に自動で有効化
- 確実なログ管理（journalctlで管理）
- サービスの状態管理が簡単
- 失敗時の自動リトライ設定が可能
- PATH環境変数を確実に設定可能

## 処理の流れ

1. 環境変数から対象リポジトリリストを取得
2. 各リポジトリのopenなissueを取得（`bot-processed`ラベルがないもの）
3. 各issueに対して以下を実行：
   - GitHub Copilot SDKでissueの内容を分析
   - 分析結果をコメントとして追加
   - 適切なラベルを付与
   - リポジトリをクローン
   - 対応用ブランチ（`fix/issue-{番号}`）をチェックアウト
   - **Copilot SDKが実際にコードを修正** ← NEW!
   - 変更をコミット
   - ブランチをプッシュ
   - プルリクエストを自動作成
   - `bot-processed`ラベルを付与（重複処理を防ぐ）
4. 一時ファイルをクリーンアップ

## ファイル構成

```
github-issues-checker/
├── check_issues.py              # メインスクリプト（自動実装機能付き）
├── config.py                    # 設定管理
├── github_handler.py            # GitHub API操作
├── github_auth.py               # GitHub認証（PAT/GitHub App対応）
├── git_handler.py               # Gitクローン・コミット・プッシュ操作
├── copilot_handler.py           # Copilot SDK操作（分析＋実装）
├── copilot-instructions.md      # Copilot用カスタム指示
├── get_installation_id.py       # GitHub App Installation ID確認ツール
├── requirements.txt             # Python依存パッケージ
├── .env.example                # 環境変数テンプレート
├── .env                        # 環境変数（要作成、gitignore対象）
├── TOKEN_MANAGEMENT.md         # トークン管理ガイド（複数リポジトリ対応の詳細）
├── DESIGN.md                   # 設計書
└── README.md                   # このファイル
```

## ログ

実行ログはsystemdサービスの`StandardOutput`と`StandardError`で指定したファイルに保存されます。

```bash
# ファイルログを確認
tail -f /path/to/github-issues-checker/logs/checker.log

# または、systemdのjournalで確認
sudo journalctl -u github-issues-checker.service -f
```

## トラブルシューティング

### トークンの有効期限切れ

```
Error: Bad credentials (401)
```

→ トークンが期限切れです。以下の対応を検討してください：

1. **短期対応**: 新しいPATを発行して更新
2. **長期対応**: GitHub Appに移行（[TOKEN_MANAGEMENT.md](TOKEN_MANAGEMENT.md)参照）

起動時にトークンの状態をチェックし、問題があればログに記録されます。

### GitHub App認証エラー

```
Error: Private key file not found
```

→ `GITHUB_APP_PRIVATE_KEY_PATH`が正しいパスを指しているか確認してください。

### Copilot CLIが見つからない

```
Error: copilot command not found
または
FileNotFoundError: [Errno 2] No such file or directory: 'copilot'
```

→ GitHub Copilot CLIがインストールされていないか、systemdサービスファイルのPATHが正しく設定されていません。

**解決方法:**

1. copilotコマンドのパスを確認：

```bash
which copilot
# 例: /home/user/.nvm/versions/node/v20.18.0/bin/copilot
```

2. systemdサービスファイルの`Environment`行を更新：

```bash
sudo nano /etc/systemd/system/github-issues-checker.service
```

3. `Environment`行にcopilotのパスを含めます：

```ini
Environment="PATH=/home/user/.nvm/versions/node/v20.18.0/bin:/usr/local/bin:/usr/bin:/bin"
```

4. systemdをリロードして再起動：

```bash
sudo systemctl daemon-reload
sudo systemctl restart github-issues-checker.timer
```

### GitHub認証エラー

```
Error: Bad credentials
```

→ `GITHUB_TOKEN`が正しく設定されているか確認してください。トークンに`repo`権限があることを確認してください。

### リポジトリが見つからない

```
Error: Not Found
```

→ `GITHUB_REPOS`の形式が正しいか（`owner/repo`）、トークンに該当リポジトリへのアクセス権があるか確認してください。

## 注意事項

- **自動生成されたPRは必ずレビューしてからマージしてください** ⚠️
  - Copilotが実装したコードは完璧ではありません
  - セキュリティ、パフォーマンス、ロジックを確認してください
  - 必要に応じて修正を加えてください
- APIレート制限に注意してください（GitHub API: 5000リクエスト/時間、GitHub App: 15000リクエスト/時間）
- 大量のissueがある場合は、初回実行時に時間がかかります（1 issue あたり5-10分程度）
- Copilot SDKの使用にはGitHub Copilotのサブスクリプションが必要です
- **長期運用にはGitHub Appの使用を強く推奨します**（詳細: [TOKEN_MANAGEMENT.md](TOKEN_MANAGEMENT.md)）
- リポジトリのクローン先（デフォルト: `/tmp/github-issues-checker`）に十分な空き容量があることを確認してください

## ライセンス

MIT

## 貢献

Issue報告やプルリクエストを歓迎します。
