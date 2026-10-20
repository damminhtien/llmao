# Current state

E3 is complete. Stop here; do not launch another evaluation, model request, or search unless the user explicitly asks.

## Result

- Report: `results/v4/e3/e2_macro_program_evaluation_2026-10-20/REPORT.md`
- Machine-readable records: `results/v4/e3/e2_macro_program_evaluation_2026-10-20/e3_results.json`
- Exactly three E2-distinct expanded G0 programs were evaluated. No exact canonical expanded-AST match existed in E1 records.
- E1 shared initial best: 0.490582252501 fitness, 0.493 validation accuracy.
- `stroke_degree_profile`: 0.491352636567 fitness, 0.4950 accuracy, 19 features.
- `multiscale_spatial_profile`: 0.822582448734 fitness, 0.8280 accuracy, 116 features.
- `multiscale_spatial_degree_profile`: 0.778964810772 fitness, 0.7825 accuracy, 18 features.

## Data and provenance

- Train-only manifest SHA-256: `26c3e3f7b8ee8b2eb3169d684fbc4bf7e0c429f38f0e7bd2654278b87cef63f4`.
- E1 split fingerprint: `41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`.
- Official test data was not accessed. No model or optimizer ran. E1/E2 input hashes were rechecked after scoring and remained unchanged.

## Limitations

E1 artifacts do not record the full evaluator configuration or dataset fingerprint, so all three E3 scores were freshly measured in the current E1 environment. Feature runtime depends on local timing and cross-candidate subtree-cache reuse. These descriptive scores do not measure search efficiency or establish causal macro utility or transfer.
