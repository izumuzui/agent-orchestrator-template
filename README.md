# Verify-first multi-agent orchestrator

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
AGENTS.md / CLAUDE.md        Tool adapters and always-on safety rules
.ai/knowledge/              Stable facts and decision journal
.ai/standards/              Invariants and repository risk overlay
.ai/verification/           Definition of verified completion
.ai/workflows/              Change, review, routing, orchestration
.ai/handoffs/               Versioned handoff template only
.ai/metrics/                Event schema; actual events stay outside Git
.agent-state/               Ignored task snapshots and event journal
scripts/agent/              Deterministic checks and state helpers
```

## Start using it

1. `.ai/knowledge/repository-map.md` を対象repositoryに合わせて更新する。
2. `.ai/standards/security.md` のrepository overlayを埋める。
3. `.ai/workflows/routing.md` のassignment policyを契約と利用可能Agentに合わせる。
4. `scripts/agent/check-agent-env.sh` を実行する。
5. taskごとにhandoffを作り、routingを予約する。

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

## Initial assignment policy

最初に試すPattern Cは、P2への交換可能なassignmentです。

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
