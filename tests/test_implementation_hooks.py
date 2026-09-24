"""Tests for deterministic implementation-agent PreToolUse guardrails."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from artifact_tools.constants import ARTIFACT_TYPES
from artifact_tools.guard import evaluate_guard
from artifact_tools.implementation import (
    create_work_package,
    init_implementation,
    transition_work_package,
)
from artifact_tools.scaffold import scaffold

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_TEMPLATES = REPO_ROOT / "aegis/skills/artifact-management/assets/templates"
IMPLEMENTATION_TEMPLATES = REPO_ROOT / "aegis/skills/implementation-management/assets/templates"


def _guard_fixture(root: Path) -> tuple[Path, Path, Path]:
    app = root / "docs/artifacts/sample"
    for type_key in ARTIFACT_TYPES:
        scaffold(type_key, app, project="Sample", templates_dir=ARTIFACT_TEMPLATES)
    target = root / "target"
    target.mkdir()
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    init_implementation(
        app,
        target_workspace=target,
        standards_review="verified",
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    _, work_package_id = create_work_package(
        app,
        "Service slice",
        scope="Implement service files.",
        source_ids=["FR-001"],
        target_paths=["apps/sample/src"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    transition_work_package(
        app,
        work_package_id,
        "approved",
        actor="orchestrator",
        approved_by="delivery-lead",
    )
    transition_work_package(app, work_package_id, "in-progress", actor="service-implementer")
    return app, target, root


def _payload(agent: str, tool: str, **tool_args: object) -> dict:
    return {"agentName": agent, "toolName": tool, "toolArgs": tool_args}


def test_non_implementation_agent_is_unaffected(tmp_path: Path):
    decision = evaluate_guard(
        _payload("GitHub Copilot", "apply_patch", filePath=str(tmp_path / "anything.py")),
        repo_root=tmp_path,
    )
    assert decision.permission == "allow"


def test_code_agent_may_write_only_declared_target_paths(tmp_path: Path):
    _, target, root = _guard_fixture(tmp_path)

    allowed = evaluate_guard(
        _payload(
            "Service Implementer",
            "create_file",
            filePath=str(target / "apps/sample/src/index.ts"),
        ),
        repo_root=root,
    )
    denied = evaluate_guard(
        _payload(
            "Service Implementer",
            "create_file",
            filePath=str(target / "apps/other/src/index.ts"),
        ),
        repo_root=root,
    )

    assert allowed.permission == "allow"
    assert "WP-0001" in allowed.reason
    assert denied.permission == "deny"
    assert "outside" in denied.reason


def test_code_agent_cannot_write_artifacts(tmp_path: Path):
    app, _, root = _guard_fixture(tmp_path)
    decision = evaluate_guard(
        _payload(
            "UI Implementer",
            "apply_patch",
            input=f"*** Update File: {app / 'implementation/implementation.md'}",
        ),
        repo_root=root,
    )
    assert decision.permission == "deny"
    assert "Artifact Manager" in decision.reason


def test_code_agent_without_active_package_is_denied(tmp_path: Path):
    app = tmp_path / "docs/artifacts/sample"
    for type_key in ARTIFACT_TYPES:
        scaffold(type_key, app, templates_dir=ARTIFACT_TEMPLATES)
    target = tmp_path / "target"
    target.mkdir()
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    init_implementation(
        app,
        target_workspace=target,
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )

    decision = evaluate_guard(
        _payload("Platform Implementer", "create_file", filePath=str(target / "deploy.yaml")),
        repo_root=tmp_path,
    )
    assert decision.permission == "deny"
    assert "active work package" in decision.reason


def test_destructive_and_deployment_commands_require_human_gate(tmp_path: Path):
    _, target, root = _guard_fixture(tmp_path)
    destructive = evaluate_guard(
        _payload(
            "Service Implementer",
            "run_in_terminal",
            command=f"Set-Location '{target}'; git reset --hard HEAD~1",
            path=str(target / "apps/sample/src"),
        ),
        repo_root=root,
    )
    deployment = evaluate_guard(
        _payload(
            "Platform Implementer",
            "run_in_terminal",
            command="oc apply -f deploy.yaml",
            path=str(target / "apps/sample/src"),
        ),
        repo_root=root,
    )
    assert destructive.permission == "ask"
    assert deployment.permission == "ask"


def test_shell_file_edit_is_denied(tmp_path: Path):
    _, target, root = _guard_fixture(tmp_path)
    decision = evaluate_guard(
        _payload(
            "Service Implementer",
            "run_in_terminal",
            command="'generated' | Set-Content apps/sample/src/generated.ts",
            path=str(target / "apps/sample/src"),
        ),
        repo_root=root,
    )
    assert decision.permission == "deny"
    assert "file-edit tools" in decision.reason


def test_hook_wrapper_emits_vscode_permission_contract():
    payload = json.dumps({"agentName": "GitHub Copilot", "toolName": "read_file", "toolArgs": {}})
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/implementation_guard.py")],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )
    output = json.loads(result.stdout)
    assert result.returncode == 0
    assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


# --------------------------------------------------------------------------- Claude Code


def _claude_payload(agent: str | None, tool: str, **tool_input: object) -> dict:
    payload = {
        "session_id": "test-session",
        "hook_event_name": "PreToolUse",
        "cwd": str(REPO_ROOT),
        "tool_name": tool,
        "tool_input": tool_input,
    }
    if agent is not None:
        payload["agent_type"] = agent  # present only when a subagent makes the call
    return payload


def test_claude_subagent_write_is_bounded_by_work_package(tmp_path: Path):
    _, target, root = _guard_fixture(tmp_path)
    allowed = evaluate_guard(
        _claude_payload("service-implementer", "Write", file_path=str(target / "apps/sample/src/app.py"), content="x"),
        repo_root=root,
    )
    denied = evaluate_guard(
        _claude_payload("service-implementer", "Edit", file_path=str(target / "apps/other/app.py"), old_string="a", new_string="b"),
        repo_root=root,
    )
    notebook = evaluate_guard(
        _claude_payload("test-quality-engineer", "NotebookEdit", notebook_path=str(target / "notebooks/x.ipynb"), new_source=""),
        repo_root=root,
    )
    assert allowed.permission == "allow"
    assert denied.permission == "deny"
    assert notebook.permission == "deny"


def test_claude_subagent_cannot_write_artifacts(tmp_path: Path):
    app, _, root = _guard_fixture(tmp_path)
    decision = evaluate_guard(
        _claude_payload("ui-implementer", "MultiEdit", file_path=str(app / "product-requirements.md"), edits=[]),
        repo_root=root,
    )
    assert decision.permission == "deny"


def test_claude_bash_gates(tmp_path: Path):
    _, _, root = _guard_fixture(tmp_path)
    destructive = evaluate_guard(_claude_payload("platform-implementer", "Bash", command="rm -rf build"), repo_root=root)
    deploy = evaluate_guard(_claude_payload("platform-implementer", "Bash", command="helm upgrade app ./chart"), repo_root=root)
    redirect = evaluate_guard(_claude_payload("service-implementer", "Bash", command="echo hi > apps/sample/src/x.txt"), repo_root=root)
    assert destructive.permission == "ask"
    assert deploy.permission == "ask"
    assert redirect.permission == "deny"


def test_only_implementers_may_write_to_the_target_repository(tmp_path: Path):
    app, target, root = _guard_fixture(tmp_path)
    inside_package = str(target / "apps/sample/src/app.py")
    main_session = evaluate_guard(_claude_payload(None, "Write", file_path=inside_package), repo_root=root)
    orchestrator = evaluate_guard(
        _payload("Implementation Orchestrator", "create_file", filePath=inside_package), repo_root=root
    )
    reviewer = evaluate_guard(_claude_payload("implementation-reviewer", "Edit", file_path=inside_package), repo_root=root)
    for decision in (main_session, orchestrator, reviewer):
        assert decision.permission == "deny"
        assert "delegate" in decision.reason


def test_other_agents_keep_reads_commands_and_non_target_writes(tmp_path: Path):
    app, target, root = _guard_fixture(tmp_path)
    decisions = [
        evaluate_guard(_claude_payload(None, "Read", file_path=str(target / "apps/sample/src/app.py")), repo_root=root),
        evaluate_guard(_claude_payload("critic-reviewer", "Bash", command="python -m pytest"), repo_root=root),
        evaluate_guard(_claude_payload("artifact-manager", "Write", file_path=str(app / "product-requirements.md")), repo_root=root),
        evaluate_guard(_claude_payload(None, "Write", file_path=str(root / "notes.md")), repo_root=root),
    ]
    assert [d.permission for d in decisions] == ["allow"] * 4


def test_hook_wrapper_accepts_claude_payload():
    payload = json.dumps(_claude_payload("critic-reviewer", "Read", file_path=str(REPO_ROOT / "README.md")))
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/implementation_guard.py")],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def _load_validate_hook():
    import importlib.util

    spec = importlib.util.spec_from_file_location("validate_hook", REPO_ROOT / "scripts/validate_hook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_hook_output_per_platform():
    hook = _load_validate_hook()
    assert hook.hook_output("fix FR-001", "copilot") == {"systemMessage": "fix FR-001"}
    claude = hook.hook_output("fix FR-001", "claude")
    assert claude["hookSpecificOutput"] == {"hookEventName": "PostToolUse", "additionalContext": "fix FR-001"}
    assert "fix FR-001" not in claude["systemMessage"]


# --------------------------------------------------------------------------- fail closed


def _load_guard_wrapper():
    import importlib.util

    spec = importlib.util.spec_from_file_location("implementation_guard_wrapper", REPO_ROOT / "scripts/implementation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_wrapper(monkeypatch, capsys, stdin_text: str) -> tuple[int, dict, str]:
    import io

    wrapper = _load_guard_wrapper()
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    code = wrapper.main()
    captured = capsys.readouterr()
    return code, json.loads(captured.out)["hookSpecificOutput"], captured.err


def test_wrapper_asks_when_payload_is_unreadable(monkeypatch, capsys):
    for text in ("not json", "[1, 2]", ""):
        code, output, _ = _run_wrapper(monkeypatch, capsys, text)
        assert output["permissionDecision"] == "ask", text
        assert code == 0


def test_wrapper_denies_when_the_guard_raises(monkeypatch, capsys):
    def broken(payload, *, repo_root):
        raise RuntimeError("corrupt implementation state")

    monkeypatch.setattr("artifact_tools.guard.evaluate_guard", broken)
    code, output, err = _run_wrapper(monkeypatch, capsys, json.dumps(_claude_payload("service-implementer", "Write", file_path="x")))
    assert output["permissionDecision"] == "deny"
    assert "corrupt implementation state" in output["permissionDecisionReason"]
    assert code == 2
    assert "denying to stay safe" in err


def test_wrapper_asks_others_when_the_guard_raises(monkeypatch, capsys):
    """A broken guard must not lock a person out of their own session."""

    def broken(payload, *, repo_root):
        raise NameError("name 'helper' is not defined")

    monkeypatch.setattr("artifact_tools.guard.evaluate_guard", broken)
    for agent in (None, "critic-reviewer"):
        code, output, _ = _run_wrapper(monkeypatch, capsys, json.dumps(_claude_payload(agent, "Edit", file_path="x")))
        assert output["permissionDecision"] == "ask", agent
        assert code == 0


def test_wrapper_when_the_guard_cannot_be_imported(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "artifact_tools.guard", None)
    code, output, _ = _run_wrapper(monkeypatch, capsys, json.dumps(_claude_payload("service-implementer", "Write", file_path="x")))
    assert output["permissionDecision"] == "deny"
    assert "unavailable" in output["permissionDecisionReason"]
    assert code == 2
    code, output, _ = _run_wrapper(monkeypatch, capsys, json.dumps(_claude_payload(None, "Write", file_path="x")))
    assert output["permissionDecision"] == "ask"
    assert code == 0


def test_wrapper_agent_list_matches_guard():
    from artifact_tools.guard import IMPLEMENTATION_CODE_AGENTS

    wrapper = _load_guard_wrapper()
    assert wrapper.IMPLEMENTATION_CODE_AGENTS == IMPLEMENTATION_CODE_AGENTS
    assert wrapper.is_code_agent({"agentName": "Service Implementer"})
    assert wrapper.is_code_agent({"agent_type": "ui-implementer"})
    assert not wrapper.is_code_agent({"agent_type": "critic-reviewer"})
    assert not wrapper.is_code_agent({})


def test_wrapper_reports_deny_reason_on_stderr(tmp_path: Path, monkeypatch, capsys):
    app, _, root = _guard_fixture(tmp_path)
    wrapper = _load_guard_wrapper()
    monkeypatch.setattr(wrapper, "REPO_ROOT", root)
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_claude_payload("ui-implementer", "Write", file_path=str(app / "x.md")))))
    assert wrapper.main() == 2
    captured = capsys.readouterr()
    assert "docs/artifacts" in captured.err


# --------------------------------------------------------------------------- same-repository target


def _same_repo_fixture(root: Path) -> Path:
    """The repository that holds docs/artifacts is also the implementation target."""
    (root / "README.md").write_text("# Repo\n", encoding="utf-8")
    app = root / "docs/artifacts/sample"
    for type_key in ARTIFACT_TYPES:
        scaffold(type_key, app, project="Sample", templates_dir=ARTIFACT_TEMPLATES)
    init_implementation(app, target_workspace=root, standards_review="verified", templates_dir=IMPLEMENTATION_TEMPLATES)
    _, work_package_id = create_work_package(
        app, "Slice", scope="Same-repo slice.", source_ids=["FR-001"],
        target_paths=["apps/sample/src"], templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    transition_work_package(app, work_package_id, "approved", actor="orchestrator", approved_by="lead")
    transition_work_package(app, work_package_id, "in-progress", actor="service-implementer")
    return app


def test_same_repo_target_keeps_artifacts_writable_for_other_agents(tmp_path: Path):
    root = tmp_path.resolve()
    app = _same_repo_fixture(root)
    manager = evaluate_guard(_claude_payload("artifact-manager", "Write", file_path=str(app / "product-requirements.md")), repo_root=root)
    main_session = evaluate_guard(_claude_payload(None, "Edit", file_path=str(app / "implementation/decision.md")), repo_root=root)
    assert manager.permission == "allow"
    assert main_session.permission == "allow"


def test_same_repo_target_still_bounds_code_and_implementers(tmp_path: Path):
    root = tmp_path.resolve()
    app = _same_repo_fixture(root)
    main_code = evaluate_guard(_claude_payload(None, "Write", file_path=str(root / "apps/sample/src/app.py")), repo_root=root)
    implementer_code = evaluate_guard(_claude_payload("service-implementer", "Write", file_path=str(root / "apps/sample/src/app.py")), repo_root=root)
    implementer_outside = evaluate_guard(_claude_payload("service-implementer", "Write", file_path=str(root / "README.md")), repo_root=root)
    implementer_artifact = evaluate_guard(_claude_payload("service-implementer", "Write", file_path=str(app / "product-requirements.md")), repo_root=root)
    assert main_code.permission == "deny"
    assert implementer_code.permission == "allow"
    assert implementer_outside.permission == "deny"
    assert implementer_artifact.permission == "deny"


# --------------------------------------------------------------------------- --repo-root (plugin layout)


def _run_script(script: str, payload: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *args],
        input=json.dumps(payload), text=True, capture_output=True, check=False, cwd=REPO_ROOT,
    )


def test_guard_script_guards_the_repository_given_by_repo_root(tmp_path: Path):
    """A plugin runs the guard from its own folder against the user's repository."""
    root = tmp_path.resolve()
    _same_repo_fixture(root)
    outside = _claude_payload("service-implementer", "Write", file_path=str(root / "README.md"))
    inside = _claude_payload("service-implementer", "Write", file_path=str(root / "apps/sample/src/app.py"))
    for args in (("--repo-root", str(root)), (f"--repo-root={root}",)):
        denied = _run_script("implementation_guard.py", outside, *args)
        allowed = _run_script("implementation_guard.py", inside, *args)
        assert json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", args
        assert denied.returncode == 2
        assert json.loads(allowed.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow", args


def test_guard_script_fails_closed_on_an_unusable_repo_root(tmp_path: Path):
    """An empty --repo-root (for example an unset variable) must not guard the wrong folder."""
    for value in ("", str(tmp_path / "missing")):
        implementer = _run_script("implementation_guard.py", _claude_payload("service-implementer", "Write", file_path="x"), "--repo-root", value)
        person = _run_script("implementation_guard.py", _claude_payload(None, "Write", file_path="x"), "--repo-root", value)
        assert json.loads(implementer.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", value
        assert json.loads(person.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask", value
    dangling = _run_script("implementation_guard.py", _claude_payload("service-implementer", "Write", file_path="x"), "--repo-root")
    assert json.loads(dangling.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_validate_hook_validates_the_repository_given_by_repo_root(tmp_path: Path):
    empty = _run_script("validate_hook.py", {}, "--platform", "claude", "--repo-root", str(tmp_path))
    assert empty.returncode == 0
    assert empty.stdout == ""

    app = tmp_path / "docs/artifacts/sample"
    scaffold("functional-requirements", app, project="Sample", templates_dir=ARTIFACT_TEMPLATES)
    broken = app / "functional-requirements.md"
    broken.write_text(broken.read_text(encoding="utf-8").replace("| FR-001 | The system shall", "| FR-001 | Refers to FR-999; the system shall"), encoding="utf-8")
    result = _run_script("validate_hook.py", {}, "--platform", "claude", "--repo-root", str(tmp_path))
    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "FR-999" in context
