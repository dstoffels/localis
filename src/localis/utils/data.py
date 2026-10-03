from typing import Protocol


class CacheFilterPredicate(Protocol):
    def __call__(self, row: list[str]) -> bool: ...


class IndexFilterPredicate(Protocol):
    def __call__(self, id: int, allowed_ids: set[int]) -> bool: ...
