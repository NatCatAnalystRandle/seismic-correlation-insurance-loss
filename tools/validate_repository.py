#!/usr/bin/env python3
"""Validate the public repository structure and reproducibility contract.

The script uses only the Python standard library so it can run immediately
following a fresh clone, before project dependencies are installed.

Examples
--------
Repository-only validation during development:

    python tools/validate_repository.py --allow-dirty

Final repository milestone validation:

    python tools/validate_repository.py

Fresh-clone runtime validation, including Java availability:

    python tools/validate_repository.py --profile runtime
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence
from urllib.parse import unquote, urlsplit

PROJECT_NAME = "seismic-correlation-insurance-loss"
TESTED_PYTHON = (3, 12, 3)
REQUIRED_JAVA_MAJOR = 11
PINNED_NSHMP_HAZ_TAG = "2.6.5"
PINNED_GRADLE_VERSION = "7.3.1"

EXPECTED_NOTEBOOKS = [
    "01_download_and_inspect_usgs_nshm2018.ipynb",
    "02_extract_usgs_rupture_rates.ipynb",
    "03_generate_annual_event_catalog.ipynb",
    "04_generate_ground_motion_fields.ipynb",
    "05_calculate_ground_up_losses.ipynb",
    "06_apply_insurance_terms.ipynb",
    "07_baseline_results_and_validation.ipynb",
]

REQUIRED_ROOT_FILES = [
    ".gitattributes",
    ".gitignore",
    "README.md",
    "SETUP.md",
    "requirements.txt",
]

REQUIRED_DOCUMENTATION = [
    "docs/REPOSITORY_AUDIT_FINDINGS.md",
    "docs/REPOSITORY_VALIDATION_CHECKLIST.md",
]

REQUIRED_METADATA_HANDOFFS = [
    "data/metadata/notebook_2_completion_metadata.json",
    "data/metadata/notebook_2_final_validation.csv",
    "data/metadata/notebook_3_completion_metadata.json",
    "data/metadata/notebook_3_final_validation.csv",
    "data/metadata/notebook_4_final_validation.csv",
    "data/metadata/notebook_4_final_summary.json",
    "data/metadata/notebook_4_final_handoff/notebook_5_input_handoff.json",
    "data/metadata/notebook_5_damage_loss/notebook_5_cell_12_summary.json",
    "data/metadata/notebook_5_damage_loss/notebook_5_cell_12_validation.csv",
    "data/metadata/notebook_6_insurance_terms/notebook_6_final_handoff.json",
    "data/metadata/notebook_6_insurance_terms/notebook_6_cell_8_summary.json",
    "data/metadata/notebook_6_insurance_terms/notebook_6_cell_8_validation.csv",
    "data/metadata/notebook_7_baseline_results_validation/notebook_7_final_handoff.json",
    "data/metadata/notebook_7_baseline_results_validation/notebook_7_cell_6_summary.json",
    "data/metadata/notebook_7_baseline_results_validation/notebook_7_cell_6_validation.csv",
]

REQUIRED_JAVA_SOURCES = [
    "tools/parker_gmm_inspection/AuthoritativeRuptureSiteDistances.java",
    "tools/parker_gmm_inspection/ControlledRuptureRetrieval.java",
    "tools/parker_gmm_inspection/ParkerBranchProbe.java",
    "tools/parker_gmm_inspection/ParkerDepthInputProbe.java",
    "tools/parker_gmm_inspection/ParkerGmmInventory.java",
    "tools/usgs_rupture_rate_exporter/print_runtime_classpath.gradle",
    "tools/usgs_rupture_rate_exporter/rupture_set_rate_audit/src/RuptureSetRateAudit.java",
    "tools/usgs_rupture_rate_exporter/src/RuptureRateExporter.java",
    "tools/usgs_rupture_rate_exporter/tree_inventory/SourceTreeInventory.java",
]

SELECTED_FIGURES = [
    "data/processed/notebook_7_baseline_results_validation/plots/baseline_aal_loss_flow.png",
    "data/processed/notebook_7_baseline_results_validation/plots/baseline_full_aep_exceedance_curves.png",
    "data/processed/notebook_7_baseline_results_validation/plots/baseline_full_oep_exceedance_curves.png",
    "data/processed/notebook_7_baseline_results_validation/plots/baseline_source_aal_contributions.png",
]

REQUIRED_GITIGNORE_FRAGMENTS = [
    "data/raw/usgs_nshm_conus_2018/",
    "data/processed/**",
    "__pycache__/",
    "*.py[cod]",
    ".ipynb_checkpoints/",
    ".venv/",
    ".env",
    "*.log",
    "*.tmp",
    "**/*.class",
    "**/build/",
    "tools/**/classes/",
    "tools/**/*_arguments.txt",
]

FORBIDDEN_TRACKED_SUFFIXES = {
    ".class",
    ".log",
    ".pyc",
    ".pyo",
    ".swp",
    ".temp",
    ".tmp",
}

FORBIDDEN_TRACKED_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

FORBIDDEN_TRACKED_PATH_PARTS = {
    ".gradle",
    ".idea",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
}

TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".csv",
    ".gitignore",
    ".gitattributes",
    ".gradle",
    ".ini",
    ".ipynb",
    ".java",
    ".json",
    ".md",
    ".properties",
    ".py",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}

IMPORT_TO_DISTRIBUTION = {
    "IPython": "ipython",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "requests": "requests",
    "scipy": "scipy",
}

ENVIRONMENT_ONLY_REQUIREMENTS = {
    "ipykernel",
    "jupyterlab",
}

SECRET_PATTERNS = [
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)"
            r"\s*[:=]\s*[\"']([^\"']{8,})[\"']"
        ),
    ),
]

WINDOWS_HOME_RE = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"']+")
POSIX_HOME_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^/\s\"']+")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"(?i)\b(?:src|href)\s*=\s*[\"']([^\"']+)[\"']")
DUPLICATE_NOTEBOOK_RE = re.compile(r"(?i)\.ipynb(?:\.ipynb)+$")
NUMBERED_NOTEBOOK_RE = re.compile(r"^(\d{2})_.+\.ipynb$")


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    severity: str
    passed: bool
    detail: str


class RepositoryValidator:
    def __init__(
        self,
        root: Path,
        *,
        profile: str,
        max_tracked_mb: float,
        allow_dirty: bool,
    ) -> None:
        self.root = root.resolve()
        self.profile = profile
        self.max_tracked_bytes = int(max_tracked_mb * 1024 * 1024)
        self.allow_dirty = allow_dirty
        self.results: list[CheckResult] = []
        self.tracked_files: list[str] = []
        self.tracked_blob_sizes: dict[str, int] = {}

    def add(self, check_id: str, passed: bool, detail: str, severity: str = "critical") -> None:
        self.results.append(
            CheckResult(
                check_id=check_id,
                severity=severity,
                passed=bool(passed),
                detail=str(detail),
            )
        )

    def run(self) -> list[CheckResult]:
        self.check_git_repository()
        self.check_required_files()
        self.check_notebooks()
        self.check_required_project_artifacts()
        self.check_readme_links_and_mermaid()
        self.check_gitignore()
        self.check_tracked_artifacts_and_sizes()
        self.check_machine_specific_paths()
        self.check_secrets()
        self.check_environment_specification()
        self.check_java_environment()
        self.check_git_status()
        return self.results

    def run_command(self, command: Sequence[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )

    def check_git_repository(self) -> None:
        git = shutil.which("git")
        self.add("git_executable_available", git is not None, git or "git was not found on PATH")
        if git is None:
            return

        result = self.run_command([git, "rev-parse", "--show-toplevel"])
        is_repo = result.returncode == 0
        resolved_top = Path(result.stdout.strip()).resolve() if is_repo else None
        self.add(
            "repository_is_git_worktree",
            is_repo and resolved_top == self.root,
            f"detected_root={resolved_top}; expected_root={self.root}",
        )
        if not is_repo:
            return

        tracked = self.run_command([git, "ls-files", "-z"])
        if tracked.returncode != 0:
            self.add("tracked_file_inventory_available", False, tracked.stderr.strip())
            return

        self.tracked_files = sorted(path for path in tracked.stdout.split("\0") if path)
        self.add(
            "tracked_file_inventory_available",
            bool(self.tracked_files),
            f"tracked_files={len(self.tracked_files):,}",
        )
        self.tracked_blob_sizes = self.get_index_blob_sizes(git)

    def get_index_blob_sizes(self, git: str) -> dict[str, int]:
        index_result = self.run_command([git, "ls-files", "-s", "-z"])
        if index_result.returncode != 0:
            return {}

        path_to_sha: dict[str, str] = {}
        for record in index_result.stdout.split("\0"):
            if not record:
                continue
            metadata, separator, path = record.partition("\t")
            if not separator:
                continue
            parts = metadata.split()
            if len(parts) >= 2:
                path_to_sha[path] = parts[1]

        unique_shas = sorted(set(path_to_sha.values()))
        if not unique_shas:
            return {}

        process = subprocess.run(
            [git, "cat-file", "--batch-check=%(objectname) %(objectsize)"],
            cwd=self.root,
            input="\n".join(unique_shas) + "\n",
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if process.returncode != 0:
            return {}

        sha_sizes: dict[str, int] = {}
        for line in process.stdout.splitlines():
            sha, _, size = line.partition(" ")
            try:
                sha_sizes[sha] = int(size)
            except ValueError:
                continue
        return {path: sha_sizes.get(sha, -1) for path, sha in path_to_sha.items()}

    def check_required_files(self) -> None:
        for relative in [*REQUIRED_ROOT_FILES, *REQUIRED_DOCUMENTATION]:
            path = self.root / relative
            self.add(
                f"required_file:{relative}",
                path.is_file() and path.stat().st_size > 0,
                relative,
            )
            if self.tracked_files:
                self.add(
                    f"required_file_tracked:{relative}",
                    relative in self.tracked_files,
                    relative,
                )

    def check_notebooks(self) -> None:
        root_notebooks = sorted(path.name for path in self.root.glob("*.ipynb"))
        self.add(
            "expected_root_notebook_names",
            root_notebooks == EXPECTED_NOTEBOOKS,
            f"actual={root_notebooks}; expected={EXPECTED_NOTEBOOKS}",
        )

        numbered = []
        for name in root_notebooks:
            match = NUMBERED_NOTEBOOK_RE.match(name)
            if match:
                numbered.append(int(match.group(1)))
        self.add(
            "notebook_numbering_continuous",
            numbered == list(range(1, 8)),
            f"numbers={numbered}",
        )

        duplicate_extensions = [path for path in self.tracked_files if DUPLICATE_NOTEBOOK_RE.search(path)]
        self.add(
            "no_duplicate_notebook_extensions",
            not duplicate_extensions,
            f"matches={duplicate_extensions[:20]}",
        )

        recorded_versions: dict[str, str] = {}
        for name in EXPECTED_NOTEBOOKS:
            path = self.root / name
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.add(f"notebook_valid_json:{name}", False, repr(exc))
                continue

            valid_structure = (
                isinstance(payload, dict)
                and payload.get("nbformat") == 4
                and isinstance(payload.get("cells"), list)
                and all(
                    isinstance(cell, dict)
                    and cell.get("cell_type") in {"code", "markdown", "raw"}
                    and isinstance(cell.get("source", []), (list, str))
                    for cell in payload.get("cells", [])
                )
            )
            self.add(
                f"notebook_valid_json:{name}",
                valid_structure,
                f"nbformat={payload.get('nbformat')}; cells={len(payload.get('cells', []))}",
            )
            version = (
                payload.get("metadata", {})
                .get("language_info", {})
                .get("version")
            )
            if isinstance(version, str):
                recorded_versions[name] = version

        unique_versions = sorted(set(recorded_versions.values()))
        self.add(
            "notebook_python_metadata_consistent",
            unique_versions == ["3.12.3"],
            f"versions={recorded_versions}",
        )

    def check_required_project_artifacts(self) -> None:
        groups = {
            "metadata_handoff": REQUIRED_METADATA_HANDOFFS,
            "java_source": REQUIRED_JAVA_SOURCES,
            "selected_figure": SELECTED_FIGURES,
        }
        for group, paths in groups.items():
            missing: list[str] = []
            untracked: list[str] = []
            empty: list[str] = []
            for relative in paths:
                path = self.root / relative
                if not path.is_file():
                    missing.append(relative)
                elif path.stat().st_size == 0:
                    empty.append(relative)
                if self.tracked_files and relative not in self.tracked_files:
                    untracked.append(relative)
            self.add(
                f"required_{group}s_present",
                not missing and not empty,
                f"missing={missing}; empty={empty}; required_count={len(paths)}",
            )
            if self.tracked_files:
                self.add(
                    f"required_{group}s_tracked",
                    not untracked,
                    f"untracked={untracked}",
                )

    def check_readme_links_and_mermaid(self) -> None:
        readme_path = self.root / "README.md"
        if not readme_path.is_file():
            return
        text = readme_path.read_text(encoding="utf-8")

        targets = [*MARKDOWN_LINK_RE.findall(text), *HTML_LINK_RE.findall(text)]
        local_targets: list[str] = []
        broken: list[str] = []
        for target in targets:
            cleaned = self.clean_link_target(target)
            if cleaned is None:
                continue
            local_targets.append(cleaned)
            candidate = (readme_path.parent / PurePosixPath(cleaned)).resolve()
            try:
                candidate.relative_to(self.root)
            except ValueError:
                broken.append(f"outside repository: {target}")
                continue
            if not candidate.exists():
                broken.append(cleaned)

        self.add(
            "readme_local_links_resolve",
            not broken,
            f"local_links={len(local_targets)}; broken={broken}",
        )

        normalized_targets = {PurePosixPath(item).as_posix() for item in local_targets}
        missing_figure_references = [path for path in SELECTED_FIGURES if path not in normalized_targets]
        self.add(
            "readme_embeds_selected_figures",
            not missing_figure_references,
            f"missing_references={missing_figure_references}",
        )

        missing_notebook_links = [name for name in EXPECTED_NOTEBOOKS if name not in normalized_targets]
        self.add(
            "readme_links_all_notebooks",
            not missing_notebook_links,
            f"missing_links={missing_notebook_links}",
        )

        mermaid_blocks = re.findall(r"```mermaid\s*\n(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        mermaid_basic_valid = bool(mermaid_blocks) and all(
            re.search(r"(?m)^\s*(?:flowchart|graph)\s+(?:TB|TD|BT|RL|LR)\b", block)
            for block in mermaid_blocks
        )
        self.add(
            "readme_mermaid_block_basic_validation",
            mermaid_basic_valid,
            f"mermaid_blocks={len(mermaid_blocks)}; GitHub visual rendering remains a manual check",
        )

        display_math_open = text.count("\\[")
        display_math_close = text.count("\\]")
        self.add(
            "readme_uses_github_display_math_delimiters",
            display_math_open == 0 and display_math_close == 0,
            (
                f"found_backslash_bracket_pairs={min(display_math_open, display_math_close)}; "
                "use double-dollar display delimiters for reliable GitHub rendering"
            ),
        )

    @staticmethod
    def clean_link_target(target: str) -> str | None:
        target = target.strip()
        if target.startswith("<") and target.endswith(")"):
            target = target[1:-1]
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        # Remove an optional Markdown title following a path.
        if " \"" in target:
            target = target.split(" \"", 1)[0]
        elif " '" in target:
            target = target.split(" '", 1)[0]
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith("//") or target.startswith("#"):
            return None
        path = unquote(parsed.path).strip()
        if not path:
            return None
        return PurePosixPath(path.replace("\\", "/")).as_posix()

    def check_gitignore(self) -> None:
        path = self.root / ".gitignore"
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        missing = [fragment for fragment in REQUIRED_GITIGNORE_FRAGMENTS if fragment not in text]
        self.add(
            "gitignore_contains_required_exclusions",
            not missing,
            f"missing={missing}",
        )

    def check_tracked_artifacts_and_sizes(self) -> None:
        if not self.tracked_files:
            return

        forbidden: list[str] = []
        generated_work: list[str] = []
        for relative in self.tracked_files:
            path = PurePosixPath(relative)
            if path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
                forbidden.append(relative)
            if path.name in FORBIDDEN_TRACKED_NAMES:
                forbidden.append(relative)
            if any(part in FORBIDDEN_TRACKED_PATH_PARTS for part in path.parts):
                forbidden.append(relative)
            lower = relative.lower()
            if (
                lower.startswith("tools/usgs_nshmp/")
                or "/classes/" in lower
                or lower.endswith("_arguments.txt")
                or "/build/" in lower
            ):
                generated_work.append(relative)

        self.add(
            "no_forbidden_generated_artifacts_tracked",
            not forbidden and not generated_work,
            f"forbidden={sorted(set(forbidden))[:30]}; generated={sorted(set(generated_work))[:30]}",
        )

        large = [
            (path, size)
            for path, size in self.tracked_blob_sizes.items()
            if size > self.max_tracked_bytes
        ]
        large.sort(key=lambda item: item[1], reverse=True)
        detail = [f"{path}={size / 1024 / 1024:.2f} MiB" for path, size in large[:20]]
        self.add(
            "no_tracked_files_above_size_threshold",
            not large,
            f"threshold={self.max_tracked_bytes / 1024 / 1024:.2f} MiB; files={detail}",
        )

    def tracked_text_files(self) -> Iterable[tuple[str, str]]:
        for relative in self.tracked_files:
            path = self.root / relative
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if path.name in {".gitignore", ".gitattributes"}:
                suffix = path.name
            if suffix not in TEXT_SUFFIXES:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > 30 * 1024 * 1024:
                continue
            try:
                yield relative, path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

    def check_machine_specific_paths(self) -> None:
        """Classify machine-specific paths by their effect on reproducibility.

        Absolute home-directory paths are critical when they occur in public
        documentation or executable source. Paths retained only in saved notebook
        outputs or generated validation/provenance metadata are reported as
        warnings because they document the machine on which the validated run was
        produced but do not control a fresh-clone execution.
        """

        documentation_matches: list[str] = []
        source_matches: list[str] = []
        notebook_output_matches: list[str] = []
        provenance_matches: list[str] = []

        documentation_names = {"README.md", "SETUP.md"}
        source_suffixes = {
            ".cfg",
            ".gradle",
            ".ini",
            ".java",
            ".properties",
            ".py",
            ".toml",
            ".yaml",
            ".yml",
        }

        def has_home_path(value: str) -> bool:
            return bool(WINDOWS_HOME_RE.search(value) or POSIX_HOME_RE.search(value))

        def append_line_matches(
            bucket: list[str],
            relative: str,
            value: str,
            *,
            maximum: int = 50,
        ) -> None:
            if len(bucket) >= maximum:
                return
            for line_number, line in enumerate(value.splitlines(), start=1):
                if has_home_path(line):
                    bucket.append(f"{relative}:{line_number}")
                    if len(bucket) >= maximum:
                        return

        for relative in self.tracked_files:
            path = self.root / relative
            if not path.is_file():
                continue

            if path.suffix.lower() == ".ipynb":
                try:
                    notebook = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    continue

                for cell_number, cell in enumerate(notebook.get("cells", []), start=1):
                    source_value = cell.get("source", [])
                    source_text = (
                        "".join(source_value)
                        if isinstance(source_value, list)
                        else str(source_value)
                    )
                    if has_home_path(source_text):
                        source_matches.append(f"{relative}:cell {cell_number}")

                    outputs_text = json.dumps(
                        cell.get("outputs", []),
                        ensure_ascii=False,
                    )
                    if has_home_path(outputs_text):
                        notebook_output_matches.append(
                            f"{relative}:cell {cell_number}"
                        )
                continue

            suffix = path.suffix.lower()
            if path.name in {".gitignore", ".gitattributes"}:
                suffix = path.name
            if suffix not in TEXT_SUFFIXES:
                continue

            try:
                if path.stat().st_size > 30 * 1024 * 1024:
                    continue
                value = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            normalized = relative.replace("\\", "/")
            is_documentation = (
                relative in documentation_names
                or normalized.startswith("docs/")
                or normalized.startswith(".github/")
            )

            if is_documentation:
                append_line_matches(documentation_matches, relative, value)
            elif suffix in source_suffixes:
                append_line_matches(source_matches, relative, value)
            elif has_home_path(value):
                append_line_matches(provenance_matches, relative, value)

        self.add(
            "no_machine_specific_home_paths_in_public_documentation",
            not documentation_matches,
            f"first_matches={documentation_matches}; maximum_reported=50",
        )
        self.add(
            "no_machine_specific_home_paths_in_executable_sources",
            not source_matches,
            f"first_matches={source_matches}; maximum_reported=50",
        )
        self.add(
            "saved_notebook_outputs_with_machine_paths_reviewed",
            not notebook_output_matches,
            (
                f"cells={len(notebook_output_matches)}; "
                f"first_matches={notebook_output_matches[:20]}; "
                "saved outputs are provenance snapshots and do not control execution"
            ),
            severity="warning",
        )
        self.add(
            "generated_provenance_metadata_with_machine_paths_reviewed",
            not provenance_matches,
            (
                f"first_matches={provenance_matches[:20]}; maximum_reported=50; "
                "generated metadata paths are retained as run provenance and do not control execution"
            ),
            severity="warning",
        )

    def check_secrets(self) -> None:
        findings: list[str] = []
        for relative, text in self.tracked_text_files():
            for pattern_name, pattern in SECRET_PATTERNS:
                for match in pattern.finditer(text):
                    captured = match.group(1) if match.lastindex else match.group(0)
                    normalized = captured.strip().lower()
                    if any(
                        marker in normalized
                        for marker in (
                            "<your",
                            "${",
                            "example",
                            "placeholder",
                            "replace_me",
                            "your_",
                        )
                    ):
                        continue
                    line_number = text.count("\n", 0, match.start()) + 1
                    findings.append(f"{pattern_name}:{relative}:{line_number}")
                    if len(findings) >= 50:
                        break
                if len(findings) >= 50:
                    break
            if len(findings) >= 50:
                break
        self.add(
            "no_obvious_secrets_or_credentials_in_tracked_text",
            not findings,
            f"findings={findings}; values are intentionally not printed",
        )

    def check_environment_specification(self) -> None:
        requirements_path = self.root / "requirements.txt"
        setup_path = self.root / "SETUP.md"
        if not requirements_path.is_file():
            return

        requirement_names = self.parse_requirement_names(requirements_path)
        imported_modules, parse_errors, excel_io_detected = self.collect_imports()
        distributions = {
            IMPORT_TO_DISTRIBUTION[module]
            for module in imported_modules
            if module in IMPORT_TO_DISTRIBUTION
        }
        if excel_io_detected:
            distributions.add("openpyxl")

        missing = sorted(distributions - requirement_names)
        self.add(
            "requirements_cover_detected_python_dependencies",
            not missing and not parse_errors,
            (
                f"detected_imports={sorted(imported_modules)}; "
                f"required_distributions={sorted(distributions)}; missing={missing}; "
                f"parse_errors={parse_errors[:20]}"
            ),
        )

        expected_environment_tools = ENVIRONMENT_ONLY_REQUIREMENTS - requirement_names
        self.add(
            "requirements_include_notebook_environment",
            not expected_environment_tools,
            f"missing={sorted(expected_environment_tools)}",
        )

        if setup_path.is_file():
            setup = setup_path.read_text(encoding="utf-8")
            required_setup_phrases = [
                "Python 3.12",
                "JDK 11",
                PINNED_NSHMP_HAZ_TAG,
                PINNED_GRADLE_VERSION,
                "Windows 10 or Windows 11",
                "requirements.txt",
                "validate_repository.py",
            ]
            absent = [phrase for phrase in required_setup_phrases if phrase not in setup]
            self.add(
                "setup_documents_validated_environment",
                not absent,
                f"missing_phrases={absent}",
            )

        current = sys.version_info[:2]
        severity = "critical" if self.profile == "runtime" else "warning"
        self.add(
            "current_python_major_minor_matches_tested_runtime",
            current == TESTED_PYTHON[:2],
            f"current={sys.version.split()[0]}; tested={'.'.join(map(str, TESTED_PYTHON))}",
            severity=severity,
        )

    @staticmethod
    def parse_requirement_names(path: Path) -> set[str]:
        names: set[str] = set()
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith(("-r", "--", "git+", "http://", "https://")):
                continue
            match = re.match(r"([A-Za-z0-9_.-]+)", line)
            if match:
                names.add(match.group(1).lower().replace("_", "-"))
        return names

    def collect_imports(self) -> tuple[set[str], list[str], bool]:
        modules: set[str] = set()
        parse_errors: list[str] = []
        excel_io_detected = False

        sources: list[tuple[str, str]] = []
        for notebook_name in EXPECTED_NOTEBOOKS:
            path = self.root / notebook_name
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            for index, cell in enumerate(payload.get("cells", [])):
                if cell.get("cell_type") != "code":
                    continue
                source = cell.get("source", "")
                source_text = "".join(source) if isinstance(source, list) else str(source)
                sources.append((f"{notebook_name}:cell{index}", source_text))

        for relative in self.tracked_files:
            if not relative.endswith(".py"):
                continue
            path = self.root / relative
            if path.is_file():
                try:
                    sources.append((relative, path.read_text(encoding="utf-8")))
                except (OSError, UnicodeDecodeError):
                    continue

        for label, source in sources:
            if "read_excel(" in source or ".to_excel(" in source:
                excel_io_detected = True
            sanitized = "\n".join(
                line
                for line in source.splitlines()
                if not line.lstrip().startswith(("!", "%", "?"))
            )
            try:
                tree = ast.parse(sanitized)
            except SyntaxError as exc:
                parse_errors.append(f"{label}:{exc.lineno}:{exc.msg}")
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.add(node.module.split(".", 1)[0])

        relevant = {
            module
            for module in modules
            if module in IMPORT_TO_DISTRIBUTION
        }
        return relevant, parse_errors, excel_io_detected

    def check_java_environment(self) -> None:
        setup_path = self.root / "SETUP.md"
        if setup_path.is_file():
            text = setup_path.read_text(encoding="utf-8")
            self.add(
                "java_requirements_documented",
                all(
                    phrase in text
                    for phrase in (
                        "JDK 11",
                        f"nshmp-haz {PINNED_NSHMP_HAZ_TAG}",
                        f"Gradle {PINNED_GRADLE_VERSION}",
                    )
                ),
                "Expected JDK, nshmp-haz tag, and Gradle wrapper version in SETUP.md",
            )

        java_findings: list[str] = []
        majors: list[int | None] = []
        commands_present = True
        for command in ("java", "javac"):
            executable = shutil.which(command)
            if executable is None:
                commands_present = False
                java_findings.append(f"{command}=not found")
                continue
            result = self.run_command([executable, "-version"])
            output = "\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            major = self.parse_java_major(output)
            majors.append(major)
            java_findings.append(f"{command}={major}; path={executable}")

        matches = commands_present and len(majors) == 2 and all(
            major == REQUIRED_JAVA_MAJOR for major in majors
        )
        severity = "critical" if self.profile == "runtime" else "warning"
        self.add(
            "java_and_javac_match_validated_major_version",
            matches,
            "; ".join(java_findings),
            severity=severity,
        )

    @staticmethod
    def parse_java_major(output: str) -> int | None:
        quoted = re.search(r"version\s+[\"']([0-9][^\"']*)[\"']", output, flags=re.IGNORECASE)
        javac = re.search(r"\bjavac\s+([0-9][^\s]*)", output, flags=re.IGNORECASE)
        match = quoted or javac
        if match is None:
            return None
        numbers = re.findall(r"\d+", match.group(1))
        if not numbers:
            return None
        if numbers[0] == "1" and len(numbers) >= 2:
            return int(numbers[1])
        return int(numbers[0])

    def check_git_status(self) -> None:
        git = shutil.which("git")
        if git is None or not (self.root / ".git").exists():
            return
        result = self.run_command([git, "status", "--porcelain=v1", "--untracked-files=all"])
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        passed = result.returncode == 0 and (self.allow_dirty or not lines)
        detail = (
            f"allow_dirty={self.allow_dirty}; changed_paths={lines[:50]}"
            if result.returncode == 0
            else result.stderr.strip()
        )
        self.add("git_worktree_clean", passed, detail)


def find_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists() and (candidate / "README.md").exists():
            return candidate
        if (candidate / EXPECTED_NOTEBOOKS[0]).exists() and (candidate / "README.md").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find the repository root. Run this script from inside the project or pass --root."
    )


def print_results(results: Sequence[CheckResult]) -> None:
    width = max((len(result.check_id) for result in results), default=10)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status:4}] [{result.severity.upper():8}] {result.check_id:<{width}}  {result.detail}")

    critical_failures = [result for result in results if result.severity == "critical" and not result.passed]
    warning_failures = [result for result in results if result.severity == "warning" and not result.passed]
    print()
    print("=" * 88)
    print("REPOSITORY VALIDATION SUMMARY")
    print("=" * 88)
    print(f"Checks:             {len(results):,}")
    print(f"Critical failures:  {len(critical_failures):,}")
    print(f"Warnings:           {len(warning_failures):,}")
    print(f"Final status:       {'PASS' if not critical_failures else 'FAIL'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        help="Repository root. By default, the script searches upward from the current directory.",
    )
    parser.add_argument(
        "--profile",
        choices=("repository", "runtime"),
        default="repository",
        help=(
            "repository checks committed content and documents local tool mismatches as warnings; "
            "runtime requires the validated Python and Java major versions."
        ),
    )
    parser.add_argument(
        "--max-tracked-mb",
        type=float,
        default=50.0,
        help="Maximum permitted tracked Git blob size in MiB. Default: 50.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Do not fail solely because the Git worktree contains changes.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for a machine-readable JSON report. Prefer a path outside the repository.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve() if args.root else find_root(Path.cwd())
    validator = RepositoryValidator(
        root,
        profile=args.profile,
        max_tracked_mb=args.max_tracked_mb,
        allow_dirty=args.allow_dirty,
    )
    results = validator.run()
    print_results(results)

    if args.json_out:
        payload = {
            "project": PROJECT_NAME,
            "root": str(root),
            "profile": args.profile,
            "checks": [asdict(result) for result in results],
            "critical_failures": sum(
                result.severity == "critical" and not result.passed for result in results
            ),
            "warning_failures": sum(
                result.severity == "warning" and not result.passed for result in results
            ),
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nJSON report: {args.json_out}")

    has_critical_failure = any(
        result.severity == "critical" and not result.passed for result in results
    )
    return 1 if has_critical_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
