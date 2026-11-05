# 作業イベントの形式

イベントは追記専用の意思決定記録で、モデル順位表ではない。実データは `.agent-state/metrics/task-events.jsonl` またはアクセス制限した保存先へ置く。仮名化であり匿名ではない。

## プライバシー

不透明な作業IDと列挙値・長さを制限した識別子だけを使い、自由文の問題欄を作らない。入力文、ソース、会話、端末出力、非公開の絶対パス、秘密、ユーザー識別、非公開メディア由来の文を記録しない。能力IDは版を含めても認証情報やアカウントIDを含めない。

## 役割予約: `routing_reserved`

必須項目:

- `event`, `ts`, `task_id`, `policy_version`
- `area_id`, `task_type`, `risk`, `intended_pattern`
- `sentinel_counter_key`, `routing_sequence`, `sentinel_sequence`
- `non_trivial`, `calibration`, `sentinel`
- `review_required`, `review_reason`

実装前に順番を排他的に予約する。最初の非定型10件は `calibration=true`。校正後の低リスクだけで分類ごとの5件に1件を抜き取り対象とする。対象外の `sentinel_sequence` は `null`。

## 終了: `task_completed`

予約の識別子と役割項目、版付きの計画・編集・レビュー能力IDに加えて、次を必須とする。

- `reviewer_relation`, `review_outcome`, `review_rework_rounds`
- 実装、検証、計画修正の再試行数
- 検証の `overall`, `passed`, `failed`, `skipped`, `environment_blocked`
- `fallback_reason`, `rate_limit_hits`、取得可能なら使用量の状態・値・単位
- 分類した人の介入
- 見逃した欠陥の修正なら `regression_of`

レビュー指摘件数を成績指標にしない。見直し時は介入、手戻り、再試行、実行不能の検証、利用制限、見逃しを質的に確認する。

## 使用できる列挙値

| 分類 | 値 |
|---|---|
| 作業種別 | `feature`, `bugfix`, `refactor`, `review`, `ops`, `docs` |
| リスク | `low`, `medium`, `high` |
| 構成 | `P0`, `P1`, `P2`, `P3`, `P3+P0`, `P3+P1`, `P3+P2` |
| レビュー関係 | `none`, `fresh_same`, `cross_provider` |
| レビュー結果 | `none`, `accepted`, `changes_required`, `blocked` |
| 検証総合 | `passed`, `failed`, `blocked`, `incomplete` |
| 代替理由 | `none`, `quota`, `rate_limit`, `availability`, `scope_reduced` |
| 使用量の状態 | `missing`, `approximate`, `reported` |
| 介入 | `permission_approval`, `scope_decision`, `acceptance_clarification`, `environment_recovery`, `safety_stop` |
