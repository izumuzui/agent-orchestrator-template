# 共通ハーネスの入口

モデルに依存しない知識、安全、手順、検証、役割分担、引き継ぎの正本です。ツール別の入口は短く保ち、ここを参照します。

## 共通管理と固有設定

導入先で `.ai/harness.lock.json` に載るファイルは正本で編集し、同期コマンドで更新します。導入先で直接編集しません。この正本自体にはロックは不要です。

| プロジェクト所有の場所 | 内容 |
|---|---|
| `.ai/project.md` | 製品の前提、正本となる資料、追加手順、レビュー観点 |
| `.ai/standards/security-overlay.md` | 固有のリスクと禁止操作 |
| `.ai/verification/project.md` | 固有の検証と実行モード |
| `.ai/knowledge/repository-map.md` | 調査先と除外対象 |
| `.ai/knowledge/decisions.md` | 長く残す意思決定 |
| `.ai/knowledge/work-queue.md` | 非公開情報を除いた作業一覧 |
| `scripts/project/verify.sh` | 固有の検証コマンド |
| `scripts/project/check.sh` | 任意の追加整合性検査 |

管理対象外の追加文書もプロジェクト所有です。共通ルールと固有設定を両方適用し、安全上は厳しい方を優先します。

## 指示の優先順位

1. 今回のユーザーの明示指示
2. 安全・プライバシー・承認・非破壊操作の制約
3. 最も近いツール別入口
4. この共通環境とリポジトリの正本資料
5. 一般的な慣例

重要な矛盾を推測で解決しません。

## 作業別の手順

| 作業 | 文書 | 必要な証拠 |
|---|---|---|
| 変更・修正 | `workflows/change.md` | 受入基準、対象別の検証、共通チェック |
| ユーザーの訂正・画面の指摘 | `workflows/feedback-loop.md` | 出典、期待する挙動、検証した再発防止 |
| GitHub CI・Codexレビュー | `workflows/github-review.md` | 実際のCI・レビュー結果 |
| 独立レビュー | `workflows/review.md` | 出典からの基準導出、差分、検証の証拠 |
| 複数担当の作業 | `workflows/orchestration.md` | 限定した役割、一人の書き手、最終的な統合 |
| 利用枠・端末間引き継ぎ | `workflows/subscription-scheduling.md` | 観測した残量、旧担当の停止、再開地点 |
| 役割の選択 | `workflows/routing.md` | 意図した構成、実際の担当、代替理由 |
| プロジェクト固有の作業 | `.ai/project.md` | 固有条件と共通条件 |

## 実装前と完了時

要求の出典を識別し、生の非公開内容はコピーしません。版を付けて受入基準を固定し、許可・禁止範囲、検証、停止条件、再試行上限を宣言します。
`standards/security.md` と `standards/security-overlay.md` でリスクを分類し、P0〜P3を選んで追跡対象の役割を予約します。
実装完了・レビュー完了の両時点で、構成・所有範囲・安全境界・検証・役割方針に変更があれば `knowledge/decisions.md` へ記録します。安定した事実だけを残します。
