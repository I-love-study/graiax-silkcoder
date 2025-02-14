"""https://github.com/python/cpython/pull/127648"""
from abc import abstractmethod
from typing import TypeVar, Protocol

try:
    import numpy as np
    DataBuffer = TypeVar("DataBuffer", bytes, np.ndarray)
except ImportError:
    DataBuffer = bytes


T = TypeVar("T", covariant=True)
U = TypeVar("U", contravariant=True)

class Reader(Protocol[T]):
    """Protocol for simple I/O reader instances.
    This protocol only supports blocking I/O.
    """

    __slots__ = ()

    @abstractmethod
    def read(self, size: int = ..., /) -> T:
        """Read data from the input stream and return it.
        If "size" is specified, at most "size" items (bytes/characters) will be
        read.
        """

class Writer(Protocol[U]):
    """Protocol for simple I/O writer instances.
    This protocol only supports blocking I/O.
    """

    __slots__ = ()

    @abstractmethod
    def write(self, data: U, /) -> int:
        """Write data to the output stream and return number of items written."""

class AsyncReader(Protocol[T]):
    """Protocol for simple I/O reader instances.
    This protocol only supports blocking I/O.
    """

    __slots__ = ()

    @abstractmethod
    async def read(self, size: int = ..., /) -> T:
        """Read data from the input stream and return it.
        If "size" is specified, at most "size" items (bytes/characters) will be
        read.
        """

U = TypeVar("U", contravariant=True)
class AsyncWriter(Protocol[U]):
    """Protocol for simple I/O writer instances.
    This protocol only supports blocking I/O.
    """

    __slots__ = ()

    @abstractmethod
    async def write(self, data: U, /) -> int:
        """Write data to the output stream and return number of items written."""