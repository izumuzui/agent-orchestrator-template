# 作業の引き継ぎ

## 識別情報

- task_id: `{{TASK_ID}}`
- status: planned
- acceptance_version: 1

## レビュアーへ最初に渡す資料

- requirement_sources:
- allowed_scope:
- forbidden_scope:
- risk_class:
- risk_overlay:

出典から独立に基準を導くため、最初の資料には書き手の受入基準や計画を含めない。

## 役割分担

- policy_version: v3
- area_id:
- task_type:
- intended_pattern:
- routing_sequence:
- sentinel_sequence:
- sentinel_counter_key:
- sentinel:
- review_required:
- actual_assignment:
- fallback_reason: none

## 固定した受入基準

| ID | 条件 | 要求の出典 |
|---|---|---|
| A1 |  |  |

実装開始後に意味を変える場合は受入基準の版を上げ、範囲変更の判断を記録する。

## 検証と停止条件

- focused_proof:
- common_proof: `scripts/agent/verify-change.sh full`
- required_checks:
- non_required_checks:
- max_fix_rounds: 3
- same_failure_reconsider_after: 2

## 変更の要約

短く要約し、会話全文、内部推論、秘密、生の非公開内容、非公開の絶対パス、端末出力全文を含めない。

## 検証結果

- overall: incomplete
- passed:
- failed:
- skipped:
- environment_blocked:

## レビュー

- reviewer_relation: none
- review_outcome: none
- rework_rounds: 0

## 残る課題

- blockers:
- residual_risks:

## 変更ファイル

リポジトリ相対パスだけを使う。

## 再開地点

- repository_id: (安全な識別子。非公開URLや絶対パスは禁止)
- branch:
- checkpoint_commit:
- previous_writer:
- previous_writer_stopped: false
- next_writer:
- next_action:
- uncommitted_work: (端末間転送前に意図した変更をコミットする)
- required_review_pending:
- receiving_machine_checks:

受け手は編集前にコミットと受入基準を確認する。Git除外のローカル引き継ぎを転送済みと仮定しない。安全な転送は `.ai/workflows/subscription-scheduling.md` に従う。


キーと状態値はコマンドや既存記録と対応する識別子のため英字のまま記入する。
