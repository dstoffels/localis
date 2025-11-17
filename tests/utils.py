import random
import string
from villager.registries import Registry
from villager.dtos import DTO


alphabet = string.ascii_lowercase


def mangle(
    s: str,
    typo_chance: float = 0.15,
    seed: int | None = None,
) -> str:
    if not s or len(s) < 4:
        return s

    rng = random.Random(seed)

    s_list = list(s)
    n = len(s_list)

    realism_factor = 0.5
    num_typos = max(1, round(n * typo_chance * realism_factor))

    typo_ops = rng.choices(
        ["replace", "swap", "delete", "insert"],
        weights=[60, 25, 10, 5],
        k=num_typos,
    )

    used_positions = set()

    for op in typo_ops:
        # find a usable position (avoid whitespace and repeats)
        attempts = 0
        while attempts < 10:
            idx = rng.randint(1, len(s_list) - 2)
            if idx not in used_positions and not s_list[idx].isspace():
                break
            attempts += 1
        else:
            continue

        used_positions.add(idx)

        # apply op
        if op == "replace":
            s_list[idx] = rng.choice(alphabet)

        elif op == "swap" and idx < len(s_list) - 1 and not s_list[idx + 1].isspace():
            s_list[idx], s_list[idx + 1] = s_list[idx + 1], s_list[idx]

        elif op == "delete":
            del s_list[idx]

        elif op == "insert":
            s_list.insert(idx + 1, rng.choice(alphabet))

    return "".join(s_list)


def select_random(reg: Registry) -> DTO:
    id = random.choice(range(1, reg.count))
    return reg.get(id=id)
