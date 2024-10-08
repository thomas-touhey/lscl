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
from typing import Literal, Union

from pydantic import BaseModel, TypeAdapter
from typing_extensions import TypeAliasType

from .errors import SelectorElementRenderingError, StringRenderingError
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
    LsclLiteral,
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

_PATTERN_ESCAPE_PATTERN = re.compile(r"[/]")
"""Pattern to match sequences to escape in patterns."""

_BASE_STRING_ESCAPE_DISABLED_REPLACEMENTS = {
    "\\": "\\",
    "\n": "\n",
    "\t": "\t",
}
"""Replacements to use when string escapes are disabled."""

_DOUBLE_QUOTE_STRING_ESCAPE_DISABLED_REPLACEMENTS = {
    **_BASE_STRING_ESCAPE_DISABLED_REPLACEMENTS,
    "'": "'",
}
"""Replacements for chars to escape when double string escaping is disabled."""

_SINGLE_QUOTE_STRING_ESCAPE_DISABLED_REPLACEMENTS = {
    **_BASE_STRING_ESCAPE_DISABLED_REPLACEMENTS,
    '"': '"',
}
"""Replacements for chars to escape when single string escaping is disabled."""

_BASE_STRING_ESCAPE_REPLACEMENTS = {
    "\\": "\\\\",
    "\0": "\\0",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    '"': '"',
    "'": "'",
}
"""Replacements for escape sequences in all strings."""

_DOUBLE_QUOTE_STRING_ESCAPE_REPLACEMENTS = {
    **_BASE_STRING_ESCAPE_REPLACEMENTS,
    '"': '\\"',
}
"""Replacements for escape sequences in double quote strings."""

_SINGLE_QUOTE_STRING_ESCAPE_REPLACEMENTS = {
    **_BASE_STRING_ESCAPE_REPLACEMENTS,
    "'": "\\'",
}
"""Replacements for escape sequences in single quote strings."""


class _LsclContentMatcher(BaseModel):
    value: LsclContent


class _LsclListMatcher(BaseModel):
    value: list[LsclData] | dict[str | LsclLiteral, LsclData]


_lscl_list_type_adapter = TypeAdapter(_LsclContentMatcher | _LsclListMatcher)


# ---
# Renderer.
# ---


class _LsclRenderingOptions(BaseModel):
    """Renderer options for LSCL."""

    escapes_supported: bool
    """Whether escapes are supported."""

    field_reference_escape_style: Literal["percent", "ampersand", "none"]
    """Escape style of field references."""


def _render_lscl_string(
    raw: str,
    /,
    *,
    options: _LsclRenderingOptions,
    use_barewords: bool = False,
) -> str:
    """Render an LSCL string for any context.

    :param raw: Raw string to render.
    :param options: Rendering options.
    :return: Rendered string.
    """
    if use_barewords and _BAREWORD_PATTERN.fullmatch(raw):
        return raw

    if '"' not in raw or "'" in raw:
        delimiter = '"'
        if options.escapes_supported:
            replacements = _DOUBLE_QUOTE_STRING_ESCAPE_REPLACEMENTS
        else:
            replacements = _DOUBLE_QUOTE_STRING_ESCAPE_DISABLED_REPLACEMENTS
    else:
        delimiter = "'"
        if options.escapes_supported:
            replacements = _SINGLE_QUOTE_STRING_ESCAPE_REPLACEMENTS
        else:
            replacements = _SINGLE_QUOTE_STRING_ESCAPE_DISABLED_REPLACEMENTS

    def repl(m: re.Match, /) -> str:
        """Replace the provided match with the corresponding escape code."""
        try:
            return replacements[m[0]]
        except KeyError:
            raise StringRenderingError(string=raw)

    raw = _STRING_ESCAPE_PATTERN.sub(repl, raw)
    return delimiter + raw + delimiter


def _render_lscl_pattern(
    raw: re.Pattern,
    /,
    *,
    options: _LsclRenderingOptions,
) -> str:
    """Render an LSCL string as a pattern.

    :param raw: Raw string to render.
    :param options: Rendering options.
    :return: Rendered string.
    """
    escaped = _PATTERN_ESCAPE_PATTERN.sub(
        lambda match: "\\" + match[0],
        raw.pattern,
    )
    return f"/{escaped}/"


def _render_lscl_data(
    content: LsclData,
    /,
    *,
    options: _LsclRenderingOptions,
    prefix: str,
) -> str:
    """Render LSCL data.

    This function considers that the beginning is already indented correctly,
    and always adds a newline at the end.

    :param content: Content to render.
    :param options: Rendering options.
    :param prefix: Prefix to render with.
    :return: Rendered content.
    """
    if isinstance(content, LsclLiteral):
        return content.content + "\n"

    if isinstance(content, dict):
        if not content:
            return "{}\n"

        rendered = "{\n"
        for key, value in content.items():
            if isinstance(key, LsclLiteral):
                rendered_key = key.content
            else:
                rendered_key = _render_lscl_string(
                    key,
                    options=options,
                    use_barewords=True,
                )

            rendered += (
                prefix
                + "  "
                + rendered_key
                + " => "
                + _render_lscl_data(
                    value,
                    options=options,
                    prefix=prefix + "  ",
                )
            )

        return rendered + prefix + "}\n"

    if isinstance(content, list):
        if not content:
            return "[]\n"

        rendered = "[\n"
        for i, value in enumerate(content):
            rendered += (
                prefix
                + "  "
                + _render_lscl_data(
                    value,
                    options=options,
                    prefix=prefix + "  ",
                )
            )
            if i < len(content) - 1:
                rendered = rendered[:-1] + ",\n"

        return rendered + prefix + "]\n"

    if isinstance(content, bool):
        return "true\n" if content else "false\n"

    if isinstance(content, (int, float, Decimal)):
        return str(content) + "\n"

    if isinstance(content, str):
        return (
            _render_lscl_string(content, options=options, use_barewords=True)
            + "\n"
        )

    raise NotImplementedError()  # pragma: no cover


_PERCENT_ENCODING_PATTERN = re.compile(r"%([0-9A-F]{2})")
"""Pattern to use to find percent signs that require percent-encoding.

This is done because '%' not followed by two uppercase hexadecimal digits
are **not** unescaped, hence there is no need to percent-encode them.

See `PERCENT EscapeHandler`_ for more information.

.. _PERCENT EscapeHandler:
    https://github.com/elastic/logstash/blob/
    3480c32b6ee64f5b1193f5c3b4f0f722731c0fda/logstash-core/src/main/java/org/
    logstash/util/EscapeHandler.java#L26
"""

_AMPERSAND_ENCODING_PATTERN = re.compile(r"&#([0-9]{2,});")
"""Pattern to use to find ampersands that require ampersand-encoding.

This is done because '&' that do not introduce valid ampersand patterns
are **not** unescaped, hence there is no need to ampersand-encode them.

.. _AMPERSAND EscapeHandler:
    https://github.com/elastic/logstash/blob/
    3480c32b6ee64f5b1193f5c3b4f0f722731c0fda/logstash-core/src/main/java/org/
    logstash/util/EscapeHandler.java#L53
"""


def _render_lscl_selector_element(
    element: str,
    /,
    *,
    options: _LsclRenderingOptions,
) -> str:
    """Render an LSCL selector element.

    :param content: Content to render.
    :param options: Rendering options.
    :return: Rendered selector.
    """
    if options.field_reference_escape_style == "none":
        if "[" in element or "]" in element or "," in element:
            raise SelectorElementRenderingError(selector_element=element)
    elif options.field_reference_escape_style == "percent":
        # NOTE: As opposed to Logstash's percent escape function, we
        #       also escape commas.
        element = (
            _PERCENT_ENCODING_PATTERN.sub(r"%25\1", element)
            .replace("[", "%5B")
            .replace("]", "%5D")
            .replace(",", "%2C")
        )
    elif options.field_reference_escape_style == "ampersand":
        # NOTE: As opposed to Logstash's ampersand escape function, we
        #       also escape commas.
        element = (
            _AMPERSAND_ENCODING_PATTERN.sub(r"&#38;#\1;", element)
            .replace("[", "&#91;")
            .replace("]", "&#93;")
            .replace(",", "&#44;")
        )
    else:  # pragma: no cover
        raise NotImplementedError()

    return f"[{element}]"


def _render_lscl_selector(
    content: LsclSelector,
    /,
    *,
    options: _LsclRenderingOptions,
) -> str:
    """Render an LSCL selector.

    :param content: Content to render.
    :param options: Rendering options.
    :return: Rendered selector.
    """
    return "".join(
        _render_lscl_selector_element(name, options=options)
        for name in content.names
    )


def _render_lscl_rvalue(
    content: LsclRValue,
    /,
    *,
    options: _LsclRenderingOptions,
    prefix: str,
) -> str:
    """Render an LSCL right-value.

    :param content: Content to render.
    :param options: Rendering options.
    :param prefix: Prefix to render with.
    :return: Rendered right-value.
    """
    if isinstance(content, (list, LsclLiteral)):
        return _render_lscl_data(content, options=options, prefix=prefix)[:-1]

    if isinstance(content, LsclSelector):
        return _render_lscl_selector(content, options=options)

    if isinstance(content, LsclMethodCall):
        return (
            f"{content.name}("
            + ", ".join(
                _render_lscl_rvalue(param, options=options, prefix=prefix)
                for param in content.params
            )
            + ")"
        )

    if isinstance(content, str):
        return _render_lscl_string(
            content,
            options=options,
            use_barewords=False,
        )

    if isinstance(content, (int, bool, float, Decimal)):
        return str(content)

    raise NotImplementedError()  # pragma: no cover


def _render_lscl_condition(
    content: LsclCondition,
    /,
    *,
    options: _LsclRenderingOptions,
    prefix: str,
) -> str:
    """Render an LSCL condition.

    :param content: Condition to render.
    :param options: Rendering options.
    :param prefix: Prefix.
    :return: Rendered condition.
    """
    if isinstance(content, (LsclAnd, LsclOr, LsclXor, LsclNand)):
        if len(content.conditions) == 1:
            return _render_lscl_condition(
                content.conditions[0],
                options=options,
                prefix=prefix,
            )

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
            rendered = _render_lscl_condition(
                cond,
                options=options,
                prefix=prefix,
            )
            if isinstance(cond, (LsclAnd, LsclOr, LsclXor, LsclNand)):
                rendered = f"({rendered})"

            rendered_conditions.append(rendered)

        result = op.join(rendered_conditions)
    elif isinstance(content, LsclNot):
        if isinstance(content.condition, LsclSelector):
            result = "!" + _render_lscl_selector(
                content.condition,
                options=options,
            )
        else:
            result = (
                "!("
                + _render_lscl_condition(
                    content.condition,
                    options=options,
                    prefix=prefix,
                )
                + ")"
            )
    elif isinstance(content, LsclIn):
        result = (
            _render_lscl_rvalue(content.needle, options=options, prefix=prefix)
            + " in "
            + _render_lscl_rvalue(
                content.haystack,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclNotIn):
        result = (
            _render_lscl_rvalue(content.needle, options=options, prefix=prefix)
            + " not in "
            + _render_lscl_rvalue(
                content.haystack,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclEqualTo):
        result = (
            _render_lscl_rvalue(content.first, options=options, prefix=prefix)
            + " == "
            + _render_lscl_rvalue(
                content.second,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclNotEqualTo):
        result = (
            _render_lscl_rvalue(content.first, options=options, prefix=prefix)
            + " != "
            + _render_lscl_rvalue(
                content.second,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclGreaterThanOrEqualTo):
        result = (
            _render_lscl_rvalue(content.first, options=options, prefix=prefix)
            + " >= "
            + _render_lscl_rvalue(
                content.second,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclLessThanOrEqualTo):
        result = (
            _render_lscl_rvalue(content.first, options=options, prefix=prefix)
            + " <= "
            + _render_lscl_rvalue(
                content.second,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclGreaterThan):
        result = (
            _render_lscl_rvalue(content.first, options=options, prefix=prefix)
            + " > "
            + _render_lscl_rvalue(
                content.second,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclLessThan):
        result = (
            _render_lscl_rvalue(content.first, options=options, prefix=prefix)
            + " < "
            + _render_lscl_rvalue(
                content.second,
                options=options,
                prefix=prefix,
            )
        )
    elif isinstance(content, LsclMatch):
        result = (
            _render_lscl_rvalue(content.value, options=options, prefix=prefix)
            + " =~ "
            + _render_lscl_pattern(content.pattern, options=options)
        )
    elif isinstance(content, LsclNotMatch):
        result = (
            _render_lscl_rvalue(content.value, options=options, prefix=prefix)
            + " !~ "
            + _render_lscl_pattern(content.pattern, options=options)
        )
    else:
        result = _render_lscl_rvalue(content, options=options, prefix=prefix)

    return result


def _render_lscl_content(
    content: LsclContent,
    /,
    *,
    options: _LsclRenderingOptions,
    prefix: str,
) -> str:
    """Render LSCL content.

    :param content: Content to render.
    :param options: Rendering options.
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
                        options=options,
                        prefix=prefix + "  ",
                    )
                    + f"{prefix}{'}'}\n"
                )
            else:
                rendered += f"{prefix}{element.name} {'{}'}\n"
        elif isinstance(element, LsclAttribute):
            rendered += f"{prefix}{element.name} => " + _render_lscl_data(
                element.content,
                options=options,
                prefix=prefix,
            )
        else:
            before_cond = prefix

            for cond, body in element.conditions:
                rendered += f"{before_cond}if " + _render_lscl_condition(
                    cond,
                    options=options,
                    prefix=prefix,
                )

                if body:
                    rendered += (
                        " {\n"
                        + _render_lscl_content(
                            body,
                            options=options,
                            prefix=prefix + "  ",
                        )
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
                            options=options,
                            prefix=prefix + "  ",
                        )
                        + prefix
                        + "}"
                    )
                else:
                    rendered += before_cond + "{}"

            rendered += "\n"

    return rendered


def render_as_lscl(
    content: LsclRenderable,
    /,
    *,
    escapes_supported: bool = False,
    field_reference_escape_style: Literal[
        "percent",
        "ampersand",
        "none",
    ] = "none",
) -> str:
    """Render content as LSCL.

    :param content: Content to render as LSCL.
    :param escapes_supported: Whether ``config.support_escapes`` is defined
        as true in the configuration of the target environment.
    :param field_reference_escape_style: The
        ``config.field_reference.escape_style`` value in the configuration
        of the target environment.
    :return: Rendered content.
    :raises StringRenderingError: A string could not be rendered due to
        invalid characters being present.
    :raises SelectorElementRenderingError: A selector could not be rendered
        due to invalid characters being in one of its elements.
    """
    options = _LsclRenderingOptions(
        escapes_supported=escapes_supported,
        field_reference_escape_style=field_reference_escape_style,
    )

    if isinstance(content, (str, bool, int, float, Decimal, LsclLiteral)):
        return _render_lscl_data(content, options=options, prefix="")

    if isinstance(content, (LsclSelector, LsclMethodCall)):
        return _render_lscl_rvalue(content, options=options, prefix="")

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
        return _render_lscl_condition(content, options=options, prefix="")

    if isinstance(content, (LsclBlock, LsclAttribute, LsclConditions)):
        return _render_lscl_content([content], options=options, prefix="")

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
        return _render_lscl_content(result.value, options=options, prefix="")

    return _render_lscl_data(result.value, options=options, prefix="")
