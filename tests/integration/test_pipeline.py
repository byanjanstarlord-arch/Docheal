from pathlib import Path

from docheal.config import load_config
from docheal.demo_provider import DemoLLMProvider
from docheal.diff import DiffAnalyzer
from docheal.parser import PythonParser
from docheal.pipeline import AnalysisPipeline, build_index

ROOT = Path(__file__).resolve().parents[2]


def test_demo_repository_end_to_end():
    repository = ROOT / "demo" / "repository"
    config = load_config(ROOT / "config" / "default.yaml")
    config.github.auto_fix_enabled = True
    index = build_index(repository, config, persist=False)
    parser = PythonParser()
    before = parser.parse_text((ROOT / "demo" / "before" / "users.py").read_text(encoding="utf-8"), "src/users.py")
    after = parser.parse_file(repository / "src" / "users.py", repository)
    changes = DiffAnalyzer().compare_entities(before, after)
    result = AnalysisPipeline(config, DemoLLMProvider()).run(changes, index)
    assert result.entities_changed == 1
    assert result.sections_checked == 1
    assert result.stale_count == 1
    assert result.repairs_validated == 1
    assert result.findings[0].decision.action == "AUTO_FIX"
    assert "role" in result.findings[0].repair.corrected_content
