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
"""Filter decoding and encoding using lscl."""

from __future__ import annotations

from typing import Annotated, Union

from annotated_types import Len
from pydantic import BaseModel
from typing_extensions import TypeAliasType

from .lang import (
    LsclAttribute,
    LsclBlock,
    LsclCondition,
    LsclConditions,
    LsclContent,
    LsclData,
)
from .parser import parse_lscl
from .renderer import render_as_lscl


LogstashFilters = TypeAliasType(
    "LogstashFilters",
    list[Union["LogstashFilter", "LogstashFilterBranching"]],
)
"""Type representing a list of Logstash filters and branching."""


class LogstashFilter(BaseModel):
    """Definition of a Logstash filter."""

    name: str
    """Name of the filter."""

    config: dict[str, LsclData] = {}
    """Configuration for the filter."""


class LogstashFilterBranching(BaseModel):
    """Condition under which one or more filters can be executed."""

    conditions: Annotated[
        list[tuple[LsclCondition, LogstashFilters]],
        Len(min_length=1),
    ]
    """Conditions and associated filters and additional branching."""

    default: LogstashFilters | None = None
    """Default branch to take, if other branches aren't explored."""


def _get_filters(
    raw: LsclContent,
    /,
) -> LogstashFilters:
    """Get filters defined in a given content.

    :param raw: Raw LSCL content to get the filters from.
    :return: Logstash filters or branching.
    """
    result: list[LogstashFilter | LogstashFilterBranching] = []

    for element in raw:
        if isinstance(element, LsclConditions):
            # We have a condition in the source, we want to determine
            # branching out of it.
            result.append(
                LogstashFilterBranching(
                    conditions=[
                        (cond, _get_filters(body))
                        for cond, body in element.conditions
                    ],
                    default=(
                        _get_filters(element.default)
                        if element.default
                        else None
                    ),
                ),
            )
        elif isinstance(element, LsclBlock):
            # We consider this to be a filter configuration.
            # We want to get the configuration from the attributes.
            config: dict[str, LsclData] = {}
            for subelement in element.content:
                if isinstance(subelement, LsclAttribute):
                    config[subelement.name] = subelement.content

            result.append(LogstashFilter(name=element.name, config=config))

    return result


def _find_filter_content(raw: LsclContent, /) -> LsclContent:
    """Find filter content recursively.

    :param raw: Raw content in which to find content.
    :return: Filter content.
    """
    content = []
    for element in raw:
        if isinstance(element, LsclBlock):
            if element.name == "filter":
                content.extend(element.content)
        elif isinstance(element, LsclConditions):
            content.append(
                LsclConditions(
                    conditions=[
                        (cond, _find_filter_content(body))
                        for cond, body in element.conditions
                    ],
                    default=(
                        _find_filter_content(element.default)
                        if element.default is not None
                        else None
                    ),
                ),
            )

    return content


def _get_filter_content(
    raw: str | LsclContent | LsclBlock,
    /,
    *,
    at_root: bool | None = None,
) -> LsclContent:
    """Get LSCL content corresponding to the filter plugin.

    This may be behind evaluations to make at an upper level.

    :param raw: Raw configuration, to decode filters from.
    :param at_root: Whether the filters should be look for at root (True),
        in the "filter" block (False), or in the second case with a fallback
        to the first if unsure (None).
    :return: LSCL content to be used for
    """
    if isinstance(raw, LsclBlock):
        # If we are passed a block directly, it is either the "filter" block
        # directly, or nothing.
        if raw.name != "filter":
            return []

        return raw.content

    if isinstance(raw, str):
        src = parse_lscl(raw)
    else:
        src = raw

    if at_root is True:
        return src

    # We want to look for one or more "filter" blocks, possibly behind
    # conditions.
    content = _find_filter_content(src)
    if not content and at_root is None:
        return src

    return content


def parse_logstash_filters(
    raw: str | LsclContent | LsclBlock,
    /,
    *,
    at_root: bool | None = None,
) -> LogstashFilters:
    """Decode filters from a Logstash configuration file.

    :param raw: Raw configuration, to decode filters from.
    :param at_root: Whether the filters should be look for at root (True),
        in the "filter" block (False), or in the second case with a fallback
        to the first if unsure (None).
    :return: Obtained Logstash filters.
    """
    content = _get_filter_content(raw, at_root=at_root)
    return _get_filters(content)


# ---
# Rendering.
# ---


def _render_as_lscl_content(filters: LogstashFilters, /) -> LsclContent:
    """Render a list of filters or branching as LSCL content.

    :param filters: Filters or branching.
    :return: Rendered LSCL content.
    """
    content: LsclContent = []
    for element in filters:
        if isinstance(element, LogstashFilter):
            content.append(
                LsclBlock(
                    name=element.name,
                    content=[
                        LsclAttribute(name=key, content=value)
                        for key, value in sorted(element.config.items())
                    ],
                ),
            )
        elif isinstance(element, LogstashFilterBranching):
            content.append(
                LsclConditions(
                    conditions=[
                        (cond, _render_as_lscl_content(body))
                        for cond, body in element.conditions
                    ],
                    default=(
                        _render_as_lscl_content(element.default)
                        if element.default is not None
                        else None
                    ),
                ),
            )

    return content


def render_logstash_filters(filters: LogstashFilters, /) -> str:
    """Render Logstash filters.

    :param filters: Logstash filters or branching.
    :return: Filters encoded using LSCL.
    """
    return render_as_lscl(_render_as_lscl_content(filters))
