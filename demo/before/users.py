from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str
    role: str = "user"


def create_user(name: str, email: str) -> User:
    """Create a user with the standard role."""
    return User(name=name, email=email)


def normalize_email(email: str) -> str:
    return email.strip().lower()

