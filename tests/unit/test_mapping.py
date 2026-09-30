from docheal.mapping import HeuristicMapper, SemanticMapper
from docheal.parser import MarkdownParser, PythonParser


class FakeEmbeddings:
    def embed(self, texts):
        return [[1.0, 0.0], [0.9, 0.1]]


def test_deterministic_symbol_mapping():
    entity = PythonParser().parse_text("def create_user(name):\n    return name\n", "src/users.py")
    section = MarkdownParser().parse_text("## create_user\nCall `create_user(name)`.\n", "docs/users.md")
    links = HeuristicMapper().map(entity, section)
    assert len(links) == 1
    assert links[0].source == "deterministic"
    assert links[0].confidence == 1


def test_semantic_mapping_interface():
    entity = PythonParser().parse_text("def charge(amount):\n    return amount\n", "src/pay.py")
    section = MarkdownParser().parse_text("## Billing\nCollect money.\n", "docs/pay.md")
    links = SemanticMapper(FakeEmbeddings(), threshold=0.8).map(entity, section)
    assert len(links) == 1
    assert links[0].link_type == "semantic"

