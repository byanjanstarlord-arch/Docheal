from __future__ import annotations

from pathlib import PurePosixPath

from docheal.errors import GitHubIntegrationError
from docheal.github.comments import find_bot_comment


class GitHubClient:
    def __init__(self, token: str, repository: str) -> None:
        if not token or not repository:
            raise GitHubIntegrationError("GitHub token and repository name are required")
        try:
            from github import Auth, Github
        except ImportError as exc:
            raise GitHubIntegrationError("PyGithub is not installed") from exc
        self._github = Github(auth=Auth.Token(token))
        self.repository = self._github.get_repo(repository)

    @staticmethod
    def _cleanup_ref(ref: object | None) -> str | None:
        if ref is None:
            return None
        try:
            ref.delete()
        except Exception as exc:  # noqa: BLE001 - third-party API exceptions vary by transport
            return str(exc)
        return None

    def upsert_pr_comment(self, pr_number: int, body: str) -> None:
        try:
            issue = self.repository.get_issue(pr_number)
            existing = find_bot_comment(issue.get_comments())
            if existing:
                existing.edit(body)
            else:
                issue.create_comment(body)
        except Exception as exc:
            raise GitHubIntegrationError(f"could not update PR comment: {exc}") from exc

    def create_documentation_pr(
        self,
        *,
        base_branch: str,
        branch_name: str,
        title: str,
        body: str,
        replacements: list[tuple[str, str, str]],
    ) -> str:
        """Create an isolated branch and PR containing Markdown replacements only."""
        if not replacements:
            raise GitHubIntegrationError("cannot create an empty documentation PR")
        for path, _old, _new in replacements:
            pure = PurePosixPath(path)
            if pure.is_absolute() or ".." in pure.parts or pure.suffix.lower() not in {".md", ".markdown"}:
                raise GitHubIntegrationError(f"unsafe documentation path: {path}")
        ref = None
        try:
            base_sha = self.repository.get_branch(base_branch).commit.sha
            ref = self.repository.create_git_ref(f"refs/heads/{branch_name}", base_sha)
            by_file: dict[str, list[tuple[str, str]]] = {}
            for path, old, new in replacements:
                by_file.setdefault(path, []).append((old, new))
            for path, edits in by_file.items():
                source = self.repository.get_contents(path, ref=base_branch)
                content = source.decoded_content.decode("utf-8")
                for old, new in edits:
                    if content.count(old) != 1:
                        raise GitHubIntegrationError(f"expected section exactly once in {path}")
                    content = content.replace(old, new, 1)
                self.repository.update_file(
                    path, f"docs: synchronize {path} with code", content, source.sha, branch=branch_name
                )
            pull = self.repository.create_pull(title=title, body=body, head=branch_name, base=base_branch)
            return pull.html_url
        except GitHubIntegrationError as exc:
            cleanup_error = self._cleanup_ref(ref)
            if cleanup_error:
                raise GitHubIntegrationError(f"{exc}; temporary branch cleanup also failed: {cleanup_error}") from exc
            raise
        except Exception as exc:
            cleanup_error = self._cleanup_ref(ref)
            suffix = f"; temporary branch cleanup also failed: {cleanup_error}" if cleanup_error else ""
            raise GitHubIntegrationError(f"could not create documentation PR: {exc}{suffix}") from exc
