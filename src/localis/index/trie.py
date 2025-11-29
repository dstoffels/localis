class PrefixTrie:
    def __init__(self):
        self.root: dict[str, set[str]] = {}

    def add(self, word: str, id: int):
        node = self.root

        for char in word.lower():
            if char not in node:
                node[char] = {"ids": set(), "children": {}}
            node = node[char]
            node["ids"].add(id)

    def search_prefix(self, prefix: str, limit=500) -> set[int]:
        node = self.root

        for char in prefix.lower():
            if char not in node:
                return set()
            node = node[char]

        return node.get("ids", set())
