"""Dependency-free structural validation for the AI Toolbox marketplace."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_UPSTREAMS = {
    "microsoft/playwright",
    "microsoft/playwright-mcp",
    "browser-use/browser-use",
    "OpenBB-finance/OpenBB",
    "ranaroussi/yfinance",
    "goldmansachs/gs-quant",
    "TauricResearch/TradingAgents",
    "AI4Finance-Foundation/FinGPT",
    "n8n-io/n8n",
    "activepieces/activepieces",
    "modelcontextprotocol/servers",
    "punkpeye/awesome-mcp-servers",
}
ALLOWED_CLASSIFICATIONS = {
    "runtime-dependency",
    "mcp-integration",
    "optional-dependency",
    "reference-only",
    "external-service",
}
EXPECTED_UPSTREAM_PLUGINS = {
    "microsoft/playwright": {"research-tools"},
    "microsoft/playwright-mcp": {"research-tools"},
    "browser-use/browser-use": {"research-tools"},
    "OpenBB-finance/OpenBB": {"finance-tools"},
    "ranaroussi/yfinance": {"finance-tools"},
    "goldmansachs/gs-quant": {"quant-tools"},
    "TauricResearch/TradingAgents": {"finance-tools"},
    "AI4Finance-Foundation/FinGPT": {"finance-tools"},
    "n8n-io/n8n": {"automation-tools"},
    "activepieces/activepieces": {"automation-tools"},
    "modelcontextprotocol/servers": {"research-tools", "automation-tools"},
    "punkpeye/awesome-mcp-servers": {"research-tools", "automation-tools"},
}


def validate() -> list[str]:
    errors: list[str] = []
    marketplace = load_json(MARKETPLACE, errors)
    if not marketplace:
        return errors
    if marketplace.get("name") != "ai-toolbox":
        errors.append("Marketplace name must be 'ai-toolbox'.")

    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or not entries:
        errors.append("Marketplace must contain plugin entries.")
        return errors

    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Each marketplace plugin entry must be an object.")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            errors.append("Marketplace plugin entry is missing a name.")
            continue
        if name in seen:
            errors.append(f"Duplicate marketplace plugin: {name}")
        seen.add(name)
        expected_path = f"./plugins/{name}"
        if entry.get("source") != {"source": "local", "path": expected_path}:
            errors.append(f"{name}: source must be local at {expected_path}.")
        policy = entry.get("policy", {})
        if policy.get("installation") not in {
            "AVAILABLE",
            "INSTALLED_BY_DEFAULT",
            "NOT_AVAILABLE",
        }:
            errors.append(f"{name}: invalid installation policy.")
        if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
            errors.append(f"{name}: invalid authentication policy.")
        validate_plugin(ROOT / "plugins" / name, name, errors)

    disk_plugins = {path.name for path in (ROOT / "plugins").iterdir() if path.is_dir()}
    if seen != disk_plugins:
        errors.append(
            f"Marketplace/plugin directory mismatch: catalog={sorted(seen)}, disk={sorted(disk_plugins)}"
        )

    lock = load_json(ROOT / "upstream-lock.json", errors)
    if lock.get("schemaVersion") != 2:
        errors.append("upstream-lock.json schemaVersion must be 2.")
    upstreams = lock.get("upstreams", [])
    if not isinstance(upstreams, list):
        errors.append("upstream-lock.json requires an 'upstreams' array.")
        upstreams = []

    repositories = []
    for item in upstreams:
        if not isinstance(item, dict):
            errors.append("Each upstream entry must be an object.")
            continue
        repository = item.get("repository")
        if not isinstance(repository, str) or not repository:
            errors.append("Each upstream entry requires a repository name.")
            continue
        repositories.append(repository)
        if not isinstance(item.get("ref"), str) or not item["ref"].strip():
            errors.append(f"{repository}: requires a non-empty ref.")
        if not isinstance(item.get("commit"), str) or not GIT_SHA.fullmatch(
            item["commit"]
        ):
            errors.append(f"{repository}: commit must be an exact 40-character SHA.")
        classification = item.get("classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(
                f"{repository}: classification must be one of "
                f"{', '.join(sorted(ALLOWED_CLASSIFICATIONS))}."
            )
        groups = {
            group.strip()
            for group in str(item.get("group", "")).split(",")
            if group.strip()
        }
        expected_groups = EXPECTED_UPSTREAM_PLUGINS.get(repository)
        if expected_groups is not None and groups != expected_groups:
            errors.append(
                f"{repository}: expected plugin groups {sorted(expected_groups)}, "
                f"found {sorted(groups)}."
            )
        package_required = classification in {
            "mcp-integration",
            "optional-dependency",
        }
        if package_required and not isinstance(item.get("package"), str):
            errors.append(f"{repository}: {classification} requires a package pin.")

    locked = set(repositories)
    missing = REQUIRED_UPSTREAMS - locked
    if missing:
        errors.append(f"upstream-lock.json is missing: {', '.join(sorted(missing))}")
    duplicates = {
        repository for repository in locked if repositories.count(repository) > 1
    }
    if duplicates:
        errors.append(f"Duplicate upstream entries: {', '.join(sorted(duplicates))}")

    unfinished_marker = "[" + "TODO:"
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts and path.suffix in {
            ".json",
            ".md",
            ".py",
            ".mjs",
            ".txt",
        }:
            try:
                contents = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if unfinished_marker in contents:
                errors.append(f"Unfinished placeholder in {path.relative_to(ROOT)}")
            if path.suffix == ".json":
                load_json(path, errors)

    return errors


def validate_plugin(root: Path, name: str, errors: list[str]) -> None:
    manifest_path = root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path, errors)
    if manifest.get("name") != name:
        errors.append(f"{name}: manifest name must match its folder.")
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append(f"{name}: manifest version must be semantic versioning.")
    for field in ("description", "author", "interface"):
        if field not in manifest:
            errors.append(f"{name}: manifest is missing '{field}'.")
    for pointer in ("skills", "mcpServers", "apps"):
        value = manifest.get(pointer)
        if isinstance(value, str) and not (root / value).exists():
            errors.append(f"{name}: {pointer} points to missing path {value}.")

    skills_root = root / "skills"
    if not skills_root.is_dir():
        errors.append(f"{name}: skills directory is missing.")
        return
    for skill_dir in (path for path in skills_root.iterdir() if path.is_dir()):
        skill_path = skill_dir / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"{name}: {skill_dir.name} is missing SKILL.md.")
            continue
        text = skill_path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        if frontmatter.get("name") != skill_dir.name:
            errors.append(f"{name}: skill name must match folder {skill_dir.name}.")
        if not frontmatter.get("description"):
            errors.append(f"{name}: {skill_dir.name} requires a description.")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    result = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"Missing JSON file: {path.relative_to(ROOT)}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"JSON root must be an object: {path.relative_to(ROOT)}")
        return {}
    return data


if __name__ == "__main__":
    problems = validate()
    if problems:
        print("Repository validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        raise SystemExit(1)
    print("Repository validation passed.")
