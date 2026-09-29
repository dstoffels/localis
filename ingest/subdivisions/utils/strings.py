def dedupe(items: list[str]) -> list[str]:
    seen = {}
    for s in items:
        key = s.lower()
        if key not in seen or len(s) < len(seen[key]):
            seen[key] = s
    return sorted(seen.values())
