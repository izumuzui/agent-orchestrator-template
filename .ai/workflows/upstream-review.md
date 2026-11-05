# Requirements and design milestone review (opt-in)

Invoke at requirement agreement, detailed-design completion, implementation
completion, or when implementation/review exposes upstream ambiguity. The
review is read-only and supplements required code review and verification.
Declare sources, revisions, allowed scope, evidence access and a one-pass budget
before starting; do not ask for an entire private conversation by default.

| Axis | Evidence question |
|---|---|
| Questions | Were consequential open choices raised at the right time, without excessive questioning? |
| Intent | Does the agreed artifact reflect the user's goal and constraints? |
| Assumptions | Are inferred behaviors marked as assumptions rather than agreements? |
| Clarity | Can a reader explain the decision and resulting behavior? |
| Agreement | Are decided, open and deferred items distinguished, with owner/next action? |
| Consistency | Does the revision preserve earlier agreements and constraints? |
| Traceability | Can requirements be followed through design decisions, implementation and proof? |

Question priority depends on impact and rework cost if an assumption is wrong.
Clarify consequential unresolved choices before dependent work. For reversible,
low-impact details, state a reasonable assumption and proceed. Do not mandate a
question count or ask about every detail. Do not treat silence as agreement.

Freeze an agreement snapshot with: requirement ID and safe source reference,
revision, goal/constraints, explicit decisions, assumptions, open/deferred
questions with owner/next step, linked design IDs and intended proof. Absence
of a link is a gap to inspect, not proof of a process failure. Record changes
with a new acceptance version rather than rewriting the earlier agreement.

Review output per candidate: phase, axis, observed fact and evidence handle,
expected behavior, impact, separate hypothesis/confidence, unknowns and next
validation. Include covered axes with no observable issue; never manufacture
findings. An AI self-review is a candidate assessment, not confirmed cause or
independent acceptance. Apply the normal fresh-review requirement where due.

If implementation exposes ambiguity, trace the affected requirement and design
revision and record where the decision was made or remained open. Correct the
current artifact through the normal change workflow. Store process candidates
separately for later evaluation; this review itself changes no artifacts or
permanent rules. Use the existing curated feedback workflow only after a
substantive defect is established. Keep private source content out of reports.

Pilot on 5–10 milestones. Compare rework, consequential unresolved choices,
question burden, review time and evidence usefulness. Stop or simplify the
review if it adds cost without useful detection. Rollback removes the optional
milestone invocation, not existing acceptance history or mandatory proof.

This template-local extension is opt-in and not in the distribution manifest.
Add a project-specific routing entry when adopting it; no schedule is installed.
