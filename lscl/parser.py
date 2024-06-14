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
"""LSCL parser definition.

This file bases itself on the `LSCL Grammar`_. All of the weirdness in the
parsing comes from said grammar, in order to reproduce the constraints of
the original language without adding too much.

.. _LSCL Grammar:
    https://github.com/elastic/logstash/blob/
    948a0edf1a58583d761f254d7e327ae02d18bc40/logstash-core/lib/logstash/
    compiler/lscl/lscl_grammar.treetop
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from enum import Enum
from itertools import chain
import re
from typing import Literal, Union

from pydantic import BaseModel

from .errors import DecodeError
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
from .utils import Runk


__all__ = ["parse_lscl"]


# ---
# Lexer definition.
# ---


_LSCL_TOKEN_PATTERN = re.compile(
    r"(#[^\n]*)|\[([^\[\],]+)\]"
    + r"|(=>|==|!=|<=|>=|<|>|=~|!~|\{|\}|\[|\]|\(|\)|!|,)"
    + r'|"((?:\\.|[^"])*)"|\'((?:\\.|[^\'])*)\'|/((?:\\.|[^/])*)/'
    + r"|(-?[0-9]+(?:\.[0-9]*)?)|([A-Za-z_][A-Za-z0-9_]+)|([A-Za-z0-9_-]+)",
    re.MULTILINE,
)
"""Pattern used by the lexer to match raw tokens from a string.

Case 1. Inline comment.
Case 2. Selector element.
    Note that this is NOT equivalent to [<bareword>], as the content of the
    selector element has access to a broader set of characters.
    However, just because a selector element is matched does not mean that
    the parsed result will be a selector, as it may as well be a list of
    one or more elements that will need to be re-parsed in the context of
    data parsing.

Case 3. Special symbols.
    In order: attribute marker (=>), equal to (==),
    different from (!=), less or equal to (<=), greater or equal to (>=),
    less than (<), greater than (>), match to regex (=~),
    negative match to regex (!~), left brace ({), right brace (}),
    left bracket ([), right bracket (]), left parenthesis ("("),
    right parenthesis (")"), exclamation mark (!), comma (,).

Case 4. Double quoted string.
Case 5. Single quoted string.
Case 6. Pattern.
Case 7. Number.
Case 8. Bareword.
    Barewords may also match special bareword-compatible tokens, including
    "if", "else", "in", "not", "and", "or", "xor", "nand".

Case 9. Barewords starting with numbers.
    This may be used as block names, e.g. "0hello".

NOTE: The original grammar checks for "newline or end of input", but we
actually check for the end of input in the lexer function directly.

NOTE: In case of barewords, the source language actually requires at least
two characters, but that may be an oversight that could be fixed later, so
we want to support one-character barewords.
"""

_LSCL_ESCAPE_PATTERN = re.compile(r"\\(.)")
"""Pattern used to unescape quoted strings."""


class LsclTokenType(str, Enum):
    """Token type."""

    END = "end"
    """End of input."""

    ATTR = "attr"
    """Attribute marker (=>)."""

    EQ = "eq"
    """Equal to (==)."""

    NEQ = "neq"
    """Different from (!=)."""

    LTE = "lte"
    """Less than or equal to (<=)."""

    LT = "lt"
    """Less than (<)."""

    GTE = "gte"
    """Greater than or equal to (>=)."""

    GT = "gt"
    """Greater than (>)."""

    MATCH = "match"
    """Match regex (=~)."""

    NMATCH = "nmatch"
    """Does not match regex (!~)."""

    LBRACE = "lbrace"
    """Left brace ({)."""

    RBRACE = "rbrace"
    """Right brace (})."""

    LBRK = "lbrk"
    """Left bracket ([)."""

    RBRK = "rbrk"
    """Right bracket (])."""

    LPAREN = "lparen"
    """Left parenthesis ("(")."""

    RPAREN = "rparen"
    """Right parenthesis (")")."""

    EXCL = "excl"
    """Exclamation mark ("!")."""

    COMMA = "comma"
    """Comma (,)."""

    SELECTOR_ELEMENT = "selector_element"
    """Selector, or single-element array."""

    DQUOT = "dquot"
    """Double-quoted string."""

    SQUOT = "squot"
    """Single-quoted string."""

    PATTERN = "pattern"
    """Regular expression pattern."""

    NUMBER = "number"
    """Number."""

    BAREWORD = "bareword"
    """Bareword."""

    DIGIT_BAREWORD = "digit_bareword"
    """Bareword starting with a digit."""

    IF = "if"
    """If clause."""

    ELSE = "else"
    """Else clause."""

    IN = "in"
    """In clause."""

    NOT = "not"
    """Not clause."""

    AND = "and"
    """And clause."""

    OR = "or"
    """Or clause."""

    XOR = "xor"
    """Exclusive or clause."""

    NAND = "nand"
    """Negative and clause."""


LsclSimpleTokenType = Literal[
    LsclTokenType.END,
    LsclTokenType.ATTR,
    LsclTokenType.EQ,
    LsclTokenType.NEQ,
    LsclTokenType.LTE,
    LsclTokenType.LT,
    LsclTokenType.GTE,
    LsclTokenType.GT,
    LsclTokenType.MATCH,
    LsclTokenType.NMATCH,
    LsclTokenType.LBRACE,
    LsclTokenType.RBRACE,
    LsclTokenType.LBRK,
    LsclTokenType.RBRK,
    LsclTokenType.LPAREN,
    LsclTokenType.RPAREN,
    LsclTokenType.EXCL,
    LsclTokenType.COMMA,
    LsclTokenType.IF,
    LsclTokenType.ELSE,
    LsclTokenType.IN,
    LsclTokenType.NOT,
    LsclTokenType.AND,
    LsclTokenType.OR,
    LsclTokenType.XOR,
    LsclTokenType.NAND,
]
"""Token types that can be represented using :py:class:`LsclSimpleToken`."""


class LsclSimpleToken(BaseModel):
    """LSCL token with no additional components."""

    type: LsclSimpleTokenType
    """Type of the token."""

    line: int = 1
    """Line at which the token starts, counting from 1."""

    column: int = 1
    """Column at which the token starts, counting from 1."""

    offset: int = 0
    """Offset at which the token starts, counting from 0."""


class LsclNumberToken(BaseModel):
    """LSCL token with a numeric value."""

    type: Literal[LsclTokenType.NUMBER]
    """Type of the token."""

    value: int | Decimal
    """Value as a number."""

    raw: str
    """Value as a string."""

    line: int = 1
    """Line at which the token starts, counting from 1."""

    column: int = 1
    """Column at which the token starts, counting from 1."""

    offset: int = 0
    """Offset at which the token starts, counting from 0."""


class LsclStringToken(BaseModel):
    """LSCL token with a string value."""

    type: Literal[
        LsclTokenType.SELECTOR_ELEMENT,
        LsclTokenType.DQUOT,
        LsclTokenType.SQUOT,
        LsclTokenType.PATTERN,
        LsclTokenType.BAREWORD,
        LsclTokenType.DIGIT_BAREWORD,
    ]
    """Type of the token."""

    value: str
    """Value as a string."""

    line: int = 1
    """Line at which the token starts, counting from 1."""

    column: int = 1
    """Column at which the token starts, counting from 1."""

    offset: int = 0
    """Offset at which the token starts, counting from 0."""


LsclToken = Union[LsclSimpleToken, LsclNumberToken, LsclStringToken]
"""LSCL token."""

_LSCL_SIMPLE_TOKEN_MAPPING: dict[str, LsclSimpleTokenType] = {
    "=>": LsclTokenType.ATTR,
    "==": LsclTokenType.EQ,
    "!=": LsclTokenType.NEQ,
    "<=": LsclTokenType.LTE,
    ">=": LsclTokenType.GTE,
    "<": LsclTokenType.LT,
    ">": LsclTokenType.GT,
    "=~": LsclTokenType.MATCH,
    "!~": LsclTokenType.NMATCH,
    "{": LsclTokenType.LBRACE,
    "}": LsclTokenType.RBRACE,
    "[": LsclTokenType.LBRK,
    "]": LsclTokenType.RBRK,
    "(": LsclTokenType.LPAREN,
    ")": LsclTokenType.RPAREN,
    "!": LsclTokenType.EXCL,
    ",": LsclTokenType.COMMA,
    "if": LsclTokenType.IF,
    "else": LsclTokenType.ELSE,
    "in": LsclTokenType.IN,
    "not": LsclTokenType.NOT,
    "and": LsclTokenType.AND,
    "or": LsclTokenType.OR,
    "xor": LsclTokenType.XOR,
    "nand": LsclTokenType.NAND,
}
"""Mapping from symbols and keywords to simple token types."""

_LSCL_ESCAPE_CHARACTERS = {
    '"': '"',
    "'": "'",
    "\\": "\\",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "0": "\0",
}
"""Valid characters for escape sequences.

See `string_escape`_ for the source of these characters.

.. _string_escape:
    https://github.com/elastic/logstash/blob/
    948a0edf1a58583d761f254d7e327ae02d18bc40/logstash-core/lib/
    logstash/config/string_escape.rb
"""


def _unescape_lscl_string(escaped_string: str, /) -> str:
    """Unescape an LSCL string.

    :param escaped_string: String with escape sequences.
    :return: Unescaped string.
    """
    return _LSCL_ESCAPE_PATTERN.sub(
        lambda match: _LSCL_ESCAPE_CHARACTERS.get(match[1], match[0]),
        escaped_string,
    )


def _unescape_lscl_pattern(escaped_pattern: str, /) -> str:
    """Unescape an LSCL pattern.

    :param escaped_pattern: Pattern with escape sequences.
    :return: Unescaped pattern.
    """
    return _LSCL_ESCAPE_PATTERN.sub(
        lambda m: "/" if m[1] == "/" else m[0],
        escaped_pattern,
    )


def parse_lscl_tokens(
    raw: str,
    /,
    *,
    runk: Runk | None = None,
) -> Iterator[LsclToken]:
    """Parse a string as a series of Logstash configuration tokens.

    This always emits a :py:class:`LsclSimpleToken` with
    type :py:attr:`LsclTokenType.END` after all others, so that
    the caller does not need to handle :py:exc:`StopIteration` as a "normal"
    exception.

    :param raw: Raw string from which to extract tokens.
    :param runk: Initial line, column and offset counter. This can be used to
        parse a substring starting after the content start.
    :return: Token iterator.
    :raises DecodeError: A decoding error has occurred.
    """
    if runk is None:
        runk = Runk()

    while True:
        # First, remove the leading whitespace, and check if there is still
        # contents in the string.
        stripped_raw = raw.lstrip()
        runk.count(raw[: len(raw) - len(stripped_raw)])
        if not stripped_raw:
            break

        raw = stripped_raw
        match = _LSCL_TOKEN_PATTERN.match(raw)
        if match is None:
            if len(raw) > 30:
                raw = raw[:27] + "..."

            raise DecodeError(
                f"Could not parse configuration starting from: {raw}",
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )

        if match[1] is not None:
            # Case 1. Inline comment.
            # We do not actually yield it, ignoring it is enough.
            pass
        elif match[2] is not None:
            # Case 2. Selector elements.
            # WARNING: We do *not* want to strip the obtained string here,
            # as it may produce invalid line, column and offset counts if
            # re-parsing the content in the context of data parsing.
            yield LsclStringToken(
                type=LsclTokenType.SELECTOR_ELEMENT,
                value=match[2],
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[3] is not None:
            # Case 3. Special symbols.
            try:
                yield LsclSimpleToken(
                    type=_LSCL_SIMPLE_TOKEN_MAPPING[match[3]],
                    line=runk.line,
                    column=runk.column,
                    offset=runk.offset,
                )
            except KeyError as exc:  # pragma: no cover
                raise NotImplementedError() from exc
        elif match[4] is not None:
            # Case 4. Double quoted string.
            yield LsclStringToken(
                type=LsclTokenType.DQUOT,
                value=_unescape_lscl_string(match[4]),
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[5] is not None:
            # Case 5. Single quoted string.
            yield LsclStringToken(
                type=LsclTokenType.SQUOT,
                value=_unescape_lscl_string(match[5]),
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[6] is not None:
            # Case 6. Pattern.
            yield LsclStringToken(
                type=LsclTokenType.PATTERN,
                value=_unescape_lscl_pattern(match[6]),
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[7] is not None:
            # Case 7. Number.
            raw_number = match[7]
            if "." in raw_number:
                number: int | Decimal = Decimal(raw_number)
            else:
                number = int(raw_number)

            yield LsclNumberToken(
                type=LsclTokenType.NUMBER,
                value=number,
                raw=raw_number,
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[8] is not None:
            # Case 8. Bareword.
            bareword = match[8]
            try:
                yield LsclSimpleToken(
                    type=_LSCL_SIMPLE_TOKEN_MAPPING[bareword],
                    line=runk.line,
                    column=runk.column,
                    offset=runk.offset,
                )
            except KeyError:
                yield LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value=bareword,
                    line=runk.line,
                    column=runk.column,
                    offset=runk.offset,
                )
        elif match[9] is not None:
            yield LsclStringToken(
                type=LsclTokenType.DIGIT_BAREWORD,
                value=match[9],
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        else:  # pragma: no cover
            raise NotImplementedError()

        runk.count(match[0])
        raw = raw[match.end() :]

    yield LsclSimpleToken(
        type=LsclTokenType.END,
        line=runk.line,
        column=runk.column,
        offset=runk.offset,
    )


# ---
# Parser.
# ---


class _LsclParsingOptions(BaseModel):
    """Parsing options for LSCL."""

    accept_trailing_commas: bool
    """Whether to accept or refuse trailing commas.

    This is used when parsing arrays (lists), hash tables (dicts) and
    method calls. Logstash does not support those by default, but this
    option can be used to make our parser more fault-tolerant.
    """


class UnexpectedLsclToken(DecodeError):
    """An unexpected token was obtained."""

    token: LsclToken
    """Token detail."""

    def __init__(self, token: LsclToken, /) -> None:
        super().__init__(
            f"Unexpected token {token.type.name} at line {token.line}, "
            + f"column {token.column}",
            line=token.line,
            column=token.column,
            offset=token.offset,
        )
        self.token = token


def _parse_lscl_data(
    token_iter: Iterator[LsclToken],
    /,
    *,
    options: _LsclParsingOptions,
) -> LsclData:
    """Parse LSCL data.

    Data here is equivalent to "values" in the original grammar.

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :return: Parsed data.
    """
    # TODO: We don't support plugins yet, as named blocks. Maybe it should
    # be supported? Not sure...
    token = next(token_iter)
    if token.type in (
        LsclTokenType.BAREWORD,
        LsclTokenType.SQUOT,
        LsclTokenType.DQUOT,
        LsclTokenType.NUMBER,
    ):
        return token.value

    if token.type == LsclTokenType.SELECTOR_ELEMENT:
        # The element is a single-element list matched as a selector.
        # We actually need to re-parse the tokens within the selector.
        value = _parse_lscl_data(
            parse_lscl_tokens(
                token.value,
                runk=Runk(
                    line=token.line,
                    column=token.column + 1,  # Ignore initial '['.
                    offset=token.offset + 1,  # Ignore initial '['.
                ),
            ),
            options=options,
        )

        return [value]

    if token.type == LsclTokenType.LBRK:
        # The element is a list.
        lst: list[LsclData] = []

        for i, token in enumerate(token_iter):
            if token.type == LsclTokenType.RBRK:
                if not options.accept_trailing_commas and i > 0:
                    raise DecodeError(
                        "Trailing commas have been disabled.",
                        line=token.line,
                        column=token.column,
                        offset=token.offset,
                    )

                break

            # We need to reinsert the token into the iterator, then parse
            # the value here.
            value = _parse_lscl_data(
                chain(iter([token]), token_iter),
                options=options,
            )
            lst.append(value)

            token = next(token_iter)
            if token.type == LsclTokenType.RBRK:
                break

            if token.type == LsclTokenType.COMMA:
                continue

            raise UnexpectedLsclToken(token)

        return lst

    if token.type == LsclTokenType.LBRACE:
        # The element is a dictionary.
        dct: dict[str, LsclData] = {}

        for token in token_iter:
            if token.type == LsclTokenType.RBRACE:
                break

            if not isinstance(token, LsclStringToken):
                raise UnexpectedLsclToken(token)

            key = token.value

            token = next(token_iter)
            if token.type != LsclTokenType.ATTR:
                raise UnexpectedLsclToken(token)

            value = _parse_lscl_data(token_iter, options=options)

            # NOTE: If the key already exists, we just override the value.
            # This may be an undesirable behaviour in the future?
            dct[key] = value

        return dct

    raise UnexpectedLsclToken(token)


def _parse_lscl_rvalue(
    token_iter: Iterator[LsclToken],
    /,
    *,
    options: _LsclParsingOptions,
) -> tuple[LsclRValue, LsclToken]:
    """Parse an LSCL right-value within the context of a condition.

    NOTE: This function does not, at root, call :py:func:`_parse_lscl_data`
    because of differences on processing of barewords (string or method call)
    and selector elements (selector or one-element array).

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :return: Parsed condition, and first token after the condition.
    """
    token = next(token_iter)
    if token.type in (
        LsclTokenType.SQUOT,
        LsclTokenType.DQUOT,
        LsclTokenType.PATTERN,
        LsclTokenType.NUMBER,
    ):
        return token.value, next(token_iter)

    if token.type == LsclTokenType.SELECTOR_ELEMENT:
        selectors = [token.value]
        for token in token_iter:
            if token.type != LsclTokenType.SELECTOR_ELEMENT:
                break

            selectors.append(token.value)

        return LsclSelector(names=selectors), token

    if token.type == LsclTokenType.LBRK:
        # The element is a list.
        lst: list[LsclData] = []

        for i, token in enumerate(token_iter):
            if token.type == LsclTokenType.RBRK:
                if not options.accept_trailing_commas and i > 0:
                    raise DecodeError(
                        "Trailing commas have been disabled.",
                        line=token.line,
                        column=token.column,
                        offset=token.offset,
                    )

                break

            # We need to reinsert the token into the iterator, then parse
            # the value here.
            value = _parse_lscl_data(
                chain(iter([token]), token_iter),
                options=options,
            )
            lst.append(value)

            token = next(token_iter)
            if token.type == LsclTokenType.RBRK:
                break

            if token.type == LsclTokenType.COMMA:
                continue

            raise UnexpectedLsclToken(token)

        return lst, next(token_iter)

    # From here, the rvalue is considered to be a method call, as barewords
    # cannot be used as strings.
    if token.type != LsclTokenType.BAREWORD:
        raise UnexpectedLsclToken(token)

    method = token.value

    token = next(token_iter)
    if token.type != LsclTokenType.LPAREN:
        raise UnexpectedLsclToken(token)

    params: list[LsclRValue] = []
    for i, token in enumerate(token_iter):
        if token.type == LsclTokenType.RPAREN:
            if not options.accept_trailing_commas and i > 0:
                raise DecodeError(
                    "Trailing commas have been disabled.",
                    line=token.line,
                    column=token.column,
                    offset=token.offset,
                )
            break

        rvalue, token = _parse_lscl_rvalue(
            chain(iter((token,)), token_iter),
            options=options,
        )
        params.append(rvalue)

        if token.type == LsclTokenType.RPAREN:
            break

        if token.type == LsclTokenType.COMMA:
            continue

        raise UnexpectedLsclToken(token)

    return LsclMethodCall(name=method, params=params)


def _parse_lscl_condition(
    token_iter: Iterator[LsclToken],
    /,
    *,
    options: _LsclParsingOptions,
    end_token_type: LsclTokenType = LsclTokenType.RPAREN,
) -> LsclCondition:
    """Parse an LSCL condition.

    Note that there is no boolean operator precedence.

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :param end_token_type: Token type that ends
    :return: Parsed condition, and first token after the condition.
    """
    current: LsclAnd | LsclNand | LsclOr | LsclXor | None = None
    new: LsclCondition

    while True:
        token = next(token_iter)

        # Parse the "expression" (condition element) first.
        if token.type == LsclTokenType.EXCL:
            # "! <selector>" or "!(<condition>)" (not, using token EXCL)
            token = next(token_iter)
            if token.type == LsclTokenType.LPAREN:
                new = LsclNot(
                    condition=_parse_lscl_condition(
                        token_iter,
                        options=options,
                    ),
                )
                token = next(token_iter)
            elif token.type == LsclTokenType.SELECTOR_ELEMENT:
                selectors = [token.value]
                for token in token_iter:
                    if token.type != LsclTokenType.SELECTOR_ELEMENT:
                        break

                    selectors.append(token.value)

                new = LsclNot(condition=LsclSelector(names=selectors))
            else:
                raise UnexpectedLsclToken(token)
        elif token.type == LsclTokenType.LPAREN:
            # "(<condition>)" (nested condition)
            new = _parse_lscl_condition(token_iter, options=options)
            token = next(token_iter)
        else:
            first, token = _parse_lscl_rvalue(
                chain(iter((token,)), token_iter),
                options=options,
            )

            if token.type == LsclTokenType.IN:
                # "<rvalue> in <rvalue>" (in)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclIn(needle=first, haystack=second)
            elif token.type == LsclTokenType.NOT:
                # "<rvalue> not in <rvalue>" (not in)
                token = next(token_iter)
                if token.type != LsclTokenType.IN:
                    raise UnexpectedLsclToken(token)

                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclNotIn(needle=first, haystack=second)
            elif token.type == LsclTokenType.EQ:
                # "<rvalue> == <rvalue>" (eq)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclEqualTo(first=first, second=second)
            elif token.type == LsclTokenType.NEQ:
                # "<rvalue> != <rvalue>" (neq)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclNotEqualTo(first=first, second=second)
            elif token.type == LsclTokenType.LTE:
                # "<rvalue> <= <rvalue>" (lte)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclLessThanOrEqualTo(first=first, second=second)
            elif token.type == LsclTokenType.GTE:
                # "<rvalue> >= <rvalue>" (gte)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclGreaterThanOrEqualTo(first=first, second=second)
            elif token.type == LsclTokenType.LT:
                # "<rvalue> < <rvalue>" (lt)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclLessThan(first=first, second=second)
            elif token.type == LsclTokenType.GT:
                # "<rvalue> > <rvalue>" (gt)
                second, token = _parse_lscl_rvalue(token_iter, options=options)
                new = LsclGreaterThan(first=first, second=second)
            elif token.type == LsclTokenType.MATCH:
                # "<rvalue> =~ <squot>", "<rvalue> =~ <dquot>",
                # "<rvalue> =~ <pattern>" (match)
                token = next(token_iter)
                if token.type not in (
                    LsclTokenType.SQUOT,
                    LsclTokenType.DQUOT,
                    LsclTokenType.PATTERN,
                ):
                    raise UnexpectedLsclToken(token)

                new = LsclMatch(value=first, pattern=token.value)
                token = next(token_iter)
            elif token.type == LsclTokenType.NMATCH:
                # "<rvalue> !~ <squot>", "<rvalue> !~ <dquot>",
                # "<rvalue> !~ <pattern>" (nmatch)
                token = next(token_iter)
                if token.type not in (
                    LsclTokenType.SQUOT,
                    LsclTokenType.DQUOT,
                    LsclTokenType.PATTERN,
                ):
                    raise UnexpectedLsclToken(token)

                new = LsclNotMatch(value=first, pattern=token.value)
                token = next(token_iter)
            else:
                # "<rvalue>" (rvalue)
                new = first

        # Find out what to do with the new condition.
        if current is not None:
            # NOTE: It is possible for both current and new to be the same
            # type, e.g. ``LsclAnd``. In this case, it would be possible to
            # extend the original conditions instead of adding a new
            # sublevel, but we prefer not to, in order to preserve the
            # meaning of the original.
            new = current
            current.conditions.append(new)

        # Check the next token, to check if it's either the end, or a boolean
        # operator.
        if token.type == end_token_type:
            break

        if token.type == LsclTokenType.AND and not isinstance(
            current,
            LsclAnd,
        ):
            current = LsclAnd(conditions=[new])
        elif token.type == LsclTokenType.OR and not isinstance(
            current,
            LsclOr,
        ):
            current = LsclOr(conditions=[new])
        elif token.type == LsclTokenType.XOR and not isinstance(
            current,
            LsclXor,
        ):
            current = LsclXor(conditions=[new])
        elif token.type == LsclTokenType.NAND and not isinstance(
            current,
            LsclNand,
        ):
            current = LsclNand(conditions=[new])
        else:
            raise UnexpectedLsclToken(token)

    return new


def _parse_lscl_content(
    token_iter: Iterator[LsclToken],
    /,
    *,
    options: _LsclParsingOptions,
    end_token_type: LsclTokenType = LsclTokenType.RBRACE,
) -> LsclContent:
    """Parse an LSCL block.

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :param end_token_type: Type of the ending token for the block.
    :return: Parsed block.
    """
    content: LsclContent = []

    # Parse the first token.
    # This is not done at the beginning of the loop, because in case of
    # conditions, we need to peek at the next token.
    token = next(token_iter)

    while token.type != end_token_type:
        # Every possibility starts with a name.
        if token.type == LsclTokenType.IF:
            # We have an "if <condition> {" structure.
            initial_condition = _parse_lscl_condition(
                token_iter,
                options=options,
                end_token_type=LsclTokenType.LBRACE,
            )

            conditions: list[tuple[LsclCondition, LsclContent]] = [
                (
                    initial_condition,
                    _parse_lscl_content(token_iter, options=options),
                ),
            ]
            default_content: LsclContent | None = None

            # We may have "else" blocks here, which we need to evaluate.
            while True:
                token = next(token_iter)
                if token.type != LsclTokenType.ELSE:
                    # The token is the beginning of a new element within the
                    # currently parsed block, or the block sentinel.
                    break

                # The next token is either an "if" or a left brace.
                token = next(token_iter)
                if token.type == LsclTokenType.LBRACE:
                    default_content = _parse_lscl_content(
                        token_iter,
                        options=options,
                    )

                    # Since the 'else' has marked an explicit end to the
                    # branching, we must get the next token manually,
                    # instead of automatically as above.
                    token = next(token_iter)
                    break

                if token.type == LsclTokenType.IF:
                    # "else if <condition> {" structure.
                    other_condition = _parse_lscl_condition(
                        token_iter,
                        options=options,
                        end_token_type=LsclTokenType.LBRACE,
                    )

                    conditions.append(
                        (
                            other_condition,
                            _parse_lscl_content(token_iter, options=options),
                        ),
                    )
                else:
                    raise UnexpectedLsclToken(token)

            content.append(
                LsclConditions(
                    conditions=conditions,
                    default=default_content,
                ),
            )
            continue

        if token.type == LsclTokenType.NUMBER:
            name = token.raw
        elif token.type in (
            LsclTokenType.BAREWORD,
            LsclTokenType.DIGIT_BAREWORD,
        ):
            name = token.value
        else:
            raise UnexpectedLsclToken(token)

        op_token = next(token_iter)
        if op_token.type == LsclTokenType.LBRACE:
            # We have a "bareword {" structure, introducing a block.
            content.append(
                LsclBlock(
                    name=name,
                    content=_parse_lscl_content(token_iter, options=options),
                ),
            )
        elif op_token.type == LsclTokenType.ATTR:
            # We have a "bareword =>" structure, introducing an
            # assignment to data.
            content.append(
                LsclAttribute(
                    name=name,
                    content=_parse_lscl_data(token_iter, options=options),
                ),
            )
        else:
            raise UnexpectedLsclToken(op_token)

        token = next(token_iter)

    return content


def parse_lscl(
    raw: str,
    /,
    *,
    accept_trailing_commas: bool = False,
) -> LsclContent:
    """Parse a string as an Logstash Configuration Language block.

    :param raw: Text to parse as an LSCL block.
    :param accept_trailing_commas: Whether to accept trailing commas in the
        input.
    :return: Obtained blocks, attributes and conditions.
    :raises DecodeError: A decode error.
    """
    token_iter = iter(parse_lscl_tokens(raw))
    return _parse_lscl_content(
        token_iter,
        options=_LsclParsingOptions(
            accept_trailing_commas=accept_trailing_commas,
        ),
        end_token_type=LsclTokenType.END,
    )
