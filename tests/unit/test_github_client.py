from types import SimpleNamespace

import pytest

from docheal.errors import GitHubIntegrationError
from docheal.github.client import GitHubClient
from docheal.reporting import MARKER


class Comment:
    def __init__(self, body):
        self.body = body
        self.edited = None

    def edit(self, body):
        self.edited = body


class Issue:
    def __init__(self, comments):
        self.comments = comments
        self.created = []

    def get_comments(self):
        return self.comments

    def create_comment(self, body):
        self.created.append(body)


def test_existing_bot_comment_is_updated():
    comment = Comment(f"{MARKER}\nold")
    issue = Issue([comment])
    client = object.__new__(GitHubClient)
    client.repository = SimpleNamespace(get_issue=lambda _number: issue)
    client.upsert_pr_comment(12, f"{MARKER}\nnew")
    assert comment.edited.endswith("new")
    assert issue.created == []


def test_repair_pr_rejects_source_file_target():
    client = object.__new__(GitHubClient)
    with pytest.raises(GitHubIntegrationError, match="unsafe documentation path"):
        client.create_documentation_pr(
            base_branch="feature", branch_name="docheal/fix", title="fix", body="body",
            replacements=[("src/api.py", "old", "new")],
        )
