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
"""Language-related definitions for lscl."""

from __future__ import annotations

from decimal import Decimal
import re
from typing import Annotated, Union

from annotated_types import Len
from pydantic import BaseModel, StringConstraints
from typing_extensions import TypeAliasType


LsclData = TypeAliasType(  # type: ignore
    "LsclData",
    Union[
        dict[str, "LsclData"],  # type: ignore
        list["LsclData"],  # type: ignore
        str,
        int,
        Decimal,
    ],
)
"""Type representing a document to process."""


# ---
# Conditions.
# ---


LsclRValue = TypeAliasType(  # type: ignore
    "LsclRValue",
    Union[
        list["LsclData"],
        str,
        int,
        Decimal,
        "LsclSelector",
        "LsclMethodCall",
    ],
)
"""Value that can be evaluated."""

LsclCondition = TypeAliasType(  # type: ignore
    "LsclCondition",
    Union[
        "LsclRValue",
        "LsclAnd",
        "LsclNand",
        "LsclOr",
        "LsclXor",
        "LsclNot",
        "LsclIn",
        "LsclNotIn",
        "LsclEqualTo",
        "LsclNotEqualTo",
        "LsclGreaterThan",
        "LsclGreaterThanOrEqualTo",
        "LsclLessThan",
        "LsclLessThanOrEqualTo",
        "LsclMatch",
        "LsclNotMatch",
    ],
)
"""Condition."""


class LsclSelector(BaseModel):
    """Selector for evaluating a variable within a condition."""

    names: Annotated[
        list[Annotated[str, StringConstraints(pattern=r"^[^\[\]\,]+$")]],
        Len(min_length=1),
    ]
    """Name of the variable to evaluate."""


class LsclMethodCall(BaseModel):
    """Method call."""

    name: str
    """Name of the function to call."""

    params: list[LsclRValue] = []
    """Parameters."""


class LsclAnd(BaseModel):
    """And condition."""

    conditions: list[LsclCondition]
    """List of conditions."""


class LsclOr(BaseModel):
    """Or condition."""

    conditions: list[LsclCondition]
    """List of conditions."""


class LsclXor(BaseModel):
    """Xor condition."""

    conditions: list[LsclCondition]
    """List of conditions."""


class LsclNand(BaseModel):
    """Nand condition."""

    conditions: list[LsclCondition]
    """Condition to inverse the result of the and of."""


class LsclNot(BaseModel):
    """Not condition."""

    condition: LsclCondition
    """Condition to inverse the result of."""


class LsclIn(BaseModel):
    """In condition."""

    needle: LsclRValue
    """Needle to look for."""

    haystack: LsclRValue
    """Haystack in which to look for the needle."""


class LsclNotIn(BaseModel):
    """Not in condition."""

    needle: LsclRValue
    """Needle to look for."""

    haystack: LsclRValue
    """Haystack in which to look for the needle."""


class LsclEqualTo(BaseModel):
    """Equal condition."""

    first: LsclRValue
    """First value."""

    second: LsclRValue
    """Second value."""


class LsclNotEqualTo(BaseModel):
    """Not equal condition."""

    first: LsclRValue
    """First value."""

    second: LsclRValue
    """Second value."""


class LsclGreaterThan(BaseModel):
    """Greater than condition."""

    first: LsclRValue
    """First value."""

    second: LsclRValue
    """Second value."""


class LsclGreaterThanOrEqualTo(BaseModel):
    """Greater than condition."""

    first: LsclRValue
    """First value."""

    second: LsclRValue
    """Second value."""


class LsclLessThan(BaseModel):
    """Greater than condition."""

    first: LsclRValue
    """First value."""

    second: LsclRValue
    """Second value."""


class LsclLessThanOrEqualTo(BaseModel):
    """Greater than condition."""

    first: LsclRValue
    """First value."""

    second: LsclRValue
    """Second value."""


class LsclMatch(BaseModel):
    """Condition to see if an rvalue matches a pattern."""

    value: LsclRValue
    """Value to match."""

    pattern: re.Pattern
    """Pattern."""


class LsclNotMatch(BaseModel):
    """Condition to see if an rvalue does not match a pattern."""

    value: LsclRValue
    """Value to match."""

    pattern: re.Pattern
    """Pattern."""


# ---
# Structures.
# ---


LsclContent = TypeAliasType(
    "LsclContent",
    list[Union["LsclBlock", "LsclAttribute", "LsclConditions"]],
)
"""Content, as a list of named blocks, named data, and conditions."""


class LsclConditions(BaseModel):
    """Condition with content."""

    conditions: Annotated[
        list[tuple[LsclCondition, LsclContent]],
        Len(min_length=1),
    ]
    """Conditions to check sequentially."""

    default: LsclContent | None = None
    """Block to consider if none of the above conditions match."""


class LsclAttribute(BaseModel):
    """Data with a name."""

    name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$")]
    """Name of the data."""

    content: LsclData = {}
    """Data being named."""


class LsclBlock(BaseModel):
    """Block with a name."""

    name: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$")]
    """Name of the block."""

    content: LsclContent = []
    """Content, as a list of named blocks, named data, and conditions."""


# HACK: Resolve circular dependencies.
LsclMethodCall.model_rebuild()
LsclSelector.model_rebuild()
LsclAnd.model_rebuild()
LsclOr.model_rebuild()
LsclXor.model_rebuild()
LsclNot.model_rebuild()
LsclConditions.model_rebuild()
LsclAttribute.model_rebuild()
