from typing import Annotated

from fastapi import Depends

from fastapi_orderly.core.config import Settings, get_settings
from fastapi_orderly.modules.auth.token import PysetoTokenizer


def get_tokenizer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PysetoTokenizer:
    return PysetoTokenizer(settings)
