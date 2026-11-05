# このリポジトリの固有設定

`agent-orchestrator-template` は設定上の `~/work` 配下へ配布する共通ハーネスの正本。変更は `scripts/harness/sync.py` を通じて他リポジトリへ伝わるため、配布に影響する変更として扱う。

| 正本資料 | 内容 |
|---|---|
| `README.md` | 全体像と導入 |
| `scripts/harness/manifest.json` | 管理対象と初期作成対象 |
| `scripts/harness/workspace.json` | 対象範囲と除外 |

## 追加手順とレビュー観点

ハーネスの契約変更は `workflows/change.md` のP1以上で行う。ここで `scripts/agent/verify-change.sh full` を実行し、導入済みの各対象で同期の変更計画も確認する。
管理対象の変更は採用先でも動く必要がある。許可された対象を指定して同期状態と差分を確認し、調査範囲外の確認は実行不能として報告する。
`guard.py` は内部エラー時に操作を止めず、この正本と除外対象の編集を妨げないこと。
