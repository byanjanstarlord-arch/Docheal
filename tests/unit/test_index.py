from pathlib import Path

from docheal.mapping import HeuristicMapper
from docheal.mapping.graph import RepositoryIndex
from docheal.parser import MarkdownParser, PythonParser


def test_index_round_trip_is_inspectable_json(tmp_path: Path):
    entities = PythonParser().parse_text("def f(x):\n    return x\n", "a.py")
    sections = MarkdownParser().parse_text("# f\n`f(x)`\n", "a.md")
    index = RepositoryIndex(code_entities=entities, documentation_sections=sections, links=HeuristicMapper().map(entities, sections))
    path = tmp_path / ".docheal" / "index.json"
    index.save(path)
    loaded = RepositoryIndex.load(path)
    assert loaded == index
    assert '"schema_version": 1' in path.read_text(encoding="utf-8")
