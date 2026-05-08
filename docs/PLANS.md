# ExecPlans

An ExecPlan is a living implementation plan. It must be self-contained enough for an agent to resume the work from the plan and repository alone.

Each plan should include:

- Purpose and user-visible outcome.
- Scope and non-goals.
- Milestones with concrete validation commands.
- Current status and decisions made.
- Risks, open questions, and evidence from validation.

Keep active plans in `docs/exec-plans/`. Move completed plans to a completed folder only when the repo has enough plans to justify that split.
