from __future__ import annotations

import ast
import hashlib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from docheal.errors import ParserError
from docheal.models import CodeEntity


def _stable_id(file_path: str, qualified_name: str) -> str:
    return f"{PurePosixPath(file_path).as_posix()}::{qualified_name}"


def _decorator_name(node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    parts: list[str] = []
    while isinstance(target, ast.Attribute):
        parts.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        parts.append(target.id)
    return ".".join(reversed(parts))


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = ast.unparse(node.args)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({args}){returns}"


class PythonParser:
    """AST parser that never imports or executes repository code."""

    def parse_file(self, path: Path, repository_root: Path | None = None) -> list[CodeEntity]:
        root = (repository_root or path.parent).resolve()
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
            source = resolved.read_text(encoding="utf-8")
        except (OSError, ValueError) as exc:
            raise ParserError(f"cannot read Python source {path}: {exc}") from exc
        return self.parse_text(source, relative)

    def parse_text(self, source: str, file_path: str) -> list[CodeEntity]:
        normalized_path = PurePosixPath(file_path).as_posix()
        try:
            tree = ast.parse(source, filename=normalized_path, type_comments=True)
        except SyntaxError as exc:
            raise ParserError(f"invalid Python in {normalized_path}:{exc.lineno}: {exc.msg}") from exc
        lines = source.splitlines(keepends=True)
        entities: list[CodeEntity] = []
        self._collect(tree.body, [], normalized_path, lines, entities)
        return entities

    def _collect(
        self,
        body: Iterable[ast.stmt],
        scope: list[str],
        file_path: str,
        lines: list[str],
        entities: list[CodeEntity],
    ) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = ".".join([*scope, node.name])
                decorators = [_decorator_name(item) for item in node.decorator_list]
                endpoint = next((name for name in decorators if name.split(".")[-1] in {"get", "post", "put", "patch", "delete"}), None)
                cli = next((name for name in decorators if name.split(".")[-1] in {"command", "callback"}), None)
                entity_type = "method" if scope else "function"
                if endpoint:
                    entity_type = "endpoint"
                elif cli:
                    entity_type = "cli"
                metadata: dict[str, object] = {
                    "decorators": decorators,
                    "parameters": [arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
                if node.decorator_list:
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and decorator.args:
                            first = decorator.args[0]
                            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                                metadata["route_or_command"] = first.value
                                break
                entities.append(self._entity(node, file_path, qualified, entity_type, lines, _signature(node), metadata))
            elif isinstance(node, ast.ClassDef):
                qualified = ".".join([*scope, node.name])
                metadata = {
                    "decorators": [_decorator_name(item) for item in node.decorator_list],
                    "bases": [ast.unparse(base) for base in node.bases],
                }
                signature = f"class {node.name}({', '.join(metadata['bases'])})" if metadata["bases"] else f"class {node.name}"
                entities.append(self._entity(node, file_path, qualified, "class", lines, signature, metadata))
                self._collect(node.body, [*scope, node.name], file_path, lines, entities)
            elif not scope and isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and (target.id.isupper() or target.id.endswith("_CONFIG")):
                        entities.append(
                            self._entity(node, file_path, target.id, "constant", lines, target.id, {"configuration": True})
                        )

    @staticmethod
    def _entity(
        node: ast.AST,
        file_path: str,
        qualified_name: str,
        entity_type: str,
        lines: list[str],
        signature: str,
        metadata: dict[str, object],
    ) -> CodeEntity:
        start = min([getattr(node, "lineno", 1), *[getattr(d, "lineno", 1) for d in getattr(node, "decorator_list", [])]])
        end = getattr(node, "end_lineno", start)
        source = "".join(lines[start - 1 : end]).rstrip("\r\n")
        metadata["content_hash"] = hashlib.sha256(source.encode()).hexdigest()
        return CodeEntity(
            id=_stable_id(file_path, qualified_name),
            file_path=file_path,
            symbol_name=qualified_name.rsplit(".", 1)[-1],
            entity_type=entity_type,
            qualified_name=qualified_name,
            source_code=source,
            start_line=start,
            end_line=end,
            signature=signature,
            metadata=metadata,
        )
