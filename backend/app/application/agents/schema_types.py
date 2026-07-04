"""Shared Pydantic field types for AI structured-output schemas.

Small local models frequently collapse a `list[str]` bullet-point field
(reasons, pros/cons, risks...) into a single prose string instead of a JSON
array. Structurally the model still gave real content — just shaped wrong —
so `StrList` reshapes rather than failing validation and burning a retry.
"""
from typing import Annotated

from pydantic import BeforeValidator


def _coerce_str_to_list(value: object) -> object:
    return [value] if isinstance(value, str) else value


StrList = Annotated[list[str], BeforeValidator(_coerce_str_to_list)]
