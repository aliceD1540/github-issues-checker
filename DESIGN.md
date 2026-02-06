# GitHub Issues Checker

## 概要

Github Copilot SDKを使用し、Githubリポジトリのissuesをチェック、自動対応するツールです。

## 環境

- WSL2 Ubuntu
- Python 3

## 処理の流れ

以下の処理をcronで定期実行します。

1. 環境変数からチェック対象リポジトリ（複数可）を取得
2. GitHub APIを使用して、リポジトリのissuesを取得
3. 各issueに対してGithub Copilot SDKを使用して以下の処理を実行
	- issueの内容を解析
	- 対応方針についてのコメントを追加、ラベルを付与
	- 対応用ブランチを作成して対応、プルリクエストを作成

## 実装方針

- 環境変数名
	- チェック対象リポジトリリスト: GITHUB_REPOS=owner1/repo1,owner2/repo2 のような形式
	- GitHub Token: GITHUB_TOKEN
- Issue選択条件
	- Openで本スクリプトで未チェックのもの
- ラベル付与
	- issuesの内容に応じたラベルを付与
- 処理方針
	- すべてのissueに対して自動的にブランチ作成＆PRを作成
- Cron設定
	- 実装完了後に検討（現時点では1時間に1回程度の実行を想定）

