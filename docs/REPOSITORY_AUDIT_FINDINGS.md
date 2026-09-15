# Repository Audit Findings

Audit milestone: Phase 2 release and reproducibility validation

Validated release: `v2.0.0`

Validated commit: `97a190d94d965f4287386dcfa41376b1ae60e8c8`

## Current status

**Phase 1 and Phase 2 are complete, validated, integrated, and released.**

The repository contains all 13 notebooks, the supporting Python and Java source, portable validation metadata, the final Phase 2 report, and selected publication figures. The Phase 1 baseline remains frozen under `v1.0.0`, and the completed correlation and risk-transfer extension is published under `v2.0.0`.

The final validation evidence includes:

- 92 passing automated tests;
- 62 repository checks with zero critical failures;
- 65 Notebook 13 upstream artifact checks with no skipped production checks;
- 14 passing final synthesis checks;
- verified SHA-256 hashes and byte sizes for all 32 Notebook 13 publication artifacts.

## Resolved repository-hardening findings

The earlier Phase 1 audit identified missing setup files, incomplete repository validation, machine-specific paths, limited Git exclusions, and README rendering issues. Those items were addressed before the Phase 1 release and carried forward into Phase 2.

The current repository includes:

- `requirements.txt` and `SETUP.md`;
- `tools/validate_repository.py`;
- continuous notebook numbering from 01 through 13;
- portable public paths in Phase 2 handoffs and metadata;
- expanded environment, cache, log, build, and generated-data exclusions;
- tracked, readable project figures;
- linked setup, validation, case-study, and final-results documentation;
- deterministic random streams, chunk manifests, restart markers, and artifact hashes.

## Supported environment

The complete workflow was validated end to end on Windows with Python 3.12.3. Notebook 2 uses JDK 11, the pinned `nshmp-haz 2.6.5` source, and its Gradle 7.3.1 wrapper.

Notebook 2 currently invokes `cmd.exe` and `gradlew.bat`, so its controlled Java build path is Windows-specific. The Python stages are generally portable, but a complete macOS or Linux production run has not been certified.

## Reproducibility boundaries

The public repository intentionally excludes several large or local inputs:

- the enriched Seaside exposure workbook;
- downloaded USGS model and Java source archives;
- compiled Java classes and build caches;
- full generated ground-motion, damage, loss, reinsurance, and annual simulation tables.

The expected local exposure path is:

```text
data/raw/exposure/seaside_nsi/gdf_NSI_Map_with_period_seaside.xlsx
```

A public clone can install the environment, validate tracked files, inspect all notebooks and public metadata, and begin the workflow. Full production reproduction additionally requires the local exposure workbook and regeneration of excluded artifacts.

Notebook 13 records hashes and sizes for the private upstream artifacts used in the production synthesis. Its public preview mode reports skipped private checks explicitly and cannot create a completed production handoff.

The Notebook 13 production handoff retains `release_published: false` and its pre-release next step because the file was generated and hashed before publication. Those historical fields are preserved rather than rewritten after the fact. The GitHub `v2.0.0` release page records the later reviewed publication action.

## Scientific interpretation limits

The project is a transparent research and portfolio demonstration. It is not a production catastrophe model, insurance quotation, reinsurance placement recommendation, market price, or regulatory capital estimate.

Key limits include:

- one synthetic 470-building W2 portfolio in Seaside, Oregon;
- model-conditioned spatial-correlation estimates using two analog models;
- HAZUS-style fragility and repair-cost approximations;
- building repair loss only;
- synthetic insurance, reinsurance, and parametric terms;
- no contents, business interruption, demand surge, claims inflation, or reinstatement pricing;
- sparse annual losses that make selected VaR measures non-informative;
- limited order-statistic support at the most extreme return periods;
- bootstrap intervals conditional on the implemented models and frozen trigger.

These limitations are retained in the README, project case study, Phase 2 design, final results report, and release notes.

## Release references

- [Phase 1 release `v1.0.0`](https://github.com/NatCatAnalystRandle/seismic-correlation-insurance-loss/releases/tag/v1.0.0)
- [Phase 2 release `v2.0.0`](https://github.com/NatCatAnalystRandle/seismic-correlation-insurance-loss/releases/tag/v2.0.0)
- [Final Phase 2 results report](../data/metadata/phase_2/notebook_13_phase_2_results/notebook_13_results_report.md)
- [Repository validation checklist](REPOSITORY_VALIDATION_CHECKLIST.md)
