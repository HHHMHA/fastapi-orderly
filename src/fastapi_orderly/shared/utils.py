import re


def camel_to_snake(value: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", value)
    return value.lower()
