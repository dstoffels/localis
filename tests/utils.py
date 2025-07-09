import random

alphabet = "abcdefghijklmnopqrstuvwxyz"


def mangle(s: str, typo_chance: float = 0.15, seed: int = 42) -> str:
    rng = random.Random(seed)
    if not s or len(s) < 3:
        return s

    s_list = list(s)
    typo_ops = ["swap", "replace", "delete"]
    num_typos = max(1, int(len(s) * typo_chance))
    applied = 0
    positions = set()

    while applied < num_typos:
        i = rng.randint(1, len(s_list) - 2)
        if i in positions or s_list[i].isspace():
            continue

        op = rng.choice(typo_ops)
        if op == "swap" and i < len(s_list) - 1 and not s_list[i + 1].isspace():
            s_list[i], s_list[i + 1] = s_list[i + 1], s_list[i]
        elif op == "replace":
            s_list[i] = rng.choice(alphabet)
        elif op == "insert":
            s_list.insert(i, rng.choice(alphabet))
        elif op == "delete":
            del s_list[i]

        positions.add(i)
        applied += 1

    return "".join(s_list)
