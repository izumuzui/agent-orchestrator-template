# GitHub CIとCodexレビュー

## 実行場所と役割

- `.github/workflows/agent-verify.yml` はPRとmainへのプッシュで共通検証を行う。GitHubの実行環境、読み取り権限のトークン、時間・同時実行制限を使い、モデル用の認証情報は渡さない。Actionsの利用料金・制限は別途適用される。
- CodexのGitHubレビューはサービス側でリポジトリごとに有効化する。契約の利用枠と権限に依存し、ワークフローへAPIキーを追加しない。
- 担当はPRコメントをGit除外の受信箱へ取得し、妥当な訂正を選び、検証した教訓だけをGitへ提案する。

ローカル設定だけではサービス側のレビューは有効にならない。導入時は対象を接続し、[コードレビュー設定](https://chatgpt.com/settings/code-review)で有効化と契機を選ぶ。試験PRで `Agent verification / verify` と実際のCodexレビューの両方を確認する。権限・枠による未実行を区別する。
必要なら人がブランチ保護へ検査を追加する。このテンプレートは保護設定を変更せず、自動マージもしない。
手動レビューの `@codex review` コメント投稿は許可された場合だけ行い、繰り返すボットループを作らない。CI成功は独立レビューの受入ではなく、ボット指摘なしでも画面品質を証明しない。見た目や軽微な改善には別の画面証拠と教訓手順を使う。
採用先は `scripts/project/verify.sh` に実際の静的検査・型・ビルド・テストを設定する。未設定なら製品の検証済み公開と扱わない。Claude Actionsはこの構成に含めない。

## 参考資料

以下は2026-10-24に確認された設計資料。今回の文書整理で最新の外部画面や機能を再確認したものではない。

- [ハーネス設計の講演](https://speakerdeck.com/kinopeee/hanesu-sekkei-nyuumon-kiso-chishiki-no-seiri-kara-jitsumu-heno-suteppu-appu): 原則を構成へ反映し、逐語転載していない。
- [CodexとGitHubの連携](https://learn.chatgpt.com/docs/third-party/github)
- [GitHub Actionsの安全な利用](https://docs.github.com/en/actions/reference/security/secure-use)
