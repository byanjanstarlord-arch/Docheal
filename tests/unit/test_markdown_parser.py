from docheal.parser import MarkdownParser


def test_heading_hierarchy_locations_and_references():
    source = "# API\nIntro\n\n## Users\nCall `create_user(name, email)`.\n\n### Notes\nSafe.\n"
    sections = MarkdownParser().parse_text(source, "docs/api.md")
    assert [item.heading for item in sections] == ["API", "Users", "Notes"]
    assert sections[1].heading_path == ["API", "Users"]
    assert sections[1].referenced_symbols == ["create_user"]
    assert sections[1].start_line == 4
    assert sections[1].end_line == 6
    assert sections[2].parent_id == sections[1].id


def test_ignores_headings_inside_code_fences():
    source = "# Real\n```md\n# Example\n```\ntext\n"
    assert [item.heading for item in MarkdownParser().parse_text(source, "x.md")] == ["Real"]

