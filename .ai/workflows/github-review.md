# GitHub CI and Codex review

## What runs where

- `.github/workflows/verify.yml`: deterministic common gate on PRs and main pushes.
  GitHub-hosted runner, read-only token, no model/API credentials, timeout and
  concurrency cap. GitHub Actions billing/limits still apply to the repository.
- Native Codex review: enable the repository separately in Codex code-review
  settings. It uses the signed-in plan's available review allowance. No API key
  is added to this workflow. Availability and remaining limits are account-specific.
- Feedback: the working agent fetches PR comments into the ignored local inbox,
  curates corrections, verifies changes, and proposes durable lessons in Git.

Local configuration does not enable hosted review. To activate after publishing:

1. Connect the intended GitHub repository to Codex.
2. Open https://chatgpt.com/settings/code-review and select the repository.
3. Enable Automatic review and choose a trigger appropriate to the usage budget.
4. Open a test PR and verify both `Agent verification / verify` and a Codex review
   actually appear. Account/repository access and quotas can block review.
5. If required, configure branch protection/rulesets to require the CI check.
   This template does not modify branch protection or automatically merge PRs.

Use `@codex review` in an authorized PR comment for a manual trigger. Avoid bot
loops that repost mentions on each review. CI success is not independent review
acceptance, and absence of a bot finding does not verify visual UI quality.
Codex native reviews focus on serious defects; use the separate UI evidence and
feedback procedure for visual preferences and lower-priority improvements.

For product adoption, add executable `scripts/project/verify.sh` with actual
lint/type/build/test checks. Without it, template CI explicitly skips product
verification and must not be represented as a verified product release.

## Sources checked 2026-10-24

- Harness design talk (principles translated to this template, not a verbatim copy):
  https://speakerdeck.com/kinopeee/hanesu-sekkei-nyuumon-kiso-chishiki-no-seiri-kara-jitsumu-heno-suteppu-appu
- Codex native review setup and repository review instructions:
  https://learn.chatgpt.com/docs/third-party/github
- GitHub least privilege and untrusted-input guidance:
  https://docs.github.com/en/actions/reference/security/secure-use

Claude Actions is intentionally not configured for this user's selected setup.
