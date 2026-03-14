"""Forge Tool: Calculator — wiskundige bewerkingen."""


def add(a: float, b: float) -> float:
    """Tel twee getallen op.

    Args:
        a: Eerste getal.
        b: Tweede getal.

    Returns:
        De som van a en b.
    """
    return a + b


def multiply(a: float, b: float) -> float:
    """Vermenigvuldig twee getallen.

    Args:
        a: Eerste getal.
        b: Tweede getal.

    Returns:
        Het product van a en b.
    """
    return a * b


def fibonacci(n: int) -> list:
    """Bereken de eerste n Fibonacci-getallen.

    Args:
        n: Aantal getallen om te genereren.

    Returns:
        Lijst met Fibonacci-reeks.
    """
    if n <= 0:
        return []
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]
