from docheal.detection import AffectedDocumentationResolver
from docheal.diff import DiffAnalyzer
from docheal.mapping import HeuristicMapper
from docheal.mapping.graph import RepositoryIndex
from docheal.parser import MarkdownParser, PythonParser


def test_resolves_only_linked_sections():
    parser = PythonParser()
    old = parser.parse_text("def f(x):\n    return x\n", "a.py")
    new = parser.parse_text("def f(x, y):\n    return x + y\n", "a.py")
    sections = MarkdownParser().parse_text("# API\n## f\nUse `f(x)`.\n## g\nUse `g()`.\n", "api.md")
    links = HeuristicMapper().map(new, sections)
    index = RepositoryIndex(code_entities=new, documentation_sections=sections, links=links)
    changes = DiffAnalyzer().compare_entities(old, new)
    result = AffectedDocumentationResolver().resolve(changes, index)
    assert [item.heading for item, _ in result["a.py::f"]] == ["f"]


def test_removed_entity_can_still_find_current_documentation():
    old = PythonParser().parse_text("def removed(x):\n    return x\n", "a.py")
    changes = DiffAnalyzer().compare_entities(old, [])
    sections = MarkdownParser().parse_text("# API\n## removed\nUse `removed(x)`.\n", "api.md")
    index = RepositoryIndex(code_entities=[], documentation_sections=sections, links=[])
    result = AffectedDocumentationResolver().resolve(changes, index)
    assert result["a.py::removed"][0][0].heading == "removed"
