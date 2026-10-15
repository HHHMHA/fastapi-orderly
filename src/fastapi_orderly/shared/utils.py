import re
import secrets
import string


def camel_to_snake(value: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", value)
    return value.lower()


def get_random_string(
    length: int,
    *,
    symbols: bool = True,
    numbers: bool = True,
    alpha: bool = True,
) -> str:
    if length < 1:
        raise ValueError("length must be greater than zero")

    required_sets: list[str] = []

    if symbols:
        required_sets.append(string.punctuation)
    if numbers:
        required_sets.append(string.digits)
    if alpha:
        required_sets.extend([string.ascii_lowercase, string.ascii_uppercase])

    if not required_sets:
        raise ValueError("At least one character set must be enabled")

    if length < len(required_sets):
        raise ValueError(
            f"length must be at least {len(required_sets)} to include every required character set"
        )

    alphabet = "".join(required_sets)

    chars = [secrets.choice(charset) for charset in required_sets]

    chars.extend(secrets.choice(alphabet) for _ in range(length - len(chars)))

    secrets.SystemRandom().shuffle(chars)

    return "".join(chars)
