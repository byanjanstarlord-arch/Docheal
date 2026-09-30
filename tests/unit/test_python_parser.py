from docheal.parser import PythonParser


def test_extracts_stable_entities_and_metadata():
    source = '''\
LIMIT = 5

class Service(Base):
    @router.post("/users")
    async def create(self, name: str, role="user") -> dict:
        return {"name": name, "role": role}
'''
    entities = PythonParser().parse_text(source, "src/api.py")
    by_name = {item.qualified_name: item for item in entities}
    assert set(by_name) == {"LIMIT", "Service", "Service.create"}
    method = by_name["Service.create"]
    assert method.id == "src/api.py::Service.create"
    assert method.entity_type == "endpoint"
    assert method.start_line == 4
    assert method.metadata["route_or_command"] == "/users"
    assert "role='user'" in method.signature


def test_ids_do_not_depend_on_line_numbers():
    parser = PythonParser()
    first = parser.parse_text("def work(x):\n    return x\n", "a.py")[0]
    second = parser.parse_text("\n\n\ndef work(x):\n    return x\n", "a.py")[0]
    assert first.id == second.id == "a.py::work"
    assert first.start_line != second.start_line

