import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class Rng:
    """Seeded helper. Only random.Random.random() is called."""

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an int")
        if seed < 0:
            raise ValueError("seed must not be negative")
        self._random = random.Random(seed)

    def unit(self) -> float:
        return self._random.random()

    def below(self, count: int) -> int:
        if count < 1:
            raise ValueError("count must be at least 1")
        return min(int(self._random.random() * count), count - 1)

    def between(self, low: int, high: int) -> int:
        return low + self.below(high - low + 1)

    def chance(self, probability: float) -> bool:
        return self._random.random() < probability

    def pick(self, items: Sequence[T]) -> T:
        return items[self.below(len(items))]

    def weighted(self, items: Sequence[T], weights: Sequence[int]) -> T:
        point = self.below(sum(weights))
        for item, weight in zip(items, weights, strict=True):
            if point < weight:
                return item
            point -= weight
        raise AssertionError("unreachable")

    def mix(self, items: list[T]) -> None:
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
