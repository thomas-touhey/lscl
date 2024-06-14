#!/usr/bin/env python
# *****************************************************************************
# Copyright (C) 2024 Thomas Touhey <thomas@touhey.fr>
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software. You can use, modify
# and/or redistribute the software under the terms of the CeCILL-C license
# as circulated by CEA, CNRS and INRIA at the following
# URL: https://cecill.info
#
# As a counterpart to the access to the source code and rights to copy, modify
# and redistribute granted by the license, users are provided only with a
# limited warranty and the software's author, the holder of the economic
# rights, and the successive licensors have only limited liability.
#
# In this respect, the user's attention is drawn to the risks associated with
# loading, using, modifying and/or developing or reproducing the software by
# the user in light of its specific status of free software, that may mean
# that it is complicated to manipulate, and that also therefore means that it
# is reserved for developers and experienced professionals having in-depth
# computer knowledge. Users are therefore encouraged to load and test the
# software's suitability as regards their requirements in conditions enabling
# the security of their systems and/or data to be ensured and, more generally,
# to use and operate it in the same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.
# *****************************************************************************
"""Renderer for lscl."""

from __future__ import annotations

from decimal import Decimal
import re
from typing import Union

from pydantic import BaseModel, TypeAdapter
from typing_extensions import TypeAliasType

from .lang import (
    LsclAnd,
    LsclAttribute,
    LsclBlock,
    LsclCondition,
    LsclConditions,
    LsclContent,
    LsclData,
    LsclEqualTo,
    LsclGreaterThan,
    LsclGreaterThanOrEqualTo,
    LsclIn,
    LsclLessThan,
    LsclLessThanOrEqualTo,
    LsclMatch,
    LsclMethodCall,
    LsclNand,
    LsclNot,
    LsclNotEqualTo,
    LsclNotIn,
    LsclNotMatch,
    LsclOr,
    LsclRValue,
    LsclSelector,
    LsclXor,
)


LsclRenderable = TypeAliasType(
    "LsclRenderable",
    Union[
        LsclData,
        LsclCondition,
        LsclConditions,
        LsclAttribute,
        LsclBlock,
        LsclContent,
    ],
)
"""Renderable entities."""

_BAREWORD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")
"""Pattern to check if a word can be replaced as a direct bareword."""

_STRING_ESCAPE_PATTERN = re.compile(r"[\\\\\"'\0\n\r\t]")
"""Pattern to match sequences to escape."""

_STRING_ESCAPE_REPLACEMENTS = {
    "\\": "\\\\",
    '"': '\\"',
    "'": "\\'",
    "\0": "\\0",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}
"""Replacements for escape sequences."""

_PATTERN_ESCAPE_PATTERN = re.compile(r"[/]")
"""Pattern to match sequences to escape in patterns."""


class _LsclContentMatcher(BaseModel):
    value: LsclContent


class _LsclListMatcher(BaseModel):
    value: list[LsclData] | dict[str, LsclData]


_lscl_list_type_adapter = TypeAdapter(_LsclContentMatcher | _LsclListMatcher)


# ---
# Renderer.
# ---


def _render_lscl_string(raw: str, /, *, use_barewords: bool = False) -> str:
    """Render an LSCL string for any context.

    :param raw: Raw string to render.
    :return: Rendered string.
    """
    if use_barewords and _BAREWORD_PATTERN.fullmatch(raw):
        return raw

    raw = _STRING_ESCAPE_PATTERN.sub(
        lambda match: _STRING_ESCAPE_REPLACEMENTS[match[0]],
        raw,
    )
    return '"' + raw + '"'


def _render_lscl_pattern(raw: re.Pattern, /) -> str:
    """Render an LSCL string as a pattern.

    :param raw: Raw string to render.
    :return: Rendered string.
    """
    escaped = _PATTERN_ESCAPE_PATTERN.sub(
        lambda match: "\\" + match[0],
        raw.pattern,
    )
    return f"/{escaped}/"


def _render_lscl_data(content: LsclData, /, *, prefix: str) -> str:
    """Render LSCL data.

    This function considers that the beginning is already indented correctly,
    and always adds a newline at the end.

    :param content: Content to render.
    :param prefix: Prefix to render with.
    :return: Rendered content.
    """
    if isinstance(content, dict):
        if not content:
            return "{}\n"

        rendered = "{\n"
        for key, value in content.items():
            rendered += (
                prefix
                + "  "
                + _render_lscl_string(key, use_barewords=True)
                + " => "
                + _render_lscl_data(value, prefix=prefix + "  ")
            )

        return rendered + prefix + "}\n"

    if isinstance(content, list):
        if not content:
            return "[]\n"

        rendered = "[\n"
        for i, value in enumerate(content):
            rendered += (
                prefix + "  " + _render_lscl_data(value, prefix=prefix + "  ")
            )
            if i < len(content) - 1:
                rendered = rendered[:-1] + ",\n"

        return rendered + prefix + "]\n"

    if isinstance(content, (int, float, Decimal)):
        return str(content) + "\n"

    if isinstance(content, str):
        return _render_lscl_string(content, use_barewords=True) + "\n"

    raise NotImplementedError()  # pragma: no cover


def _render_lscl_selector(content: LsclSelector, /) -> str:
    """Render an LSCL selector.

    :param content: Content to render.
    :return: Rendered selector.
    """
    return "".join(f"[{name}]" for name in content.names)


def _render_lscl_rvalue(content: LsclRValue, /) -> str:
    """Render an LSCL right-value.

    :param content: Content to render.
    :return: Rendered right-value.
    """
    if isinstance(content, LsclSelector):
        return _render_lscl_selector(content)

    if isinstance(content, LsclMethodCall):
        return (
            f"{content.name}("
            + ", ".join(_render_lscl_rvalue(param) for param in content.params)
            + ")"
        )

    if isinstance(content, str):
        return _render_lscl_string(content)  # No barewords allowed here!

    if isinstance(content, (int, float, Decimal)):
        return str(content)

    raise NotImplementedError()  # pragma: no cover


def _render_lscl_condition(content: LsclCondition, /) -> str:
    """Render an LSCL condition.

    :param content: Condition to render.
    :return: Rendered condition.
    """
    if isinstance(content, (LsclAnd, LsclOr, LsclXor, LsclNand)):
        if len(content.conditions) == 1:
            return _render_lscl_condition(content.conditions[0])

        if isinstance(content, LsclAnd):
            op = " and "
        elif isinstance(content, LsclOr):
            op = " or "
        elif isinstance(content, LsclXor):
            op = " xor "
        else:
            op = " nand "

        rendered_conditions: list[str] = []
        for cond in content.conditions:
            rendered = _render_lscl_condition(cond)
            if isinstance(cond, (LsclAnd, LsclOr, LsclXor, LsclNand)):
                rendered = f"({rendered})"

            rendered_conditions.append(rendered)

        result = op.join(rendered_conditions)
    elif isinstance(content, LsclNot):
        if isinstance(content.condition, LsclSelector):
            result = "!" + _render_lscl_selector(content.condition)
        else:
            result = "!(" + _render_lscl_condition(content.condition) + ")"
    elif isinstance(content, LsclIn):
        result = (
            _render_lscl_rvalue(content.needle)
            + " in "
            + _render_lscl_rvalue(content.haystack)
        )
    elif isinstance(content, LsclNotIn):
        result = (
            _render_lscl_rvalue(content.needle)
            + " not in "
            + _render_lscl_rvalue(content.haystack)
        )
    elif isinstance(content, LsclEqualTo):
        result = (
            _render_lscl_rvalue(content.first)
            + " == "
            + _render_lscl_rvalue(content.second)
        )
    elif isinstance(content, LsclNotEqualTo):
        result = (
            _render_lscl_rvalue(content.first)
            + " != "
            + _render_lscl_rvalue(content.second)
        )
    elif isinstance(content, LsclGreaterThanOrEqualTo):
        result = (
            _render_lscl_rvalue(content.first)
            + " >= "
            + _render_lscl_rvalue(content.second)
        )
    elif isinstance(content, LsclLessThanOrEqualTo):
        result = (
            _render_lscl_rvalue(content.first)
            + " <= "
            + _render_lscl_rvalue(content.second)
        )
    elif isinstance(content, LsclGreaterThan):
        result = (
            _render_lscl_rvalue(content.first)
            + " > "
            + _render_lscl_rvalue(content.second)
        )
    elif isinstance(content, LsclLessThan):
        result = (
            _render_lscl_rvalue(content.first)
            + " < "
            + _render_lscl_rvalue(content.second)
        )
    elif isinstance(content, LsclMatch):
        result = (
            _render_lscl_rvalue(content.value)
            + " =~ "
            + _render_lscl_pattern(content.pattern)
        )
    elif isinstance(content, LsclNotMatch):
        result = (
            _render_lscl_rvalue(content.value)
            + " !~ "
            + _render_lscl_pattern(content.pattern)
        )
    else:
        result = _render_lscl_rvalue(content)

    return result


def _render_lscl_content(content: LsclContent, /, *, prefix: str) -> str:
    """Render LSCL content.

    :param content: Content to render.
    :param prefix: Prefix to render with.
    :return: Rendered content.
    """
    rendered = ""
    for element in content:
        if isinstance(element, LsclBlock):
            if element.content:
                rendered += (
                    f"{prefix}{element.name} {'{'}\n"
                    + _render_lscl_content(
                        element.content,
                        prefix=prefix + "  ",
                    )
                    + f"{prefix}{'}'}\n"
                )
            else:
                rendered += f"{prefix}{element.name} {'{}'}\n"
        elif isinstance(element, LsclAttribute):
            rendered += f"{prefix}{element.name} => " + _render_lscl_data(
                element.content,
                prefix=prefix,
            )
        else:
            before_cond = prefix

            for cond, body in element.conditions:
                rendered += f"{before_cond}if " + _render_lscl_condition(cond)

                if body:
                    rendered += (
                        " {\n"
                        + _render_lscl_content(body, prefix=prefix + "  ")
                        + prefix
                        + "}"
                    )
                    before_cond = " else "
                else:
                    rendered += " {}"
                    before_cond = f"\n{prefix}else "

            if element.default is not None:
                if element.default:
                    rendered += (
                        before_cond
                        + "{\n"
                        + _render_lscl_content(
                            element.default,
                            prefix=prefix + "  ",
                        )
                        + prefix
                        + "}"
                    )
                else:
                    rendered += before_cond + "{}"

            rendered += "\n"

    return rendered


def render_as_lscl(content: LsclRenderable, /) -> str:
    """Render content as LSCL.

    :param content: Content to render as LSCL.
    :return: Rendered content.
    """
    if isinstance(content, (str, int, float, Decimal)):
        return _render_lscl_data(content, prefix="")

    if isinstance(content, (LsclSelector, LsclMethodCall)):
        return _render_lscl_rvalue(content)

    if isinstance(
        content,
        (
            LsclAnd,
            LsclNand,
            LsclOr,
            LsclXor,
            LsclNot,
            LsclIn,
            LsclNotIn,
            LsclEqualTo,
            LsclNotEqualTo,
            LsclGreaterThan,
            LsclGreaterThanOrEqualTo,
            LsclLessThan,
            LsclLessThanOrEqualTo,
            LsclMatch,
            LsclNotMatch,
        ),
    ):
        return _render_lscl_condition(content)

    if isinstance(content, (LsclBlock, LsclAttribute, LsclConditions)):
        return _render_lscl_content([content], prefix="")

    # We can either have an LsclContent, an list[LsclData], or something
    # else we don't manage here, e.g. some weird mix of both.
    # We want to use pydantic to determine which it is.
    try:
        result = _lscl_list_type_adapter.validate_python({"value": content})
    except ValueError as exc:
        raise TypeError(
            f"Unable to render {type(content)} into LSCL.",
        ) from exc

    if isinstance(result, _LsclContentMatcher):
        return _render_lscl_content(result.value, prefix="")

    return _render_lscl_data(result.value, prefix="")
