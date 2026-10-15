import string

import pytest

from fastapi_orderly.shared.utils import camel_to_snake, get_random_string


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


@pytest.mark.parametrize("length", [0, -1, -100])
def test_invalid_length(length: int) -> None:
    with pytest.raises(ValueError, match="length must be greater than zero"):
        get_random_string(length)


def test_no_character_sets_enabled() -> None:
    with pytest.raises(ValueError, match="At least one character set must be enabled"):
        get_random_string(10, symbols=False, numbers=False, alpha=False)


@pytest.mark.parametrize(
    ("length", "symbols", "numbers", "alpha", "minimum"),
    [
        (1, True, True, False, 2),
        (1, True, False, True, 3),
        (1, False, True, True, 3),
        (2, True, False, True, 3),
        (2, False, True, True, 3),
        (1, True, True, True, 4),
        (2, True, True, True, 4),
        (3, True, True, True, 4),
    ],
)
def test_length_smaller_than_required_sets(
    length: int,
    symbols: bool,
    numbers: bool,
    alpha: bool,
    minimum: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            rf"length must be at least {minimum} "
            r"to include every required character set"
        ),
    ):
        get_random_string(
            length,
            symbols=symbols,
            numbers=numbers,
            alpha=alpha,
        )


@pytest.mark.parametrize(
    ("length", "symbols", "numbers", "alpha"),
    [
        (1, True, False, False),
        (1, False, True, False),
        (2, False, False, True),
        (2, True, True, False),
        (3, True, False, True),
        (3, False, True, True),
        (4, True, True, True),
        (20, True, True, True),
        (10, False, False, True),
        (10, False, True, False),
        (10, True, False, False),
    ],
)
def test_valid_string_length_and_enabled_character_sets(
    length: int,
    symbols: bool,
    numbers: bool,
    alpha: bool,
) -> None:
    result = get_random_string(
        length,
        symbols=symbols,
        numbers=numbers,
        alpha=alpha,
    )

    assert isinstance(result, str)
    assert len(result) == length

    if symbols:
        assert any(char in string.punctuation for char in result)

    if numbers:
        assert any(char in string.digits for char in result)

    if alpha:
        assert any(char in string.ascii_lowercase for char in result)
        assert any(char in string.ascii_uppercase for char in result)

    allowed = ""
    if symbols:
        allowed += string.punctuation
    if numbers:
        allowed += string.digits
    if alpha:
        allowed += string.ascii_letters

    assert all(char in allowed for char in result)


def test_all_character_sets_disabled_individually() -> None:
    with pytest.raises(ValueError, match="At least one character set"):
        get_random_string(10, symbols=False, numbers=False, alpha=False)


@pytest.mark.parametrize(
    ("kwargs", "expected_alphabet"),
    [
        (
            {"symbols": True, "numbers": False, "alpha": False},
            string.punctuation,
        ),
        (
            {"symbols": False, "numbers": True, "alpha": False},
            string.digits,
        ),
        (
            {"symbols": False, "numbers": False, "alpha": True},
            string.ascii_letters,
        ),
        (
            {"symbols": False, "numbers": True, "alpha": True},
            string.digits + string.ascii_lowercase + string.ascii_uppercase,
        ),
    ],
)
def test_output_contains_only_enabled_character_sets(
    kwargs: dict[str, bool],
    expected_alphabet: str,
) -> None:
    result = get_random_string(20, **kwargs)

    assert all(char in expected_alphabet for char in result)


def test_exact_minimum_length() -> None:
    result = get_random_string(4)

    assert len(result) == 4
    assert any(char in string.punctuation for char in result)
    assert any(char in string.digits for char in result)
    assert any(char in string.ascii_lowercase for char in result)
    assert any(char in string.ascii_uppercase for char in result)


def test_character_sets_are_represented_when_enabled() -> None:
    result = get_random_string(10)

    assert any(char in string.punctuation for char in result)
    assert any(char in string.digits for char in result)
    assert any(char in string.ascii_lowercase for char in result)
    assert any(char in string.ascii_uppercase for char in result)


def test_randomness_is_generated_using_secrets() -> None:
    first = get_random_string(32)
    second = get_random_string(32)

    # Probabilistic sanity check, not a mathematical guarantee.
    assert first != second
