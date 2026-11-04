"""Verify pinned Spec Kit assets; optionally exercise Python helpers offline."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = {
    "analyze",
    "checklist",
    "clarify",
    "constitution",
    "converge",
    "implement",
    "plan",
    "specify",
    "tasks",
}


def verify(root=ROOT):
    source = json.loads((root / ".specify/source.json").read_text(encoding="utf-8"))
    for item in source["files"]:
        path = root / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Spec Kit asset differs: {item['path']}")
    state = json.loads((root / ".specify/integration.json").read_text(encoding="utf-8"))
    if state["default_integration"] != "copilot":
        raise ValueError("This setup expects Copilot as the default integration.")
    for key, folder in (("copilot", ".github/skills"), ("codex", ".agents/skills")):
        settings = state["integration_settings"][key]
        if settings["script"] != "py" or settings["parsed_options"]["events"] != "false":
            raise ValueError(f"Unexpected script/events settings for {key}")
        manifest = json.loads(
            (root / f".specify/integrations/{key}.manifest.json").read_text(encoding="utf-8")
        )
        if manifest["version"] != source["version"]:
            raise ValueError(f"Mismatched Spec Kit version for {key}")
        for command in COMMANDS:
            name = f"{folder}/speckit-{command}/SKILL.md"
            path = root / name
            if manifest["files"][name] != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError(f"Integration manifest differs: {name}")
            if "__SPECKIT_COMMAND_" in path.read_text(encoding="utf-8"):
                raise ValueError(f"Unresolved generated command token: {name}")
    constitution = (root / ".specify/memory/constitution.md").read_text(encoding="utf-8")
    if "[PRINCIPLE_" in constitution or not re.search(
        r"\*\*Version\*\*: \d+\.\d+\.\d+", constitution
    ):
        raise ValueError("Project constitution has not been filled in or versioned as expected.")
    print(
        f"Verified {len(source['files'])} Spec Kit assets at {source['tag']} / {source['commit']}"
    )
    print("Verified 9 Copilot + 9 Codex skills, shared Python helpers, native events disabled.")


def smoke(root=ROOT):
    with TemporaryDirectory(prefix="gentleman-spec-kit-") as temporary:
        project = Path(temporary) / "Gentleman thử nghiệm có khoảng trắng"
        project.mkdir()
        shutil.copytree(
            root / ".specify",
            project / ".specify",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "feature.json"),
        )
        env = os.environ.copy()
        for name in ("SPECIFY_FEATURE", "SPECIFY_FEATURE_DIRECTORY", "SPECIFY_FEATURE_NO_PERSIST"):
            env.pop(name, None)
        env["SPECIFY_INIT_DIR"] = str(project)
        env["PYTHONIOENCODING"] = "utf-8"

        def run(script, *args):
            result = subprocess.run(
                [sys.executable, str(project / ".specify/scripts/python" / script), *args],
                cwd=project,
                env=env,
                check=True,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )
            return json.loads(result.stdout)

        template = run("resolve_template.py", "spec-template", "--json")
        if len(template["TEMPLATE_CONTENT"]) < 100:
            raise ValueError("Resolved spec template was empty or incomplete.")
        feature = run(
            "create_new_feature.py",
            "--json",
            "--short-name",
            "smoke-test",
            "--number",
            "1",
            "Exercise isolated Spec Kit workflow",
        )
        spec = Path(feature["SPEC_FILE"])
        if not spec.is_relative_to(project) or not spec.is_file():
            raise ValueError("Feature was not created within the isolated project.")
        plan = run("setup_plan.py", "--json")
        if not Path(plan["IMPL_PLAN"]).is_file():
            raise ValueError("Plan helper did not create plan.md.")
        tasks = run("setup_tasks.py", "--json")
        task_file = Path(tasks["FEATURE_DIR"]) / "tasks.md"
        task_file.write_text(tasks["TASKS_TEMPLATE_CONTENT"], encoding="utf-8")
        prerequisites = run(
            "check_prerequisites.py",
            "--json",
            "--require-spec",
            "--require-tasks",
            "--include-tasks",
        )
        if Path(prerequisites["FEATURE_DIR"]) != spec.parent:
            raise ValueError("Helpers resolved different feature directories.")
        if "tasks.md" not in prerequisites["AVAILABLE_DOCS"]:
            raise ValueError("Prerequisites did not find the task list.")
    print(
        "PASS: isolated create → resolve → plan → tasks → prerequisites; Unicode/spaced path; no AI/network calls."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke", action="store_true", help="Exercise helpers in a temporary project"
    )
    args = parser.parse_args()
    try:
        verify()
        if args.smoke:
            smoke()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Spec Kit verification failed: {error}") from error


if __name__ == "__main__":
    main()
