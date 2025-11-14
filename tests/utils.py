import random
import string
from villager.registries import Registry


alphabet = string.ascii_lowercase


def mangle(s: str, typo_chance: float = 0.15, seed: int = 42) -> str:
    rng = random.Random(seed)
    if not s or len(s) < 4:
        return s

    s_list = list(s)
    typo_ops = ["swap", "replace", "delete", "insert"]
    num_typos = max(1, int(len(s) * typo_chance))
    applied = 0
    positions = set()

    while applied < num_typos:
        # Skip first two characters to preserve prefix
        i = rng.randint(2, len(s_list) - 2)
        if i in positions or s_list[i].isspace():
            continue

        op = rng.choice(typo_ops)

        if op == "swap" and i < len(s_list) - 1 and not s_list[i + 1].isspace():
            s_list[i], s_list[i + 1] = s_list[i + 1], s_list[i]
        elif op == "replace":
            s_list[i] = rng.choice(alphabet)
        elif op == "insert":
            s_list.insert(i + 1, rng.choice(alphabet))
        elif op == "delete":
            del s_list[i]

        positions.add(i)
        applied += 1

    return "".join(s_list)


def select_random(reg: Registry):
    id = random.choice(range(1, reg.count))
    return reg.get(id=id)
