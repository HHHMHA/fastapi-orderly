import pytest

from fastapi_orderly.shared.utils import camel_to_snake


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("CamelCase", "camel_case"),
        ("camelCase", "camel_case"),
        ("PascalCase", "pascal_case"),
        ("ABC", "abc"),
        ("ABCDef", "abc_def"),
        ("XMLHttpRequest", "xml_http_request"),
        ("HTTPResponseCode", "http_response_code"),
        ("already_snake_case", "already_snake_case"),
        ("lowercase", "lowercase"),
        ("123Value", "123_value"),
        ("value123", "value123"),
        ("value123ABC", "value123_abc"),
        ("", ""),
    ],
)
def test_camel_to_snake(value: str, expected: str) -> None:
    assert camel_to_snake(value) == expected
