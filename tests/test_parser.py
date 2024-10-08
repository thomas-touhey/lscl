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
"""Tests for the ``lscl.parser`` module."""

from __future__ import annotations

from decimal import Decimal
from itertools import zip_longest
from pathlib import Path

import pytest

from lscl.errors import DecodeError
from lscl.lang import (
    LsclAnd,
    LsclAttribute,
    LsclBlock,
    LsclConditions,
    LsclContent,
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
    LsclSelector,
    LsclXor,
)
from lscl.parser import (
    LsclNumberToken,
    LsclSimpleToken,
    LsclStringToken,
    LsclToken,
    LsclTokenType,
    parse_lscl,
    parse_lscl_tokens,
)


CONFIGS_PATH = Path(__file__).parent / "configs"


@pytest.mark.parametrize(
    "raw,tokens",
    (
        (
            "0auth {}",
            [
                LsclStringToken(
                    type=LsclTokenType.DIGIT_BAREWORD,
                    value="0auth",
                ),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ],
        ),
        (
            "if hello('world', [a], 5) == 0 {}",
            [
                LsclSimpleToken(type=LsclTokenType.IF),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="hello"),
                LsclSimpleToken(type=LsclTokenType.LPAREN),
                LsclStringToken(type=LsclTokenType.SQUOT, value="world"),
                LsclSimpleToken(type=LsclTokenType.COMMA),
                LsclStringToken(
                    type=LsclTokenType.SELECTOR_ELEMENT,
                    value="a",
                ),
                LsclSimpleToken(type=LsclTokenType.COMMA),
                LsclNumberToken(type=LsclTokenType.NUMBER, raw="5", value=5),
                LsclSimpleToken(type=LsclTokenType.RPAREN),
                LsclSimpleToken(type=LsclTokenType.EQ),
                LsclNumberToken(type=LsclTokenType.NUMBER, raw="0", value=0),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ],
        ),
    ),
)
def test_lex(raw: str, tokens: LsclToken) -> None:
    """Test the lexer."""
    for i, (obtained_token, expected_token) in enumerate(
        zip_longest(
            parse_lscl_tokens(raw),
            [*tokens, LsclSimpleToken(type=LsclTokenType.END)],
        ),
    ):
        # Update the obtained token for comparison.
        expected_token = expected_token.model_copy(
            update={
                "line": obtained_token.line,
                "column": obtained_token.column,
                "offset": obtained_token.offset,
            },
        )

        assert expected_token == obtained_token, (
            f"At index {i}, obtained {obtained_token} does not match "
            + f"expected {expected_token}"
        )


@pytest.mark.parametrize(
    "path,tokens",
    (
        # Examples taken from the Logstash config examples:
        # https://www.elastic.co/guide/en/logstash/current/config-examples.html
        (
            "example1.txt",
            (
                LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value="input",
                ),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value="stdin",
                ),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ),
        ),
        (
            "example2.txt",
            (
                LsclStringToken(type=LsclTokenType.BAREWORD, value="filter"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="grok"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="match"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.DQUOT, value="message"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclStringToken(
                    type=LsclTokenType.DQUOT,
                    value="%{COMBINEDAPACHELOG}",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="date"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="match"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclSimpleToken(type=LsclTokenType.LBRK),
                LsclStringToken(type=LsclTokenType.DQUOT, value="timestamp"),
                LsclSimpleToken(type=LsclTokenType.COMMA),
                LsclStringToken(
                    type=LsclTokenType.DQUOT,
                    value="dd/MMM/yyyy:HH:mm:ss Z",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRK),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ),
        ),
        (
            "example3.txt",
            (
                LsclStringToken(type=LsclTokenType.BAREWORD, value="output"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value="elasticsearch",
                ),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="hosts"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclStringToken(
                    type=LsclTokenType.SELECTOR_ELEMENT,
                    value='"localhost:9200"',
                ),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="stdout"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="codec"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value="rubydebug",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ),
        ),
        (
            "example4.txt",
            (
                LsclStringToken(type=LsclTokenType.BAREWORD, value="filter"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclSimpleToken(type=LsclTokenType.IF),
                LsclStringToken(
                    type=LsclTokenType.SELECTOR_ELEMENT,
                    value="path",
                ),
                LsclSimpleToken(type=LsclTokenType.MATCH),
                LsclStringToken(type=LsclTokenType.DQUOT, value="access"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="mutate"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="replace"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.DQUOT, value="type"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclStringToken(
                    type=LsclTokenType.DQUOT,
                    value="apache_access",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="grok"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="match"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.DQUOT, value="message"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclStringToken(
                    type=LsclTokenType.DQUOT,
                    value="%{COMBINEDAPACHELOG}",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="date"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="match"),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclSimpleToken(type=LsclTokenType.LBRK),
                LsclStringToken(type=LsclTokenType.DQUOT, value="timestamp"),
                LsclSimpleToken(type=LsclTokenType.COMMA),
                LsclStringToken(
                    type=LsclTokenType.DQUOT,
                    value="dd/MMM/yyyy:HH:mm:ss Z",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRK),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ),
        ),
        (
            "example5.txt",
            (
                LsclStringToken(type=LsclTokenType.BAREWORD, value="output"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclSimpleToken(type=LsclTokenType.IF),
                LsclStringToken(
                    type=LsclTokenType.SELECTOR_ELEMENT,
                    value="type",
                ),
                LsclSimpleToken(type=LsclTokenType.EQ),
                LsclStringToken(type=LsclTokenType.DQUOT, value="apache"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclSimpleToken(type=LsclTokenType.IF),
                LsclStringToken(
                    type=LsclTokenType.SELECTOR_ELEMENT,
                    value="status",
                ),
                LsclSimpleToken(type=LsclTokenType.MATCH),
                LsclStringToken(type=LsclTokenType.PATTERN, value=r"^5\d\d"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="nagios"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                # (ellipsis)
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.ELSE),
                LsclSimpleToken(type=LsclTokenType.IF),
                LsclStringToken(
                    type=LsclTokenType.SELECTOR_ELEMENT,
                    value="status",
                ),
                LsclSimpleToken(type=LsclTokenType.MATCH),
                LsclStringToken(type=LsclTokenType.PATTERN, value=r"^4\d\d"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value="elasticsearch",
                ),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                # (ellipsis)
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclStringToken(type=LsclTokenType.BAREWORD, value="statsd"),
                LsclSimpleToken(type=LsclTokenType.LBRACE),
                LsclStringToken(
                    type=LsclTokenType.BAREWORD,
                    value="increment",
                ),
                LsclSimpleToken(type=LsclTokenType.ATTR),
                LsclStringToken(
                    type=LsclTokenType.DQUOT,
                    value="apache.%{status}",
                ),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
                LsclSimpleToken(type=LsclTokenType.RBRACE),
            ),
        ),
    ),
)
def test_lex_file(path: str, tokens: LsclToken) -> None:
    """Test the lexer."""
    with open(CONFIGS_PATH / path) as fp:
        raw = fp.read()

    for i, (obtained_token, expected_token) in enumerate(
        zip_longest(
            parse_lscl_tokens(raw),
            [*tokens, LsclSimpleToken(type=LsclTokenType.END)],
        ),
    ):
        # Update the obtained token for comparison.
        expected_token = expected_token.model_copy(
            update={
                "line": obtained_token.line,
                "column": obtained_token.column,
                "offset": obtained_token.offset,
            },
        )

        assert expected_token == obtained_token, (
            f"At index {i}, obtained {obtained_token} does not match "
            + f"expected {expected_token}"
        )


@pytest.mark.parametrize("raw", ("@" + "." * 30, "'"))
def test_lex_invalid(raw: str) -> None:
    """Check that invalid tokens are correctly detected."""
    with pytest.raises(DecodeError):
        for _ in parse_lscl_tokens(raw):
            pass


@pytest.mark.parametrize(
    "raw,content",
    (
        (
            "if [world %%2B&&#45;] == 5 {}",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclEqualTo(
                                first=LsclSelector(names=["world %%2B&&#45;"]),
                                second=5,
                            ),
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            "0 { a => 05.2 }",
            [
                LsclBlock(
                    name="0",
                    content=[LsclAttribute(name="a", content=Decimal("5.2"))],
                ),
            ],
        ),
        (
            "hello => 'world'",
            [LsclAttribute(name="hello", content="world")],
        ),
        (
            "hello => -2",
            [LsclAttribute(name="hello", content=-2)],
        ),
        (
            "hello => 0.52",
            [LsclAttribute(name="hello", content=Decimal(".52"))],
        ),
        (
            "0auth {}",
            [LsclBlock(name="0auth", content=[])],
        ),
        (
            "hello => []",
            [LsclAttribute(name="hello", content=[])],
        ),
        (
            "if [a][b] == [1, 2] {}",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclEqualTo(
                                first=LsclSelector(names=["a", "b"]),
                                second=[1, 2],
                            ),
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            "if hello([a], 'world', 5) == 0 {}",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclEqualTo(
                                first=LsclMethodCall(
                                    name="hello",
                                    params=[
                                        LsclSelector(names=["a"]),
                                        "world",
                                        5,
                                    ],
                                ),
                                second=0,
                            ),
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            "if !(1 and 2 or 3 xor 4 nand 5) {}",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclNot(
                                condition=LsclNand(
                                    conditions=[
                                        LsclXor(
                                            conditions=[
                                                LsclOr(
                                                    conditions=[
                                                        LsclAnd(
                                                            conditions=[1, 2],
                                                        ),
                                                        3,
                                                    ],
                                                ),
                                                4,
                                            ],
                                        ),
                                        5,
                                    ],
                                ),
                            ),
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            "if (![a][b]) {}",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclNot(condition=LsclSelector(names=["a", "b"])),
                            [],
                        ),
                    ],
                ),
            ],
        ),
        (
            "if [a] in [] or [b] not in [] or [c] != 1 { 0a {\n} }",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclOr(
                                conditions=[
                                    LsclIn(
                                        needle=LsclSelector(
                                            names=["a"],
                                        ),
                                        haystack=[],
                                    ),
                                    LsclNotIn(
                                        needle=LsclSelector(
                                            names=["b"],
                                        ),
                                        haystack=[],
                                    ),
                                    LsclNotEqualTo(
                                        first=LsclSelector(
                                            names=["c"],
                                        ),
                                        second=1,
                                    ),
                                ],
                            ),
                            [LsclBlock(name="0a")],
                        ),
                    ],
                ),
            ],
        ),
        (
            "if 1 <= 2 or 2 >= 1 or 1 < 2 or 2 > 1 or 'x' !~ /[a-z]+/ "
            + "or 'y' !~ \"[b-d]\" { a => b }",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclOr(
                                conditions=[
                                    LsclLessThanOrEqualTo(first=1, second=2),
                                    LsclGreaterThanOrEqualTo(
                                        first=2,
                                        second=1,
                                    ),
                                    LsclLessThan(first=1, second=2),
                                    LsclGreaterThan(first=2, second=1),
                                    LsclNotMatch(value="x", pattern=r"[a-z]+"),
                                    LsclNotMatch(value="y", pattern=r"[b-d]"),
                                ],
                            ),
                            [LsclAttribute(name="a", content="b")],
                        ),
                    ],
                ),
            ],
        ),
    ),
)
def test_parse(raw: str, content: LsclContent) -> None:
    """Check that we can parse simple content directly."""
    assert parse_lscl(raw) == content


def test_parse_with_percent_field_reference_encoding() -> None:
    """Check that parsing with percent field reference encoding works."""
    assert parse_lscl(
        "if [world %%2B&&#45;] == 5 {}",
        field_reference_escape_style="percent",
    ) == [
        LsclConditions(
            conditions=[
                (
                    LsclEqualTo(
                        first=LsclSelector(names=["world %+&&#45;"]),
                        second=5,
                    ),
                    [],
                ),
            ],
        ),
    ]


def test_parse_with_ampersand_field_reference_encoding() -> None:
    """Check that parsing with & field reference encoding works."""
    assert parse_lscl(
        "if [world %%2B&&#45;] == 5 {}",
        field_reference_escape_style="ampersand",
    ) == [
        LsclConditions(
            conditions=[
                (
                    LsclEqualTo(
                        first=LsclSelector(names=["world %%2B&-"]),
                        second=5,
                    ),
                    [],
                ),
            ],
        ),
    ]


@pytest.mark.parametrize(
    "path,content",
    (
        # Examples taken from the Logstash config examples:
        # https://www.elastic.co/guide/en/logstash/current/config-examples.html
        (
            "example1.txt",
            [
                LsclBlock(
                    name="input",
                    content=[
                        LsclBlock(name="stdin"),
                    ],
                ),
            ],
        ),
        (
            "example2.txt",
            [
                LsclBlock(
                    name="filter",
                    content=[
                        LsclBlock(
                            name="grok",
                            content=[
                                LsclAttribute(
                                    name="match",
                                    content={
                                        "message": "%{COMBINEDAPACHELOG}",
                                    },
                                ),
                            ],
                        ),
                        LsclBlock(
                            name="date",
                            content=[
                                LsclAttribute(
                                    name="match",
                                    content=[
                                        "timestamp",
                                        "dd/MMM/yyyy:HH:mm:ss Z",
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            "example3.txt",
            [
                LsclBlock(
                    name="output",
                    content=[
                        LsclBlock(
                            name="elasticsearch",
                            content=[
                                LsclAttribute(
                                    name="hosts",
                                    content=["localhost:9200"],
                                ),
                            ],
                        ),
                        LsclBlock(
                            name="stdout",
                            content=[
                                LsclAttribute(
                                    name="codec",
                                    content="rubydebug",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            "example4.txt",
            [
                LsclBlock(
                    name="filter",
                    content=[
                        LsclConditions(
                            conditions=[
                                (
                                    LsclMatch(
                                        value=LsclSelector(names=["path"]),
                                        pattern=r"access",
                                    ),
                                    [
                                        LsclBlock(
                                            name="mutate",
                                            content=[
                                                LsclAttribute(
                                                    name="replace",
                                                    content={
                                                        "type": "apache_"
                                                        + "access",
                                                    },
                                                ),
                                            ],
                                        ),
                                        LsclBlock(
                                            name="grok",
                                            content=[
                                                LsclAttribute(
                                                    name="match",
                                                    content={
                                                        "message": "%{COMBINED"
                                                        + "APACHELOG}",
                                                    },
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        LsclBlock(
                            name="date",
                            content=[
                                LsclAttribute(
                                    name="match",
                                    content=[
                                        "timestamp",
                                        "dd/MMM/yyyy:HH:mm:ss Z",
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            "example5.txt",
            [
                LsclBlock(
                    name="output",
                    content=[
                        LsclConditions(
                            conditions=[
                                (
                                    LsclEqualTo(
                                        first=LsclSelector(names=["type"]),
                                        second="apache",
                                    ),
                                    [
                                        LsclConditions(
                                            conditions=[
                                                (
                                                    LsclMatch(
                                                        value=LsclSelector(
                                                            names=["status"],
                                                        ),
                                                        pattern=r"^5\d\d",
                                                    ),
                                                    [LsclBlock(name="nagios")],
                                                ),
                                                (
                                                    LsclMatch(
                                                        value=LsclSelector(
                                                            names=[
                                                                "status",
                                                            ],
                                                        ),
                                                        pattern=r"^4\d\d",
                                                    ),
                                                    [
                                                        LsclBlock(
                                                            name="elastic"
                                                            + "search",
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        LsclBlock(
                                            name="statsd",
                                            content=[
                                                LsclAttribute(
                                                    name="increment",
                                                    content="apache.%{status}",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            "example6.txt",
            [
                LsclBlock(
                    name="filter",
                    content=[
                        LsclConditions(
                            conditions=[
                                (
                                    LsclEqualTo(
                                        first=LsclSelector(names=["type"]),
                                        second="syslog",
                                    ),
                                    [
                                        LsclBlock(
                                            name="grok",
                                            content=[
                                                LsclAttribute(
                                                    name="match",
                                                    content={
                                                        "message": "%{SYSLOGTI"
                                                        + "MESTAMP:syslog_time"
                                                        + "stamp} %{SYSLOGHOST"
                                                        + ":syslog_hostname} %"
                                                        + "{DATA:syslog_progra"
                                                        + "m}(?:\\[%{POSINT:s"
                                                        + "yslog_pid}\\])?: %{"
                                                        + "GREEDYDATA:syslog_m"
                                                        + "essage}",
                                                    },
                                                ),
                                                LsclAttribute(
                                                    name="add_field",
                                                    content=[
                                                        "received_at",
                                                        "%{@timestamp}",
                                                    ],
                                                ),
                                                LsclAttribute(
                                                    name="add_field",
                                                    content=[
                                                        "received_from",
                                                        "%{host}",
                                                    ],
                                                ),
                                            ],
                                        ),
                                        LsclBlock(
                                            name="date",
                                            content=[
                                                LsclAttribute(
                                                    name="match",
                                                    content=[
                                                        "syslog_timestamp",
                                                        "MMM  d HH:mm:ss",
                                                        "MMM dd HH:mm:ss",
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            "else.txt",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclEqualTo(
                                first=LsclSelector(names=["x"]),
                                second=5,
                            ),
                            [LsclBlock(name="a")],
                        ),
                    ],
                    default=[LsclBlock(name="b")],
                ),
            ],
        ),
    ),
)
def test_parse_file(path: str, content: LsclContent) -> None:
    """Test that parsing works correctly."""
    with open(CONFIGS_PATH / path) as fp:
        raw = fp.read()

    assert parse_lscl(raw, support_escapes=True) == content


@pytest.mark.parametrize(
    "raw,expected",
    (
        ("hello => [1,]", [LsclAttribute(name="hello", content=[1])]),
        (
            "if [1, 2,] == [1, 2] {}",
            [
                LsclConditions(
                    conditions=[
                        (LsclEqualTo(first=[1, 2], second=[1, 2]), []),
                    ],
                ),
            ],
        ),
        (
            "if hello('x',) == 0 {}",
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclEqualTo(
                                first=LsclMethodCall(
                                    name="hello",
                                    params=["x"],
                                ),
                                second=0,
                            ),
                            [],
                        ),
                    ],
                ),
            ],
        ),
    ),
)
def test_parse_with_trailing_commas(raw: str, expected: LsclContent) -> None:
    """Check that trailing commas can be accepted."""
    assert parse_lscl(raw, accept_trailing_commas=True) == expected


@pytest.mark.parametrize(
    "raw",
    (
        "{",
        "hello => [1,]",
        "hello => [1",
        "hello => {",
        "hello => {hello world",
        "hello => 0notABareword",
        "if [x] == [1,] {}",
        "if [x] == [1",
        "if {",
        "if hello {}",
        "if hello(2",
        "if hello('x',) == 0 {}",
        "if ! hello {}",
        "if [x] in",
        "if [x] =~",
        "if [x] !~",
        "if [x] }",
        "if [x] not",
        "if 1 {} else else {}",
        "a { b",
    ),
)
def test_parse_invalid(raw: str) -> None:
    """Check that invalid syntax are detected correctly."""
    with pytest.raises(DecodeError):
        parse_lscl(raw)
