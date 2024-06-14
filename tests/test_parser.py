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

from itertools import zip_longest
from pathlib import Path

import pytest

from lscl.lang import (
    LsclConditions,
    LsclContent,
    LsclEqualTo,
    LsclMatch,
    LsclBlock,
    LsclAttribute,
    LsclSelector,
)
from lscl.parser import (
    LsclSimpleToken,
    LsclStringToken,
    LsclToken,
    LsclTokenType,
    parse_lscl,
    parse_lscl_tokens,
)


CONFIGS_PATH = Path(__file__).parent / "configs"


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
def test_lexer(path: str, tokens: LsclToken) -> None:
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
    ),
)
def test_parse(path: str, content: LsclContent) -> None:
    """Test that parsing works correctly."""
    with open(CONFIGS_PATH / path) as fp:
        raw = fp.read()

    assert parse_lscl(raw) == content
