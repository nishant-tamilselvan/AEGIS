"""Command-line entry point: ``python -m artifact_tools <command>``."""

from __future__ import annotations

import argparse
import json
import sys

from artifact_tools.adr import create_adr, init_adr_dir
from artifact_tools.changelog import add_changelog
from artifact_tools.constants import ARTIFACT_TYPES
from artifact_tools.diagrams import render_dir
from artifact_tools.implementation import (
    add_decision,
    approve_release,
    create_work_package,
    implementation_status,
    init_implementation,
    record_evidence,
    transition_work_package,
    validate_implementation,
)
from artifact_tools.interfaces import init_interfaces_dir
from artifact_tools.readiness import check_readiness
from artifact_tools.scaffold import scaffold
from artifact_tools.validate import has_errors, validate_dir


def _cmd_scaffold(args: argparse.Namespace) -> int:
    try:
        path = scaffold(
            args.type,
            args.out_dir,
            project=args.project,
            title=args.title,
            force=args.force,
        )
    except (FileExistsError, FileNotFoundError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created {path}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    issues = validate_dir(args.directory, strict=args.strict)
    for issue in issues:
        stream = sys.stderr if issue.severity == "error" else sys.stdout
        print(issue.format(), file=stream)

    failed = has_errors(issues, strict=args.strict)
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    if failed:
        print(f"\nvalidation FAILED: {errors} error(s), {warnings} warning(s)", file=sys.stderr)
        return 1
    print(f"\nvalidation OK: {errors} error(s), {warnings} warning(s)")
    return 0


def _cmd_changelog(args: argparse.Namespace) -> int:
    try:
        version = add_changelog(
            args.file, args.summary, level=args.bump, phase=args.phase
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.file} -> v{version}")
    return 0


def _cmd_adr(args: argparse.Namespace) -> int:
    if args.adr_command == "init":
        try:
            index = init_adr_dir(args.dir)
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"initialised ADR index {index}")
        return 0

    try:
        path, adr_id = create_adr(
            args.title,
            args.dir,
            status=args.status,
            component=args.component,
            supersedes=args.supersedes,
            deciders=args.deciders,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created {adr_id} -> {path}")
    if args.supersedes:
        print(f"{args.supersedes} marked superseded by {adr_id}")
    return 0


def _cmd_interfaces(args: argparse.Namespace) -> int:
    if args.interfaces_command == "init":
        path = init_interfaces_dir(args.dir, with_stubs=not args.no_stubs)
        print(f"initialised interfaces contract store {path}")
        return 0
    return 1


def _cmd_diagrams(args: argparse.Namespace) -> int:
    try:
        results = render_dir(
            args.directory,
            engine=args.engine,
            out_subdir=args.out,
            fmt=args.format,
            scale=args.scale,
            theme=args.theme,
            background=args.background,
            puppeteer_config=args.puppeteer_config,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ModuleNotFoundError:
        print(
            "error: the 'diagrams' command requires mermaidx. "
            "Install with: pip install mermaidx",
            file=sys.stderr,
        )
        return 1
    ok = 0
    failed = 0
    for r in results:
        if r.ok:
            ok += 1
            print(f"rendered {r.source_file} #{r.index} -> {r.image}")
        else:
            failed += 1
            print(f"FAILED {r.source_file} #{r.index}: {r.error}", file=sys.stderr)
    print(f"\ndiagrams: {ok} rendered, {failed} failed")
    return 1 if failed else 0


def _csv_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _cmd_implementation(args: argparse.Namespace) -> int:
    try:
        if args.implementation_command == "init":
            path = init_implementation(
                args.app_dir,
                target_workspace=args.target_workspace,
                target_branch=args.target_branch,
                target_baseline=args.target_baseline,
                standards_review=args.standards_review,
                project=args.project,
            )
            print(f"initialised implementation state {path}")
            return 0

        if args.implementation_command == "readiness":
            report = check_readiness(
                args.app_dir,
                target_workspace=args.target_workspace,
                standards_review=args.standards_review,
            )
            for finding in report.findings:
                print(finding.format(), file=sys.stderr if finding.severity == "error" else sys.stdout)
            if report.ready:
                print("\nimplementation readiness: READY")
                return 0
            print(f"\nimplementation readiness: BLOCKED ({len(report.findings)} finding(s))", file=sys.stderr)
            return 1

        if args.implementation_command == "status":
            status = implementation_status(args.app_dir)
            print(json.dumps(status, indent=2, default=str))
            return 0

        if args.implementation_command == "validate":
            findings = validate_implementation(args.app_dir, strict=args.strict)
            for finding in findings:
                print(finding.format(), file=sys.stderr if finding.severity == "error" else sys.stdout)
            if any(item.severity == "error" for item in findings):
                print(f"\nimplementation validation FAILED: {len(findings)} finding(s)", file=sys.stderr)
                return 1
            print(f"\nimplementation validation OK: {len(findings)} finding(s)")
            return 0

        if args.implementation_command == "release-approve":
            path = approve_release(args.app_dir, approver=args.approver, note=args.note)
            print(f"release approved -> {path}")
            return 0

        if args.implementation_command == "work-package":
            if args.work_package_command == "new":
                path, work_package_id = create_work_package(
                    args.app_dir,
                    args.title,
                    scope=args.scope,
                    source_ids=_csv_values(args.source_ids),
                    target_paths=_csv_values(args.target_paths),
                    dependencies=_csv_values(args.dependencies),
                    owner=args.owner,
                    parallel_group=args.parallel_group,
                )
                print(f"created {work_package_id} -> {path}")
                return 0
            if args.work_package_command == "transition":
                path = transition_work_package(
                    args.app_dir,
                    args.id,
                    args.status,
                    actor=args.actor,
                    note=args.note,
                    approved_by=args.approved_by,
                    review_status=args.review_status,
                )
                print(f"transitioned {args.id} -> {args.status} ({path})")
                return 0
            if args.work_package_command == "record-evidence":
                path = record_evidence(
                    args.app_dir,
                    args.id,
                    args.command,
                    args.outcome,
                    args.details,
                )
                print(f"recorded evidence for {args.id} -> {path}")
                return 0

        if args.implementation_command == "decision":
            decision_id = add_decision(
                args.app_dir,
                question=args.question,
                decision=args.decision,
                rationale=args.rationale,
                work_package=args.work_package,
                decision_type=args.type,
                status=args.status,
                sources=_csv_values(args.sources),
                affected_paths=_csv_values(args.affected_paths),
                approver=args.approver,
                adr=args.adr,
                supersedes=args.supersedes,
            )
            print(f"recorded {decision_id}")
            return 0
    except (FileExistsError, FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="artifact_tools",
        description="Scaffold, validate and maintain AEGIS artifacts across all three SDLC phases.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sc = sub.add_parser("scaffold", help="Create an artifact from its template.")
    sc.add_argument("type", help=f"Artifact type (or alias). One of: {', '.join(ARTIFACT_TYPES)}")
    sc.add_argument("out_dir", help="Application artifact directory, e.g. docs/artifacts/<app>")
    sc.add_argument("--project", default="Untitled Project", help="Project name for the header.")
    sc.add_argument("--title", default=None, help="Override the document title.")
    sc.add_argument("--force", action="store_true", help="Overwrite if the file exists.")
    sc.set_defaults(func=_cmd_scaffold)

    va = sub.add_parser(
        "validate",
        help="Validate one application's artifacts, or every app under a parent directory.",
    )
    va.add_argument(
        "directory",
        help="An app directory (docs/artifacts/<app>) or a parent holding many apps (docs/artifacts).",
    )
    va.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    va.set_defaults(func=_cmd_validate)

    cl = sub.add_parser("changelog", help="Append a changelog entry and bump version.")
    cl.add_argument("file", help="Path to the artifact markdown file.")
    cl.add_argument("summary", help="Short description of the change.")
    cl.add_argument("--bump", choices=["minor", "major"], default="minor", help="Version bump level.")
    cl.add_argument("--phase", type=int, default=None, help="Update the phase number.")
    cl.set_defaults(func=_cmd_changelog)

    adr = sub.add_parser("adr", help="Create and index Architecture Decision Records.")
    adr_sub = adr.add_subparsers(dest="adr_command", required=True)

    adr_init = adr_sub.add_parser("init", help="Create the ADR folder, index and seed template.")
    adr_init.add_argument("dir", help="ADR directory, e.g. docs/artifacts/<app>/architecture-decisions")
    adr_init.set_defaults(func=_cmd_adr)

    adr_new = adr_sub.add_parser("new", help="Create the next ADR and append it to the index.")
    adr_new.add_argument("title", help="Decision title, e.g. 'Event-driven topology'.")
    adr_new.add_argument("dir", help="ADR directory, e.g. docs/artifacts/<app>/architecture-decisions")
    adr_new.add_argument(
        "--status",
        choices=["proposed", "accepted", "rejected", "deprecated", "superseded"],
        default="proposed",
        help="ADR status.",
    )
    adr_new.add_argument("--component", default="TBD", help="Component/domain tag.")
    adr_new.add_argument("--supersedes", default=None, help="ADR id this decision supersedes, e.g. ADR-0003.")
    adr_new.add_argument("--deciders", default="architecture-orchestrator", help="Who made the decision.")
    adr_new.set_defaults(func=_cmd_adr)

    itf = sub.add_parser("interfaces", help="Manage the native-format interface contract store.")
    itf_sub = itf.add_subparsers(dest="interfaces_command", required=True)

    itf_init = itf_sub.add_parser("init", help="Create interfaces/ (synchronous, asynchronous, graphql).")
    itf_init.add_argument("dir", help="Application artifact directory holding the router index, e.g. docs/artifacts/<app>")
    itf_init.add_argument("--no-stubs", action="store_true", help="Create empty subfolders without example schema stubs.")
    itf_init.set_defaults(func=_cmd_interfaces)

    dg = sub.add_parser("diagrams", help="Render embedded Mermaid diagrams in an app's .md files to images.")
    dg.add_argument("directory", help="Application artifact directory, e.g. docs/artifacts/<app>")
    dg.add_argument("--out", default="assets/diagrams", help="Output subdirectory relative to the app directory.")
    dg.add_argument("--format", choices=["png", "svg"], default="png", help="Image format.")
    dg.add_argument("--scale", type=float, default=2.0, help="Raster scale factor for PNG.")
    dg.add_argument("--theme", choices=["default", "neutral", "dark", "forest"], default="default", help="Mermaid theme.")
    dg.add_argument("--background", default="white", help="Background colour (e.g. white, transparent, #f5f5f5).")
    dg.add_argument("--engine", choices=["mmdc", "mermaidx"], default="mmdc", help="Renderer: mmdc (official mermaid-cli, best quality) or mermaidx (pure-Python).")
    dg.add_argument("--puppeteer-config", default=None, help="Path to a Puppeteer config JSON for the mmdc engine.")
    dg.set_defaults(func=_cmd_diagrams)

    imp = sub.add_parser("implementation", help="Manage phase-3 readiness, decisions, work packages and evidence.")
    imp_sub = imp.add_subparsers(dest="implementation_command", required=True)

    imp_init = imp_sub.add_parser("init", help="Initialize a per-application implementation pointer and ledgers.")
    imp_init.add_argument("app_dir", help="Application artifact directory, e.g. docs/artifacts/<app>.")
    imp_init.add_argument("target_workspace", help="Repository in which bounded work packages will write code.")
    imp_init.add_argument("--project", default=None, help="Human-readable project name.")
    imp_init.add_argument("--target-branch", default="", help="Target branch recorded in the pointer.")
    imp_init.add_argument("--target-baseline", default="", help="Commit or other immutable target baseline.")
    imp_init.add_argument(
        "--standards-review",
        choices=["verified", "manual-review-required"],
        default="manual-review-required",
        help="Whether current Approved enterprise implementation guidance was verified.",
    )
    imp_init.set_defaults(func=_cmd_implementation)

    imp_ready = imp_sub.add_parser("readiness", help="Read-only gate before planning or code generation.")
    imp_ready.add_argument("app_dir")
    imp_ready.add_argument("target_workspace")
    imp_ready.add_argument(
        "--standards-review",
        choices=["verified", "manual-review-required"],
        default=None,
    )
    imp_ready.set_defaults(func=_cmd_implementation)

    imp_status = imp_sub.add_parser("status", help="Print canonical implementation pointer state as JSON.")
    imp_status.add_argument("app_dir")
    imp_status.set_defaults(func=_cmd_implementation)

    imp_validate = imp_sub.add_parser("validate", help="Validate phase-3 implementation state.")
    imp_validate.add_argument("app_dir")
    imp_validate.add_argument("--strict", action="store_true", help="Require verified Enterprise Standards review.")
    imp_validate.set_defaults(func=_cmd_implementation)

    imp_release = imp_sub.add_parser("release-approve", help="Record the explicit final human release gate.")
    imp_release.add_argument("app_dir")
    imp_release.add_argument("--approver", required=True)
    imp_release.add_argument("--note", default="")
    imp_release.set_defaults(func=_cmd_implementation)

    wp = imp_sub.add_parser("work-package", help="Create, transition or record evidence for a bounded package.")
    wp_sub = wp.add_subparsers(dest="work_package_command", required=True)
    wp_new = wp_sub.add_parser("new", help="Create the next work package.")
    wp_new.add_argument("app_dir")
    wp_new.add_argument("title")
    wp_new.add_argument("--scope", required=True)
    wp_new.add_argument("--source-ids", required=True, help="Comma-separated artifact, ADR or Enterprise Standards ids.")
    wp_new.add_argument("--target-paths", required=True, help="Comma-separated repository-relative paths.")
    wp_new.add_argument("--dependencies", default="", help="Comma-separated WP-NNNN ids.")
    wp_new.add_argument("--owner", default="implementation-orchestrator")
    wp_new.add_argument("--parallel-group", default=None)
    wp_new.set_defaults(func=_cmd_implementation)

    wp_transition = wp_sub.add_parser("transition", help="Apply an allowed work-package state transition.")
    wp_transition.add_argument("app_dir")
    wp_transition.add_argument("id")
    wp_transition.add_argument("status")
    wp_transition.add_argument("--actor", required=True)
    wp_transition.add_argument("--note", default="")
    wp_transition.add_argument("--approved-by", default=None)
    wp_transition.add_argument("--review-status", choices=["pending", "pass", "needs-changes"], default=None)
    wp_transition.set_defaults(func=_cmd_implementation)

    wp_evidence = wp_sub.add_parser("record-evidence", help="Append an actual command or check result.")
    wp_evidence.add_argument("app_dir")
    wp_evidence.add_argument("id")
    wp_evidence.add_argument("command")
    wp_evidence.add_argument("outcome", choices=["pass", "fail"])
    wp_evidence.add_argument("--details", default="")
    wp_evidence.set_defaults(func=_cmd_implementation)

    decision = imp_sub.add_parser("decision", help="Append an implementation decision or supersede one.")
    decision.add_argument("app_dir")
    decision.add_argument("question")
    decision.add_argument("decision")
    decision.add_argument("rationale")
    decision.add_argument("--work-package", default="—")
    decision.add_argument("--type", choices=["tactical", "material"], default="tactical")
    decision.add_argument("--status", choices=["pending", "accepted", "rejected", "superseded"], default="accepted")
    decision.add_argument("--sources", default="")
    decision.add_argument("--affected-paths", default="")
    decision.add_argument("--approver", default="")
    decision.add_argument("--adr", default="—")
    decision.add_argument("--supersedes", default=None)
    decision.set_defaults(func=_cmd_implementation)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
