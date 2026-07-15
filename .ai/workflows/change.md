# Change workflow

1. Read the relevant knowledge, standards, and existing implementation.
2. Build a reviewer bootstrap packet containing only task ID, requirement
   sources, risk, and scope.
3. Derive acceptance from requirement sources before reading or writing an
   implementation plan. Give each acceptance item a stable ID and source.
4. Freeze `acceptance_version`, allowed scope, forbidden scope, proof, stop
   condition, and retry bound in the handoff.
5. Select the role pattern in `routing.md` and reserve routing before writing.
6. Keep one writer. Explorers and reviewers remain read-only.
7. Implement the smallest coherent slice and run focused proof.
8. Run the common verification contract.
9. If independent review is required, follow `review.md` in two stages.
10. Apply accepted findings through the same writer and rerun affected proof.
11. Check whether durable knowledge or routing policy needs an update.
12. Record the terminal task event without free text or private content.

## Loops

- Default: turn-based
- Goal-based: only with machine-checkable acceptance and an explicit attempt cap
- Time-based: only for monitoring with explicit authorization and a stop rule
- Proactive: not enabled by this template

Do not silently change frozen acceptance after implementation begins. Create a
new version, preserve the old one, and record a `scope_decision` intervention.
