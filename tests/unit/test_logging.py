from docheal.logging.structured import _sanitize


def test_secrets_are_redacted_but_usage_counts_are_preserved():
    value = _sanitize({"api_key": "secret", "nested": {"github_token": "secret", "prompt_tokens": 42}})
    assert value["api_key"] == "[REDACTED]"
    assert value["nested"]["github_token"] == "[REDACTED]"
    assert value["nested"]["prompt_tokens"] == 42
