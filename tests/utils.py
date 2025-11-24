import random
import string
from localis.registries import Registry
from localis.data.dtos import DTO


alphabet = string.ascii_lowercase


def mangle(
    s: str,
    typo_chance: float = 0.15,
    seed: int | None = None,
) -> str:
    # ignore empty or strings of 3 or less
    if not s or len(s) < 4:
        return s

    rng = random.Random(seed)

    tokens = s.split()

    total_chars = sum(len(t) for t in tokens)
    realism_factor = 0.5
    total_typos = max(1, round(total_chars * typo_chance * realism_factor))

    eligible_tokens = [(i, t) for i, t in enumerate(tokens) if len(t) > 2]

    if not eligible_tokens:
        return s

    # generate weights by token length so longer tokens are more likely to receive typos
    token_weights = [len(t) - 1 for _, t in eligible_tokens]

    # randomly assign each typo to a token
    typo_assignments = {i: 0 for i, _ in eligible_tokens}
    for _ in range(total_typos):
        idx = rng.choices([i for i, _ in eligible_tokens], weights=token_weights, k=1)[
            0
        ]
        typo_assignments[idx] += 1

    mangled_tokens = []

    for token_idx, token in enumerate(tokens):
        # skip if no typo assigned to token
        if token_idx not in typo_assignments or typo_assignments[token_idx] == 0:
            mangled_tokens.append(token)
            continue

        # preserve first char, work on the rest
        num_typos = typo_assignments[token_idx]
        first_char = token[0]
        rest = list(token[1:])

        # skip shorties
        if len(token) < 1:
            mangled_tokens.append(token)
            continue

        typo_ops = rng.choices(
            ["replace", "swap", "delete", "insert"],
            weights=[60, 25, 10, 5],
            k=num_typos,
        )

        used_positions = set()

        for op in typo_ops:
            # find a usable position in the rest of the word to inject typo
            attempts = 0
            while attempts < 10:
                idx = rng.randint(0, len(rest) - 1)  # randomly select a char

                # eligible char move forward
                if idx not in used_positions:
                    break
                attempts += 1
            else:
                continue

            used_positions.add(idx)

            # apply op
            if op == "replace":
                rest[idx] = rng.choice(alphabet)

            elif op == "swap" and idx < len(rest) - 1:
                rest[idx], rest[idx + 1] = rest[idx + 1], rest[idx]

            elif op == "delete" and len(rest) > 1:
                del rest[idx]

            elif op == "insert":
                rest.insert(idx + 1, rng.choice(alphabet))

        # reassemble token
        mangled_tokens.append(first_char + "".join(rest))

    return " ".join(mangled_tokens)
