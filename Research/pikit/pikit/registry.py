"""A tiny name -> class registry with a decorator API.

Contributors add a new method by writing one file and decorating their
class; no edits to core code are required. Attacks and defenses each get
their own registry instance (see ``attacks/__init__.py`` and
``defenses/__init__.py``).
"""

from __future__ import annotations

from typing import Callable, Dict, Generic, List, Type, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Maps a short string key to a class.

    Examples
    --------
    >>> reg = Registry("attack")
    >>> @reg.register("naive")
    ... class _Naive:  # doctest: +SKIP
    ...     ...
    >>> reg.list()  # doctest: +SKIP
    ['naive']
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._registry: Dict[str, Type[T]] = {}

    def register(self, key: str) -> Callable[[Type[T]], Type[T]]:
        """Class decorator that records ``cls`` under ``key``.

        The decorator also sets ``cls.name = key`` if the class did not
        define its own, so the instance carries a stable identifier.
        """

        def decorator(cls: Type[T]) -> Type[T]:
            if key in self._registry:
                raise ValueError(
                    f"{self.kind} {key!r} is already registered by "
                    f"{self._registry[key].__name__}"
                )
            # Set name = key unless the class declared its own `name`
            # attribute directly (inherited base defaults don't count).
            if "name" not in cls.__dict__:
                cls.name = key  # type: ignore[attr-defined]
            self._registry[key] = cls
            return cls

        return decorator

    def get(self, key: str) -> Type[T]:
        """Return the class registered under ``key``.

        Raises
        ------
        KeyError
            If ``key`` is unknown, with the list of available keys.
        """
        try:
            return self._registry[key]
        except KeyError:
            raise KeyError(
                f"unknown {self.kind} {key!r}; available: {self.list()}"
            ) from None

    def list(self) -> List[str]:
        """Return all registered keys, sorted."""
        return sorted(self._registry)

    def __contains__(self, key: str) -> bool:
        return key in self._registry

    def __len__(self) -> int:
        return len(self._registry)
