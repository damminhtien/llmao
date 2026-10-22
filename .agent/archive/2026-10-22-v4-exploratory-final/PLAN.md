# E4 milestones

- [x] Inspect E1 source, frozen inputs, branch state, active workers, and fresh
  output path; archive the completed E3 task record.
- [x] Implement the small E4 runner using the E1 optimizer/evaluator, with fixed
  recipe guidance and optimizer seed 202.
- [x] Add deterministic tests for recipe equivalence, macro expansion, shared
  initial records, raw macro tracing, focus policy, hard budgets, and train-only
  data access.
- [x] Run no-token E4 preflight. It passed with zero LLM requests.
- [x] Run exactly the G0-recipe and G_pilot-macro searches sequentially, each
  under the frozen attempt/request/token limits.
- [x] Analyze and report both runs, recheck E1/E2/E3 evidence hashes, and update
  this state.
- [x] Review the final diff and commit only E4 code, tests, and workflow records.

No additional seed or search is authorized by this task.
