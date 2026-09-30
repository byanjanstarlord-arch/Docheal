from importlib.resources import files


def load_prompt(name: str) -> str:
    return files(__package__).joinpath(f"{name}.txt").read_text(encoding="utf-8")

