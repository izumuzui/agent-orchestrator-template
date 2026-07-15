# Bounded orchestration workflow

Use orchestration only when independent read-heavy work or a separate review is
worth more than the coordination cost. Keep small, ambiguous, or write-heavy
work in one primary context.

## Roles

- Primary: owns scope, synthesis, routing, and user communication
- Planner: freezes acceptance and plan for P2
- Explorer: read-only, one bounded question, evidence-only return
- Writer: the only role allowed to edit the shared worktree
- Reviewer: read-only, fresh context, follows the two-stage review workflow

## Bounds

- one shared-worktree writer
- at most two parallel explorers
- no recursive delegation by default
- no duplicate investigation or competing shared-worktree implementations
- default maximum of three implementation/verification rounds
- same failure twice triggers re-diagnosis

## Lifecycle

1. Primary defines the measurable stop condition and privacy boundary.
2. Reserve routing and determine whether calibration, sentinel, or risk requires
   independent review.
3. Assign bounded read-only questions with exact files and return shape.
4. Synthesize evidence before the writer edits.
5. Writer implements and verifies.
6. Reviewer independently derives acceptance from the bootstrap packet, then
   reviews frozen acceptance, diff, and evidence.
7. Writer applies accepted findings and reruns affected proof.
8. Primary records the terminal event and any durable policy decision.

Do not delegate deployment, production service control, destructive actions,
credentials, private raw data, or external mutations. Those require their
normal authorization and safety workflows regardless of role pattern.
