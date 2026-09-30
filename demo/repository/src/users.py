from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str
    role: str = "user"


def create_user(
    name: str,
    email: str,
    role: str = "user",
    send_welcome_email: bool = True,
) -> User:
    """Create a user with an explicitly selectable role."""
    return User(name=name, email=email, role=role)


def normalize_email(email: str) -> str:
    return email.strip().lower()

