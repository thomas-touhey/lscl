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
"""Error definitions."""

from __future__ import annotations


class Error(ValueError):
    """An error has occurred in an lscl function."""

    __slots__ = ()

    def __init__(self, message: str | None = None, /) -> None:
        super().__init__(message or "")


class DecodeError(Error):
    """An error has occurred while decoding something."""

    __slots__ = ("line", "column", "offset")

    line: int
    """Line number, counting from 1."""

    column: int
    """Column number, counting from 1."""

    offset: int
    """Offset of the string."""

    def __init__(
        self,
        message: str | None,
        /,
        *,
        line: int,
        column: int,
        offset: int,
    ) -> None:
        message = message or "A decoding error has occurred"
        super().__init__(
            f"At line {line}, column {column}: "
            + f"{message[0].lower()}{message[1:]}",
        )
        self.line = line
        self.column = column
        self.offset = offset


class StringRenderingError(Error):
    """An error has occurred while rendering a string."""

    __slots__ = ("string",)

    string: str
    """String that could not be rendered."""

    def __init__(self, /, *, string: str) -> None:
        super().__init__(
            f"The following string could not be rendered: {string!r}",
        )
        self.string = string


class SelectorElementRenderingError(Error):
    """An error has occurred while rendering a selector element."""

    __slots__ = ("selector_element",)

    selector_element: str
    """Selector element that could not be rendered."""

    def __init__(self, /, *, selector_element: str) -> None:
        super().__init__(
            "The following selector could not be rendered: "
            + f"{selector_element!r}",
        )
        self.selector_element = selector_element
