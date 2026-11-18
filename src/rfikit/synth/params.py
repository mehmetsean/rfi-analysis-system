from dataclasses import dataclass


@dataclass(frozen=True)
class GenParams:
    noise_rate: float = 0.35
    invented_rate: float = 0.3
    response_rate: float = 0.5
    greeting_rate: float = 0.3
    families: tuple[str, ...] = ("A", "B")

    def __post_init__(self) -> None:
        for name in ("noise_rate", "invented_rate", "response_rate", "greeting_rate"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if not self.families or any(f not in ("A", "B") for f in self.families):
            raise ValueError("families must be a non-empty subset of A and B")
        if len(set(self.families)) != len(self.families):
            raise ValueError("families must not repeat")
