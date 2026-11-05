# 共通の検証条件

実行したAIの名前ではなく証拠で検証を判断する。

| 総合状態 | 意味 |
|---|---|
| `passed` | 必須の証拠がすべて確認できた |
| `failed` | 変更によって必須検査が一つ以上失敗した |
| `blocked` | 環境上の理由で必須検査を一つ以上実行できない |
| `incomplete` | 必須検査が未実施、または証拠不足 |

`skipped` は実装前に必須でないと宣言した検査だけに使う。必須検査の実行不能を成功扱いにしない。

```bash
scripts/agent/verify-change.sh agent-env   # 共通環境の整合性だけ
scripts/agent/verify-change.sh ci          # 共通検証と固有のciモード
scripts/agent/verify-change.sh full        # 共通検証と固有のfullモード
scripts/agent/verify-change.sh <mode>      # 固有モード
```

`ci` / `full` は共通の回帰テストと `scripts/project/verify.sh <mode>` を実行する。製品の検査と追加モードは `.ai/verification/project.md` に定義する。
固有の検証コマンドは、成功なら終了コード0、環境による必須検査の実行不能なら3、失敗ならそれ以外の非0を返す。コマンドがなければ製品検証は `[SKIPPED]` であり、製品変更の検証済み完了と報告しない。
反復中は狭い検証から始め、完了前に該当する全体検証を行う。実際のコマンドと結果を、成功、変更による失敗、確認済みの既存失敗、事前宣言した非必須の省略、環境による実行不能に分ける。
原則3回まで。同じ失敗2回で要求・診断・設計を見直す。
