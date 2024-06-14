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
"""Tests for the ``lscl.filters`` module."""

from __future__ import annotations

from lscl.filters import (
    LogstashFilter,
    LogstashFilterBranching,
    parse_logstash_filters,
    render_logstash_filters,
)
from lscl.lang import (
    LsclAttribute,
    LsclBlock,
    LsclEqualTo,
    LsclGreaterThan,
    LsclSelector,
)


def test_find_filter() -> None:
    """Check that we find Logstash filters in subdirectives as well."""
    raw = """
    if [hello.world] == 42 {
        filter {
            mutate {
                add_field => {"hello.world" => 42}
            }
        }
    }
    """

    assert parse_logstash_filters(raw) == [
        LogstashFilterBranching(
            conditions=[
                (
                    LsclEqualTo(
                        first=LsclSelector(names=["hello.world"]),
                        second=42,
                    ),
                    [
                        LogstashFilter(
                            name="mutate",
                            config={
                                "add_field": {"hello.world": 42},
                            },
                        ),
                    ],
                ),
            ],
        ),
    ]


def test_find_filter_on_block() -> None:
    """Check that we can find Logstash filters in the given block directly."""
    block = LsclBlock(
        name="filter",
        content=[
            LsclBlock(
                name="mutate",
                content=[
                    LsclAttribute(
                        name="add_field",
                        content={"hello.world": 42},
                    ),
                ],
            ),
        ],
    )
    expected = [
        LogstashFilter(
            name="mutate",
            config={"add_field": {"hello.world": 42}},
        ),
    ]

    assert parse_logstash_filters(block) == expected
    assert parse_logstash_filters(block.content) == expected
    assert parse_logstash_filters(block.content, at_root=False) == []
    block.name = "not_filter"
    assert parse_logstash_filters(block) == []
    assert parse_logstash_filters(block.content, at_root=True) == expected


def test_render_filters() -> None:
    """Check that filter rendering works correctly."""
    assert (
        render_logstash_filters(
            [
                LogstashFilter(
                    name="mutate",
                    config={"add_field": {"hello.world": 42}},
                ),
            ],
        )
        == 'mutate {\n  add_field => {\n    "hello.world" => 42\n  }\n}\n'
    )
    assert (
        render_logstash_filters(
            [
                LogstashFilterBranching(
                    conditions=[
                        (
                            LsclGreaterThan(
                                first=LsclSelector(names=["power"]),
                                second=9000,
                            ),
                            [
                                LogstashFilter(
                                    name="mutate",
                                    config={"convert": {"power": "string"}},
                                ),
                            ],
                        ),
                    ],
                    default=[LogstashFilter(name="age")],
                ),
            ],
        )
        == "if [power] > 9000 {\n  mutate {\n    convert => {\n      power => "
        + "string\n    }\n  }\n} else {\n  age {}\n}\n"
    )
