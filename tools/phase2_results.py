"""Read-only synthesis of the frozen Phase 2 outputs, with a release audit.

No hazard, damage, insurance, reinsurance, or trigger model is recalibrated here.
All money is constant 2022 USD. Missing private inputs permit a clearly marked
metadata preview, never a completed production handoff.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

from tools.reinsurance_capital import CASE_PREFIXES

DIRECTORIES = {
    8: "notebook_8_spatial_correlation",
    9: "notebook_9_correlated_ground_motion",
    10: "notebook_10_correlated_damage_loss",
    11: "notebook_11_reinsurance_capital",
    12: "notebook_12_parametric_basis_risk",
}
HANDOFF_HASHES = {
    8: "b9c68b1ac75e16f2db0f3f005ca017778068a79e117c6e8c3dd2a685eee13fa8",
    9: "c9c8798ea2d6828353a0462297ce7874a35f6ced7a5dabae744c57fbe4adadd5",
    10: "f9bb75c8e596ebdd21b2e4d5ca39c472074d4e79e189c5959c836f3c386f1fc4",
    11: "c9a9ad70a7eb01d679e227442a2f11667a39900d2246550d71e0bb247d316b1e",
    12: "cbd134f3f5c91b79607e2ee457f75d791203319230d985cd627660e1c6d4a655",
}
PHASE1_COMMIT = "be93474ce2ab78d8002d49ae861adb641ae2741d"
BASELINE = "I0_PHASE1_INDEPENDENT"
OUTPUT_NAME = "notebook_13_phase_2_results"


def metadata_path(number, name):
    return f"data/metadata/phase_2/{DIRECTORIES[number]}/notebook_{number}_{name}"


def safe_path(root, relative):
    p = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Nonportable artifact path: {relative}")
    result = (Path(root) / relative).resolve()
    if not result.is_relative_to(Path(root).resolve()):
        raise ValueError("Artifact escapes the repository.")
    return result


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        while block := f.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    return pd.read_csv(path, float_precision="round_trip")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))


def write_csv(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(frame.to_csv(index=False, lineterminator="\n", float_format="%.17g").encode("utf-8"))


def inventory_item(root, path):
    return dict(path=Path(path).relative_to(root).as_posix(),
                bytes=Path(path).stat().st_size, sha256=sha256_file(path))


def check_artifact(root, item, *, legacy_crlf=False):
    """Exact raw match, or an explicitly authorized legacy text-byte match.

    CRLF recovery is limited by the caller to Notebook 08 public metadata. Both
    the legacy size AND hash must match; no semantic JSON canonicalization.
    """
    p = safe_path(root, item["path"])
    if not p.is_file():
        return "MISSING", "raw", None
    actual = sha256_file(p)
    if actual == item["sha256"] and p.stat().st_size == item["bytes"]:
        return "PASS", "raw", actual
    if legacy_crlf and p.suffix in (".csv", ".json"):
        b = p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        if len(b) == item["bytes"] and hashlib.sha256(b).hexdigest() == item["sha256"]:
            return "PASS", "legacy_crlf_reconstruction", actual
    return "FAIL", "raw", actual


def audit_upstream(root, *, verify_processed=True):
    rows, handoffs, validations = [], {}, []
    for number, digest in HANDOFF_HASHES.items():
        relative = metadata_path(number, "final_handoff.json")
        p = safe_path(root, relative)
        actual = sha256_file(p) if p.is_file() else None
        mode = "raw"
        matches = actual == digest
        if number in (8, 9) and p.is_file() and not matches:
            # A Windows file may retain CRLF after Git attributes change. The
            # pinned published handoff is LF; verify exactly that byte view.
            matches = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest
            mode = "legacy_lf_handoff_view"
        if not matches:
            raise RuntimeError(f"Frozen Notebook {number} handoff hash mismatch or missing file. "
                               f"Expected={digest}; actual_raw={actual}; path={relative}")
        h = json.loads(p.read_text(encoding="utf-8"))
        handoffs[number] = h
        if not h.get(f"notebook{number}_complete") or h["validation"]["critical_failures"] != 0:
            raise RuntimeError(f"Notebook {number} is not validated.")
        rows.append(dict(notebook=number, path=relative, status="PASS", hash_mode=mode,
                         expected_sha256=digest, actual_raw_sha256=actual))
        seen = set()
        for item in h["artifact_inventory"]:
            path = item["path"]
            safe_path(root, path)
            if path in seen:
                raise ValueError(f"Duplicate inventory path: {path}")
            seen.add(path)
            private = path.startswith("data/processed/")
            if private and not verify_processed:
                status, mode, actual = "SKIPPED", "preview_only", None
            else:
                legacy = number == 8 and path.startswith(f"data/metadata/phase_2/{DIRECTORIES[8]}/")
                status, mode, actual = check_artifact(root, item, legacy_crlf=legacy)
            rows.append(dict(notebook=number, path=path, status=status, hash_mode=mode,
                             expected_sha256=item["sha256"], actual_raw_sha256=actual))
        v = h["validation"]
        entry = [x for x in h["artifact_inventory"] if x["path"] == v["path"]]
        if len(entry) != 1 or entry[0]["sha256"] != v["sha256"]:
            raise RuntimeError("Validation hash does not agree with inventory.")
        frame = read_csv(safe_path(root, v["path"]))
        if "severity" not in frame:
            frame["severity"] = "critical"
        flags = frame.passed.astype(str).str.lower()
        if not flags.isin(["true", "false"]).all():
            raise ValueError("Invalid validation boolean.")
        frame["passed"] = flags.eq("true")
        if len(frame) != v["checks"] or (~frame.loc[frame.severity.eq("critical"), "passed"]).any():
            raise RuntimeError(f"Notebook {number} critical validation failed.")
        frame.insert(0, "notebook", number)
        validations.append(frame)
    audit = pd.DataFrame(rows)
    failures = audit.loc[~audit.status.isin(["PASS", "SKIPPED"])]
    if not failures.empty:
        raise RuntimeError("Upstream artifact audit failed:\n" + failures[["path", "status"]].to_string(index=False))
    # Pinned handoffs are immutable; these checks also expose the chain to readers.
    for number, h in handoffs.items():
        c = h["frozen_controls"]
        if c.get("catalog_years") != 2_000_000 or c.get("occurrences", c.get("catalog_occurrences")) != 10_630:
            raise RuntimeError(f"Notebook {number} catalog mismatch.")
        if c.get("phase1_commit") != PHASE1_COMMIT:
            raise RuntimeError(f"Notebook {number} Phase 1 reference mismatch.")
    if handoffs[11]["frozen_controls"]["notebook10_handoff_sha256"] != HANDOFF_HASHES[10]:
        raise RuntimeError("Notebook 10 to 11 handoff mismatch.")
    if handoffs[12]["upstream"]["sha256"] != HANDOFF_HASHES[11]:
        raise RuntimeError("Notebook 11 to 12 handoff mismatch.")
    if handoffs[10]["frozen_controls"]["paired_ground_motion_sha256"] != handoffs[9]["paired_output"]["sha256"]:
        raise RuntimeError("Notebook 09 to 10 field mismatch.")
    return audit, handoffs, pd.concat(validations, ignore_index=True)


def paired_comparison(frame, keys, metrics):
    """Pair each correlated row with its I0 row under identical scenario keys."""
    if frame.duplicated(["case_name", *keys]).any():
        raise ValueError("Duplicate case/scenario comparison key.")
    if set(frame.case_name) != set(CASE_PREFIXES):
        raise ValueError("Comparison requires all three dependence cases.")
    base = frame.loc[frame.case_name.eq(BASELINE), [*keys, *metrics]]
    renamed = {m: "baseline_" + m for m in metrics}
    if keys:
        merged = frame.merge(base.rename(columns=renamed), on=keys, how="left", validate="many_to_one", indicator=True)
        if not merged._merge.eq("both").all() or len(frame) != 3 * len(base):
            raise ValueError("Cases do not share a complete common scenario grid.")
        merged = merged.drop(columns="_merge")
    else:
        if len(base) != 1 or len(frame) != 3:
            raise ValueError("Expected one row per dependence case.")
        merged = frame.copy()
        for metric in metrics:
            merged["baseline_" + metric] = base.iloc[0][metric]
    rows = []
    for metric in metrics:
        out = merged[["case_name", *keys]].copy()
        out["metric"] = metric
        out["value"] = merged[metric]
        out["baseline_value"] = merged["baseline_" + metric]
        out["absolute_change"] = out.value - out.baseline_value
        valid = out.baseline_value.abs().gt(1e-12) & np.isfinite(out.baseline_value)
        out["percent_change"] = np.where(valid, 100 * out.absolute_change / out.baseline_value.where(valid), np.nan)
        out["percentage_status"] = np.where(valid, "defined", "undefined_zero_or_missing_baseline")
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def attachment_diagnostics(grid):
    score = "tvar99_5_capital_relief_per_expected_ceded_dollar"
    rows = []
    for case, frame in grid.groupby("case_name", sort=False):
        values = frame[score].to_numpy(float)
        if not np.isfinite(values).all():
            raise ValueError("Attachment scores must be finite.")
        best = values.max()
        tied = frame.loc[np.isclose(values, best, rtol=1e-10, atol=1e-10)]
        unique = len(tied) == 1
        rows.append(dict(case_name=case, criterion=score, best_score=best,
                         tied_designs=len(tied), tested_designs=len(frame),
                         minimum_tied_attachment_2022_usd=tied.attachment_2022_usd.min(),
                         maximum_tied_attachment_2022_usd=tied.attachment_2022_usd.max(),
                         selected_attachment_2022_usd=float(tied.iloc[0].attachment_2022_usd) if unique else np.nan,
                         selection_status="unique_in_tested_grid" if unique else "no_unique_selection",
                         tie_relative_tolerance=1e-10, tie_absolute_tolerance=1e-10))
    return pd.DataFrame(rows)


def load_tables(root):
    names = {
        10: ("case_summary", "damage_state_summary", "pml_table"),
        11: ("program_summary", "occurrence_design_grid", "aggregate_design_grid", "required_limit_summary",
             "diversification_summary", "raroc_assumption_grid", "break_even_premium_grid", "pml_table", "uncertainty_summary"),
        12: ("basis_risk_summary", "tail_risk_table", "uncertainty_summary"),
    }
    return {f"nb{n}_{name}": read_csv(safe_path(root, metadata_path(n, name + ".csv")))
            for n, entries in names.items() for name in entries}


def build_results(tables):
    t = tables
    results = {}
    specs = [
        ("gross_loss_comparison", 10, "case_summary", [], ["ground_up_aal_2022_usd", "gross_insured_aal_2022_usd", "uninsured_aal_2022_usd"]),
        ("gross_pml_comparison", 10, "pml_table", ["loss_basis", "curve_type", "return_period_years", "order_statistic_rank", "tail_support_sufficient"], ["pml_2022_usd"]),
        ("program_comparison", 11, "program_summary", ["program"], ["ceded_aal_2022_usd", "retained_aal_2022_usd", "retained_tvar_99_5_2022_usd", "retained_tvar_tail_capital_99_5_2022_usd", "retained_aep_2500yr_pml_2022_usd"]),
        ("required_limit_comparison", 11, "required_limit_summary", ["target_kind", "target_parameter"], ["required_limit_2022_usd"]),
        ("occurrence_design_comparison", 11, "occurrence_design_grid", ["design_id"], ["ceded_aal_2022_usd", "retained_aep_2500yr_pml_2022_usd", "retained_tvar_99_5_2022_usd"]),
        ("aggregate_design_comparison", 11, "aggregate_design_grid", ["structure", "design_id"], ["ceded_aal_2022_usd", "retained_aep_2500yr_pml_2022_usd", "retained_tvar_99_5_2022_usd"]),
        ("raroc_scenario_comparison", 11, "raroc_assumption_grid", ["program", "premium_multiple_of_gross_aal", "expense_ratio", "ceded_price_multiplier"], ["earned_premium_2022_usd", "underwriting_result_2022_usd", "raroc_using_tvar99_5_tail_capital"]),
        ("break_even_comparison", 11, "break_even_premium_grid", ["program", "ceded_price_multiplier", "expense_ratio"], ["break_even_required_earned_premium_2022_usd"]),
        ("diversification_comparison", 11, "diversification_summary", ["risk_measure", "confidence"], ["diversification_benefit"]),
    ]
    for output, number, source, keys, metrics in specs:
        result = paired_comparison(t[f"nb{number}_{source}"], keys, metrics)
        result["source_path"] = metadata_path(number, source + ".csv")
        result["period"] = "FULL_CATALOG_2000000_YEARS"
        result["unit"] = np.where(result.metric.str.contains("raroc|diversification"), "ratio", "2022_USD")
        results[output] = result
    basis = t["nb12_basis_risk_summary"].query("period == 'EVALUATION' and payout_basis == 'COLLATERALIZED'")
    results["basis_risk_comparison"] = paired_comparison(basis, [], ["payout_aal_2022_usd", "target_aal_2022_usd", "expected_protection_shortfall_2022_usd", "expected_excess_payout_2022_usd", "event_rmse_2022_usd"])
    results["basis_risk_comparison"]["period"] = "EVALUATION_YEARS_1000001_TO_2000000"
    results["basis_risk_comparison"]["unit"] = "2022_USD"
    results["basis_risk_comparison"]["source_path"] = metadata_path(12, "basis_risk_summary.csv")
    results["damage_state_summary"] = t["nb10_damage_state_summary"].copy()
    results["damage_state_summary"]["source_path"] = metadata_path(10, "damage_state_summary.csv")
    tail = t["nb12_tail_risk_table"].query("period == 'EVALUATION'").copy()
    tail["case_name"] = tail.case_prefix.map({v: k for k, v in CASE_PREFIXES.items()})
    tail = tail.rename(columns={"metric": "risk_metric"})
    results["parametric_tail_comparison"] = paired_comparison(tail, ["loss_basis", "risk_metric", "parameter", "tail_count", "headline_supported"], ["value_2022_usd"])
    results["parametric_tail_comparison"]["period"] = "EVALUATION_YEARS_1000001_TO_2000000"
    results["parametric_tail_comparison"]["unit"] = "2022_USD"
    # Keep tail support, units, and signed cash-net semantics intact.
    results["parametric_tail_comparison"]["source_path"] = metadata_path(12, "tail_risk_table.csv")
    results["attachment_selection_diagnostics"] = attachment_diagnostics(t["nb11_occurrence_design_grid"])
    results["diversification_diagnostics"] = t["nb11_diversification_summary"].copy()
    results["diversification_diagnostics"]["interpretation"] = np.where(
        results["diversification_diagnostics"].risk_measure.eq("var"),
        "undefined_ratio_zero_VaR", "AAL_additivity_or_sparse_tail_additivity_at_selected_confidence")
    uncertainty = []
    for n, scope in [(11, "full_catalog_paired_sampling"), (12, "evaluation_paired_sampling_conditional_on_frozen_trigger")]:
        frame = t[f"nb{n}_uncertainty_summary"].copy()
        frame["source_notebook"] = n
        frame["uncertainty_scope"] = scope
        frame["interval_excludes_zero"] = (frame.bootstrap_ci_lower_2022_usd > 0) | (frame.bootstrap_ci_upper_2022_usd < 0)
        uncertainty.append(frame)
    results["paired_uncertainty"] = pd.concat(uncertainty, ignore_index=True)
    results["executive_comparison"] = pd.concat([results[k] for k in ("gross_loss_comparison", "program_comparison", "required_limit_comparison", "basis_risk_comparison", "diversification_comparison")], ignore_index=True)
    return results


LIMITATIONS = [
    ("tail_support", "Return-period estimates with order-statistic rank below 20 are diagnostics, not headline estimates."),
    ("sparse_VaR", "Gross annual VaR at 99% and 99.5% is zero. The corresponding VaR capital and diversification ratios are non-informative."),
    ("attachment_identification", "The TVaR capital-relief-per-ceded-dollar score ties across the tested attachment grid. No unique best attachment is identified."),
    ("diversification", "AAL is additive. At the selected TVaR confidence levels the sparse annual loss support also produces additivity; this does not establish absence of diversification at other quantiles."),
    ("pricing", "RAROC and break-even premiums are assumption grids, not market quotes or central estimates. Matching premium multiples implies different absolute earned premiums across cases."),
    ("uncertainty", "Paired bootstrap intervals quantify catalog sampling variation under frozen models. Notebook 12 intervals condition on the fitted trigger and omit calibration uncertainty."),
    ("trigger_grid", "Both selected distance-decay parameters lie at the candidate grid's upper boundary. Optimality outside that grid is not established."),
    ("parametric_cash", "A source-only payout is identical across cases. Excess payouts and unfunded losses are separate; signed cash-net losses may be negative."),
    ("comparison_period", "Insurance/reinsurance results use all two million years. Parametric headline results use only the held-out final million years."),
    ("model_scope", "Results are conditional on the frozen catalog, portfolio, vulnerability, policy terms, and dependence models. They are a research comparison, not a calibrated capital or placement recommendation."),
    ("legacy_bytes", "Notebook 08 inventory text uses explicit CRLF reconstruction for its original Windows-byte hashes. Notebook 08 and 09 handoffs are pinned to their published LF byte views. Both modes are exposed in the audit; no frozen input is rewritten."),
]


def validate_results(t, r, audit, upstream, *, verify_processed):
    checks = []
    def add(name, passed, detail, severity="critical"):
        checks.append(dict(check_id=name, severity=severity, passed=bool(passed), detail=detail))
    add("all_available_input_hashes_match", audit.status.isin(["PASS", "SKIPPED"]).all(), f"artifacts={len(audit)}")
    add("all_production_artifacts_verified", audit.status.eq("PASS").all() and verify_processed,
        f"skipped={audit.status.eq('SKIPPED').sum()}", "critical" if verify_processed else "warning")
    add("upstream_critical_checks_pass", upstream.loc[upstream.severity.eq("critical"), "passed"].all(), f"checks={len(upstream)}")
    expected = {"nb10_case_summary": 3, "nb10_pml_table": 306, "nb11_program_summary": 12,
                "nb11_occurrence_design_grid": 45, "nb11_aggregate_design_grid": 90,
                "nb11_required_limit_summary": 6, "nb11_diversification_summary": 15,
                "nb11_raroc_assumption_grid": 585, "nb11_break_even_premium_grid": 117,
                "nb11_pml_table": 918, "nb11_uncertainty_summary": 56,
                "nb12_basis_risk_summary": 18, "nb12_tail_risk_table": 576, "nb12_uncertainty_summary": 28}
    add("frozen_table_dimensions", all(len(t[k]) == v for k, v in expected.items()), str(expected))
    p = t["nb11_program_summary"]
    add("program_AAL_reconciliation", np.max(np.abs(p.gross_aal_2022_usd - p.ceded_aal_2022_usd - p.retained_aal_2022_usd)) < .01, "gross = ceded + retained; tolerance $0.01")
    gross = t["nb10_case_summary"].set_index("case_name").gross_insured_aal_2022_usd
    add("insurance_reinsurance_AAL_match", np.allclose(p.gross_aal_2022_usd, p.case_name.map(gross), rtol=0, atol=.01), "Notebook 10 to 11 gross insured AAL")
    basis = t["nb12_basis_risk_summary"].query("period == 'EVALUATION' and payout_basis == 'COLLATERALIZED'")
    add("held_out_basis_comparison", len(basis) == 3 and basis.declared_years.eq(1_000_000).all(), "Held-out years only")
    add("common_parametric_payout", basis.payout_aal_2022_usd.nunique() == 1, "Source-only common payout AAL")
    error = basis.payout_aal_2022_usd - basis.target_aal_2022_usd - basis.expected_excess_payout_2022_usd + basis.expected_protection_shortfall_2022_usd
    add("basis_shortfall_excess_identity", error.abs().max() < .01, "payout - target = excess - shortfall")
    attachment = r["attachment_selection_diagnostics"]
    add("attachment_ties_explicit", attachment.loc[attachment.tied_designs.gt(1), "selected_attachment_2022_usd"].isna().all(), "No arbitrary selection among tied scores")
    uncertainty = r["paired_uncertainty"]
    add("paired_uncertainty_preserved", len(uncertainty) == 84 and uncertainty.bootstrap_replicates.eq(300).all() and (uncertainty.bootstrap_ci_lower_2022_usd <= uncertainty.bootstrap_ci_upper_2022_usd).all(), "56 full-catalog + 28 evaluation rows, 300 paired replicates")
    add("baseline_comparison_zero", all(frame.loc[frame.case_name.eq(BASELINE), "absolute_change"].dropna().abs().le(1e-12).all() for frame in r.values() if "absolute_change" in frame and "case_name" in frame), "All I0 comparisons reconcile to their source baseline")
    add("required_limit_feasibility", t["nb11_required_limit_summary"].feasible.astype(str).str.lower().eq("true").all(), "All six stored target solutions feasible; numerical limit tolerance retained upstream")
    add("limitations_documented", True, f"{len(LIMITATIONS)} explicit interpretation limits")
    return pd.DataFrame(checks)


def make_figures(t, results, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    colors = dict(zip(CASE_PREFIXES, ("#354f70", "#c85a35", "#238879")))
    labels = dict(zip(CASE_PREFIXES, ("I0: independent", "C1: Aldea", "C2: Goda–Atkinson")))
    def save(fig, name, subtitle):
        fig.text(.5, .01, subtitle, ha="center", fontsize=8)
        fig.tight_layout(rect=(0, .04, 1, .95))
        for suffix in ("png", "svg"):
            path = directory / f"{name}.{suffix}"
            fig.savefig(path, dpi=160, metadata={"Date": None} if suffix == "svg" else {"Software": "seismic-correlation-insurance-loss"})
            paths.append(path)
        plt.close(fig)
    with plt.rc_context({"svg.hashsalt": "phase2-notebook13", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
        for ax, curve in zip(axes, ("AEP", "OEP")):
            table = t["nb10_pml_table"]
            table = table.loc[table.loss_basis.eq("gross_insured") & table.curve_type.str.upper().eq(curve) & table.order_statistic_rank.ge(20)]
            for case in CASE_PREFIXES:
                a = table.loc[table.case_name.eq(case)].sort_values("return_period_years")
                ax.plot(a.return_period_years, a.pml_2022_usd / 1e6, label=labels[case], color=colors[case])
            ax.set(xscale="log", xlabel="Return period (years)", ylabel="Gross insured PML (million 2022 USD)", title=curve)
            ax.grid(alpha=.2)
        axes[0].legend(fontsize=8)
        fig.suptitle("Spatial dependence and gross insured tails")
        save(fig, "gross_insured_tail_curves", "Full two-million-year catalog; only order-statistic ranks of at least 20 shown.")
        programs = ["NO_REINSURANCE", "FROZEN_OCCURRENCE_XOL", "STANDALONE_AGGREGATE", "STACKED_OCCURRENCE_PLUS_AGGREGATE"]
        x = np.arange(4)
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, metric, title in zip(axes, ("retained_aep_2500yr_pml_2022_usd", "retained_tvar_tail_capital_99_5_2022_usd"), ("Retained 2,500-year AEP PML", "Retained 99.5% TVaR minus mean")):
            for i, case in enumerate(CASE_PREFIXES):
                a = t["nb11_program_summary"].query("case_name == @case").set_index("program").loc[programs]
                ax.bar(x + (i-1)*.24, a[metric]/1e6, width=.24, color=colors[case], label=labels[case])
            ax.set_xticks(x, ["None", "Occurrence", "Aggregate", "Stacked"])
            ax.set(title=title, ylabel="Million 2022 USD")
        axes[0].legend(fontsize=8)
        fig.suptitle("Four common fixed reinsurance programs")
        save(fig, "fixed_program_tail_comparison", "Full catalog; TVaR tail capital is a research measure. Zero VaR capital is non-informative.")
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
        req = t["nb11_required_limit_summary"]
        for ax, (target, frame) in zip(axes, req.groupby("target_kind", sort=True)):
            frame = frame.set_index("case_name").loc[list(CASE_PREFIXES)]
            ax.bar(["I0", "C1", "C2"], frame.required_limit_2022_usd/1e6, color=list(colors.values()))
            ax.axhline(frame.frozen_limit_2022_usd.iloc[0]/1e6, color="gray", linestyle="--", label="Frozen limit")
            ax.set(title={"aep_pml": "Target: I0 retained 2,500-year AEP PML", "aep_tvar": "Target: I0 retained 99.5% TVaR"}[target], ylabel="Required limit (million 2022 USD)")
            ax.legend(fontsize=8)
        fig.suptitle("Limits required to meet the frozen risk targets")
        save(fig, "required_limit_comparison", "Same attachment and target definition; numerical limit-search tolerance is $1,000.")
        b = t["nb12_basis_risk_summary"].query("period == 'EVALUATION' and payout_basis == 'COLLATERALIZED'").set_index("case_name").loc[list(CASE_PREFIXES)]
        fig, ax = plt.subplots(figsize=(9, 5))
        for i, (metric, label) in enumerate((("expected_protection_shortfall_2022_usd", "Expected protection shortfall"), ("expected_excess_payout_2022_usd", "Expected excess payout"))):
            ax.bar(np.arange(3)+(i-.5)*.34, b[metric]/1000, width=.34, label=label)
        ax.set_xticks(np.arange(3), ["I0", "C1", "C2"])
        ax.set(ylabel="Annual mean (thousand 2022 USD)", title="Held-out parametric basis risk")
        ax.legend()
        save(fig, "evaluation_basis_risk", "Evaluation years 1,000,001–2,000,000; common payout, case-specific target recovery.")
        u = t["nb11_uncertainty_summary"].query("program == 'FROZEN_OCCURRENCE_XOL' and metric_name == 'aep_pml_2500yr'")
        fig, ax = plt.subplots(figsize=(9, 3.5))
        for i, row in enumerate(u.itertuples()):
            ax.plot([row.bootstrap_ci_lower_2022_usd/1e6, row.bootstrap_ci_upper_2022_usd/1e6], [i, i], color="#354f70", linewidth=3)
            ax.scatter(row.absolute_change_2022_usd/1e6, i, color="#c85a35", zorder=3)
        ax.set_yticks(range(len(u)), [row.case_series.split(":")[-1].split("_")[0] + " minus I0" for row in u.itertuples()])
        ax.axvline(0, color="gray", linestyle="--")
        ax.set(xlabel="Difference (million 2022 USD)", title="Frozen occurrence program: retained 2,500-year AEP PML")
        save(fig, "paired_sampling_uncertainty", "Stored paired bootstrap intervals, 300 replicates; conditional on frozen models.")
    return paths


def write_report(path, results, *, production_complete):
    rows = ["# Phase 2 results and validation", "", "Status: " + ("production artifact audit passed" if production_complete else "metadata preview; production artifact audit pending"), "",
            "This synthesis compares frozen dependence cases. It does not recalibrate the hazard, damage, financial, or parametric models.", "",
            "## Executive comparisons", "", "Money is constant 2022 USD. Changes are relative to I0. Insurance and reinsurance use the full catalog; parametric results use the held-out evaluation years.", "",
            "| Case | Measure / program | Value | Change from I0 |", "|---|---|---:|---:|"]
    e = results["executive_comparison"]
    for row in e.to_dict("records"):
        context = " / ".join(str(row[k]) for k in ("program", "target_kind", "target_parameter", "risk_measure", "confidence", "period") if k in row and pd.notna(row[k]))
        value = "undefined" if pd.isna(row["value"]) else f"{row['value']:,.6g}"
        change = "undefined" if pd.isna(row["absolute_change"]) else f"{row['absolute_change']:,.6g}"
        rows.append(f"| {row['case_name']} | {row['metric']} / {context} | {value} | {change} |")
    rows += ["", "## Attachment identification", "", "| Case | Tied designs | Attachment range (2022 USD) | Selection |", "|---|---:|---:|---|"]
    for row in results["attachment_selection_diagnostics"].itertuples():
        rows.append(f"| {row.case_name} | {row.tied_designs} | {row.minimum_tied_attachment_2022_usd:,.2f} to {row.maximum_tied_attachment_2022_usd:,.2f} | {row.selection_status} |")
    rows += ["", "## RAROC assumption range", "", "Ranges span the tested price and expense assumptions, not statistical confidence intervals. Use the detailed paired scenario table for matching assumptions.", "", "| Case | Program | Minimum RAROC | Maximum RAROC |", "|---|---|---:|---:|"]
    raroc = results["raroc_scenario_comparison"].query("metric == 'raroc_using_tvar99_5_tail_capital'")
    for (case, program), frame in raroc.groupby(["case_name", "program"], sort=False):
        rows.append(f"| {case} | {program} | {frame.value.min():.4%} | {frame.value.max():.4%} |")
    rows += ["", "## Interpretation", "",
             "A change in spatial dependence need not increase every loss metric. Read the paired differences together with their sampling intervals, using the same program and period.", "",
             "The attachment-selection diagnostic does not identify a unique best design under the stored TVaR efficiency criterion. The scenario tables preserve RAROC assumptions and absolute earned premiums rather than treating them as observed pricing.", "",
             "## Limitations", ""]
    rows += [f"- **{name}:** {detail}" for name, detail in LIMITATIONS]
    rows += ["", "## Evidence", "", "The input audit records every upstream inventory item. The executive, design, uncertainty, and diagnostic CSV tables preserve source references. Figures are supplied as PNG and SVG. The final JSON inventory records output byte sizes and SHA-256 hashes.", "",
             "Passing Notebook 13 does not create a Git tag, merge a pull request, or publish a release. Those are separate reviewed repository actions.", ""]
    Path(path).write_bytes("\n".join(rows).encode("utf-8"))
