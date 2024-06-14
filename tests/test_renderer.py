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
"""Tests for the ``lscl.renderer`` module."""

from __future__ import annotations

import pytest

from lscl.lang import (
    LsclAnd,
    LsclAttribute,
    LsclBlock,
    LsclConditions,
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
from lscl.renderer import LsclRenderable, render_as_lscl


@pytest.mark.parametrize(
    "raw,expected",
    (
        (
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclMatch(
                                value=LsclSelector(names=["hello.world"]),
                                pattern=r"[\t\n]+",
                            ),
                            [LsclBlock(name="age")],
                        ),
                    ],
                ),
            ],
            "if [hello.world] =~ /[\\t\\n]+/ {\n  age {}\n}\n",
        ),
        ([LsclAttribute(name="hello", content={})], "hello => {}\n"),
        ([LsclAttribute(name="hello", content=[])], "hello => []\n"),
        (
            [
                LsclAttribute(name="hello", content=["world"]),
                "hello => [\n  world\n]\n",
            ]
        ),
        (
            [LsclAttribute(name="hello", content=[42, "world"])],
            "hello => [\n  42,\n  world\n]\n",
        ),
        (
            [
                LsclConditions(
                    conditions=[
                        (
                            LsclMethodCall(
                                name="my_function",
                                params=[
                                    1,
                                    LsclSelector(names=["example", "2"]),
                                    "oh no",
                                ],
                            ),
                            [LsclAttribute(name="hello", content="world")],
                        ),
                    ],
                ),
            ],
            'if my_function(1, [example][2], "oh no") {\n  hello => '
            + "world\n}\n",
        ),
        (
            LsclAnd(conditions=[LsclEqualTo(first=1, second=2)]),
            "1 == 2",
        ),
        (
            LsclAnd(
                conditions=[
                    LsclGreaterThan(first=1, second=2),
                    LsclOr(
                        conditions=[
                            LsclGreaterThanOrEqualTo(first=2, second=3),
                            LsclLessThan(first=3, second=4),
                            LsclLessThanOrEqualTo(first=4, second=5),
                        ],
                    ),
                ],
            ),
            "1 > 2 and (2 >= 3 or 3 < 4 or 4 <= 5)",
        ),
        (
            LsclXor(
                conditions=[
                    LsclNand(
                        conditions=[
                            LsclNot(condition=LsclSelector(names=["hello"])),
                            LsclNot(
                                condition=LsclOr(
                                    conditions=[
                                        LsclIn(
                                            needle=5,
                                            haystack=LsclSelector(
                                                names=["arr"],
                                            ),
                                        ),
                                        LsclNotIn(
                                            needle=6,
                                            haystack=LsclSelector(
                                                names=["arr"],
                                            ),
                                        ),
                                        LsclNotEqualTo(first=1, second=2),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    LsclNotMatch(
                        value=LsclSelector(names=["value"]),
                        pattern=r"[0-9]+",
                    ),
                ],
            ),
            "(![hello] nand !(5 in [arr] or 6 not in [arr] or 1 != 2)) xor "
            + "[value] !~ /[0-9]+/",
        ),
        (
            LsclConditions(
                conditions=[(LsclEqualTo(first=1, second=2), [])],
                default=[],
            ),
            "if 1 == 2 {}\nelse {}\n",
        ),
        (
            4,
            "4\n",
        ),
        ({"hello": "world"}, "{\n  hello => world\n}\n"),
        (
            LsclMethodCall(name="hello"),
            "hello()",
        ),
        (
            LsclSelector(names=["1", "2"]),
            "[1][2]",
        ),
        (
            [1, 2, 3],
            "[\n  1,\n  2,\n  3\n]\n",
        ),
    ),
)
def test_render(raw: LsclRenderable, expected: str) -> None:
    """Check the renderer works correctly."""
    assert render_as_lscl(raw) == expected


def test_render_unknown_type() -> None:
    """Test rendering an unknown type."""
    with pytest.raises(TypeError):
        render_as_lscl(pytest)
