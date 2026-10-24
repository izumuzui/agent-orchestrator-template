# Codex Plus / Claude Pro shared orchestrator

Claude Code、Codex、将来追加するAgentを、モデルの序列ではなく共通の
検証・handoff・routing規約で扱うためのSmall Coreです。

このディレクトリは実証済みフレームワークではありません。初期policyを
10件のnon-trivial taskで校正し、結果からassignmentを更新するための
運用テンプレートです。

## Core principles

- 要求ソースから、実装案より先にacceptanceとproofを定義する
- shared worktreeへの書込みはone writerに限定する
- 独立reviewはfresh contextの別instanceで行う
- quality routingとquota-aware schedulingを分離する
- qualified agentが不在なら待つかscopeを縮小し、品質を降格しない
- loopには停止条件、試行上限、再診断条件を持たせる
- handoffとtask eventにsecretやraw private contentを残さない

## Structure

```text
AGENTS.md / CLAUDE.md       Managed harness block + project rules
.ai/knowledge/              Stable facts and decision journal
.ai/standards/              Invariants and repository risk overlay
.ai/verification/           Definition of verified completion
.ai/workflows/              Change, review, routing, orchestration
.ai/handoffs/               Versioned handoff template only
.ai/metrics/                Event schema; actual events stay outside Git
.agent-state/               Ignored task snapshots and event journal
scripts/agent/              Deterministic checks and state helpers (managed)
scripts/harness/            Sync, guard hook, manifest, seeds (template only)
scripts/project/            Project-owned product verification
```

## ~/work 全体への導入と同期

このリポジトリは `~/work` 以下の全プロジェクトのハーネスの正本です。
各リポジトリには管理ファイルをコピーし、`.ai/harness.lock.json` にハッシュを記録します。

```bash
python3 scripts/harness/sync.py status                       # 全リポジトリの状態
python3 scripts/harness/sync.py install ~/work/<repo> --dry-run
python3 scripts/harness/sync.py install ~/work/<repo>        # 導入
python3 scripts/harness/sync.py sync ~/work/<repo>           # テンプレート更新の反映
```

- 管理ファイル（`scripts/harness/manifest.json` の `managed`）は上書き同期。
  プロジェクトで直接編集されていると同期を拒否し、差分を表示します。
- 初期ファイル（`seeded`）は無い時だけ作り、以後はプロジェクト所有です。
- `AGENTS.md` / `CLAUDE.md` は `<!-- HARNESS:START -->` 〜 `<!-- HARNESS:END -->`
  だけを置き換え、プロジェクト固有のルールは残します。
- commit・push は行いません。導入後に各プロジェクトのスロットを埋めて検証・レビューします。

強制はグローバルフック `scripts/harness/guard.py` で行います（Claude Code と Codex 共通）。

- SessionStart: リポジトリのハーネス状態と読む順番を文脈に注入
- PreToolUse（Edit / Write / apply_patch など）: 未導入リポジトリの編集と、
  管理ファイルの直接編集を拒否。導入済みリポジトリの古いブランチは警告のみ
- 対象は `scripts/harness/workspace.json` の `root`、除外は `exempt`（既定: `notes`）
- 一時的に外す: `AGENT_HARNESS_GUARD=off`。内部エラー時は fail open

## Start using it

1. `.ai/knowledge/repository-map.md` を対象repositoryに合わせて更新する。
2. `.ai/standards/security.md` のrepository overlayを埋める。
3. `.ai/workflows/routing.md` のassignment policyを契約と利用可能Agentに合わせる。
4. `scripts/project/verify.sh` に実際のlint/test/buildを書く（`.ai/verification/project.md`）。
5. `scripts/agent/check-agent-env.sh` を実行する。
6. taskごとにhandoffを作り、routingを予約する。

```bash
scripts/agent/create-handoff.sh

scripts/agent/reserve-routing.py \
  --task-id t_20260715_example \
  --policy-version v1 \
  --area-id backend \
  --task-type feature \
  --risk medium \
  --intended-pattern P2 \
  --non-trivial
```

完了時は、予約時に返された`review_required`に従ってreviewを通したうえで
eventを記録します。

```bash
scripts/agent/record-completion.py \
  --task-id t_20260715_example \
  --planner codex_plan_v1 \
  --writer claude_writer_v1 \
  --reviewer codex_review_v1 \
  --reviewer-relation cross_provider \
  --review-outcome accepted \
  --overall passed \
  --passed 12
```

## Legacy initial assignment policy

旧v1のPattern Cは、P2への交換可能なassignmentです。Plus / Proでは後述のv2を使います。

```text
Codex: Plan / acceptance draft
Claude Code: Implementation / test / fix
Fresh Codex instance: Independent review
Claude Code: Review findingsの修正
```

これは能力の固定評価ではありません。10件ごとの意思決定checkpoint、
またはモデル・契約変更時に`.ai/knowledge/decisions.md`へ理由を残して更新します。

## Not included yet

- tool別Skillの生成・同期基盤
- proactive loopや無人の外部状態変更
- provider固有のagent定義
- task eventの統計的ランキング

これらは必要性が反復して確認されてからExtensionとして追加します。

## Plus / Proで使う（v2）

MacとUbuntuで成果物・プロジェクト知識・引き継ぎを共有し、CodexとClaude
の担当を利用枠に応じて交換します。既存の検証・独立レビュー要件は維持します。

- 作業一覧: `.ai/knowledge/work-queue.md`
- 残量の手入力・担当候補の推薦: `scripts/agent/quota.py`
- PC間の引き継ぎ: `.ai/workflows/subscription-scheduling.md`
- 続行に必要な情報: handoffのResume checkpoint

担当は固定しません。まず作業に適した候補を選び、その中で残量に余裕のある
方へ割り当てます。残量はアカウント単位で扱い、調整役は1台に集約します。
未取得・古い・リセット済みの残量は再確認を求めます。上限突破や追加購入、
API呼び出し、自動でのエージェント起動は行いません。

```bash
python3 scripts/agent/quota.py --help
python3 scripts/agent/quota.py select --candidates codex claude
scripts/agent/verify-change.sh full
```

利用条件: macOS / Ubuntu、Bash 3.2以上、Python 3.9以上。
新規タスクのroutingには`--policy-version v2`を使います。
skills・個人メモリの同期、残量の自動取得、無人運転は今後の拡張です。

## GitHubレビューと、同じ指摘を繰り返さない仕組み

PRには通常の自動チェックを用意し、AIレビューはCodexのGitHub連携を使います。
有効化手順と未設定の範囲は`.ai/workflows/github-review.md`に記載しています。
CIファイルを置くだけではCodexの自動レビューは有効になりません。

UIの指摘、レビューで発見した欠陥、作業失敗は`.ai/feedback/`に記録します。
次回は対象パスに合う記録を読み、修正→検証→再発防止を回します。
モデル自体の再学習ではなく、知識・ルール・テストを育てる方式です。

```bash
python3 scripts/agent/feedback.py --help
python3 scripts/agent/feedback.py context --path src/settings/page.tsx
python3 scripts/agent/feedback.py sync-github --repo OWNER/REPO --pr 123
bash scripts/agent/verify-change.sh full
```

記録・昇格・廃止の例は`.ai/feedback/README.md`、日々の運用は
`.ai/workflows/feedback-loop.md`を参照してください。サンプルのUI指摘を
本当のユーザーの好みとして登録しないでください。GitHubの本文は未信頼の
受信データとして扱い、検証せずに指示やルールへ昇格させません。
