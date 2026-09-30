class DocHealError(Exception):
    """Base error for expected DocHeal failures."""


class ConfigurationError(DocHealError):
    pass


class ParserError(DocHealError):
    pass


class EmbeddingError(DocHealError):
    pass


class LLMError(DocHealError):
    pass


class ValidationError(DocHealError):
    pass


class PatchError(DocHealError):
    pass


class GitHubIntegrationError(DocHealError):
    pass

