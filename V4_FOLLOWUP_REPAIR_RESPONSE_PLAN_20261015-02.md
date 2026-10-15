# Response plan for failed follow-up repair pilot 20261015-02

The pilot and audit are preserved in
`results/v4/phase10_followup/archive/repair_followup_20261015-02/`; its
`manifest.json` and `manifest.sha256` identify the immutable failed archive.
Do not edit, rescore, replace, or discard its ten proposals.

## Required response before another pilot

1. **Trace the selected-prefill handoff through the real runner.** The direct
   native fixture passed, but the pilot's ten candidates still carried G0's
   parent hash. Build a data-free integration fixture using the same EvE
   configuration, native driver, prompt-file route, and evaluator context
   builder. Require the candidate to use the selected prefill's
   `lineage_state.json["language_hash"]` before evaluation. Preserve the
   original failed attempts unchanged.
2. **Capture each worker transcript.** Retain one JSONL transcript per native
   proposal invocation and verify its recorded path and hash in the archive.
   No proposal in this pilot has such a transcript; completion artifacts and
   error text are insufficient to establish the worker's actual actions.
3. **Preserve the tmux failure details.** For every `respawn-pane` failure,
   record the exact command, return code, stdout, and stderr in the attempt
   evidence. The current error files omit stdout and stderr; do not infer a
   cause from the command string.
4. **Keep the original gate accounting.** A later separately contracted run
   must keep ten submitted proposals, no replacements, the eight-valid and
   eight-distinct thresholds, macro introduction/use and descendant-use
   gates, resource limits, transcript capture, and zero protected-boundary
   violations. Start from fresh macro-free G0 and use new unused run, record,
   and archive paths.
5. **Freeze a new contract only after the data-free gates pass.** Pin all
   changed source, runtime, sandbox, prompt, fixture, and archive evidence.
   Do not launch another pilot automatically from this response plan. Keep the
   prohibition on paid credits, plan upgrades, and rate-limit resets.

## Stop point

The 20261015-02 pilot failed 0/10 candidate-context validations and captured
zero worker JSONL transcripts. The post-run scan found no monitored boundary
change across ten structural bundles and no fresh-G0 mismatch, but the missing
transcripts leave the full protected-boundary gate incomplete. M1 remains open.
No discovery conclusion may be drawn from this run.
