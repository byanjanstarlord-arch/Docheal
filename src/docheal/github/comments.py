from docheal.reporting import MARKER


def find_bot_comment(comments) -> object | None:
    return next((comment for comment in comments if MARKER in (comment.body or "")), None)

