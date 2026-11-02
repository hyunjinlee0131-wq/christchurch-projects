def plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def pct(x: float, digits: int = 0) -> str:
    return f"{x:.{digits}%}"
