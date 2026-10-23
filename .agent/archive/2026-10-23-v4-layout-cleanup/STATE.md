# Current state

V4 is integrated into main and published to origin as a frozen exploratory
study. The user explicitly authorized merge and push on 2026-10-23.

Completed:

- History-preserving merge commit: 44789d120481c5b98ee5384f219f08f80a9c6022.
- Prepared study branch: f1cbaf48558b4b2c7e9855dd9a28c13e1205bd13.
- Atomically pushed main, v4-evolving-bias-language, and v4-exploratory-final.
- Remote branch refs, annotated tag object, and peeled tag target verified with
  git ls-remote. The tag still targets 36ea8f5016007455e342d387ffda00bb64666f95.
- Current handoff and evidence manifest record the verified publication.

Validation:

- The merged tree matched the previously validated V4 branch exactly.
- Manifest sidecar, checksum index, and all 99 artifact hashes match.
- Source, tests, scientific protocols, and historical results retain their
  frozen bytes. The tag object is unchanged.
- The earlier 208 focused deterministic tests remain the software validation;
  tests were not repeated for identical source and publication metadata.
- Git diff whitespace checks passed; no remote CI result is claimed.

Known issues remain documented: E1 final-slot defect; incomplete discovery
with parent-language hash failures; no selected G* or fresh-search efficacy
evidence. Scientific conclusions and preserved failures remain unchanged.

Current: publication and documentation checkpoint complete.
Next: no further V4 work is scheduled. Keep the original tag immutable.
No model request, research run, new evaluation, or official-test loader was
invoked during integration and publication.
