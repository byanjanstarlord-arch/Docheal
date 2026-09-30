from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_action_contract_and_workflow_permissions():
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "docker"
    assert action["inputs"]["openai_api_key"]["required"] is True
    assert {"sections_checked", "stale_sections", "created_pr_url"} <= set(action["outputs"])
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "demo.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "write", "pull-requests": "write"}
