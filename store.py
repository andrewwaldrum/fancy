"""A dict-like store that keeps structure and content separately.

- content:   leaf values (str, int, None, ...), stored once under a hash key
- structure: the shape of each entry, with leaves replaced by Refs

Everything is immutable: set/delete/update return a new Store.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass, replace
from functools import reduce
from hashlib import sha1
from typing import Any, Iterator


@dataclass(frozen=True)
class Ref:
    """Points at a leaf value in the content table."""
    key: str


@dataclass(frozen=True)
class Node:
    """A container: `kind` is dict, list, or a dataclass type."""
    kind: type
    children: Any  # dict[str, Ref | Node] for dict/dataclass, list[Ref | Node] for list


Shape = Ref | Node
Content = dict[str, Any]


def leaf_key(value: Any) -> str:
    """Content address. The type name keeps 1, 1.0 and True apart."""
    return sha1(f"{type(value).__name__}:{value!r}".encode()).hexdigest()[:12]


def union(tables) -> Content:
    return reduce(lambda a, b: {**a, **b}, tables, {})


def is_instance(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type)


def split(value: Any) -> tuple[Shape, Content]:
    """Break a value into (structure, content)."""
    if isinstance(value, dict):
        parts = {k: split(v) for k, v in value.items()}
        shape = Node(dict, {k: s for k, (s, _) in parts.items()})
        return shape, union(c for _, c in parts.values())

    if isinstance(value, list):
        parts = [split(v) for v in value]
        return Node(list, [s for s, _ in parts]), union(c for _, c in parts)

    if is_instance(value):
        parts = {f.name: split(getattr(value, f.name)) for f in fields(value)}
        shape = Node(type(value), {k: s for k, (s, _) in parts.items()})
        return shape, union(c for _, c in parts.values())

    key = leaf_key(value)
    return Ref(key), {key: value}


def join(shape: Shape, content: Content) -> Any:
    """Rebuild a value from (structure, content)."""
    if isinstance(shape, Ref):
        return content[shape.key]

    if shape.kind is list:
        return [join(child, content) for child in shape.children]

    built = {k: join(child, content) for k, child in shape.children.items()}
    return built if shape.kind is dict else shape.kind(**built)


def refs(shape: Shape) -> set[str]:
    """Every content key a structure points at."""
    if isinstance(shape, Ref):
        return {shape.key}
    kids = shape.children.values() if isinstance(shape.children, dict) else shape.children
    return set().union(*map(refs, kids))


@dataclass(frozen=True)
class Store(Mapping):
    structure: dict[str, Shape] = field(default_factory=dict)
    content: Content = field(default_factory=dict)

    # --- read-only dict interface ---
    def __getitem__(self, key: str) -> Any:
        return join(self.structure[key], self.content)

    def __iter__(self) -> Iterator[str]:
        return iter(self.structure)

    def __len__(self) -> int:
        return len(self.structure)

    # --- updates return a new Store ---
    def set(self, key: str, value: Any) -> "Store":
        shape, content = split(value)
        return replace(
            self,
            structure={**self.structure, key: shape},
            content={**self.content, **content},
        )

    def update(self, items: Mapping[str, Any]) -> "Store":
        return reduce(lambda store, kv: store.set(*kv), items.items(), self)

    def delete(self, key: str) -> "Store":
        return replace(self, structure={k: s for k, s in self.structure.items() if k != key})

    def gc(self) -> "Store":
        """Drop content nothing points at any more."""
        live = set().union(*map(refs, self.structure.values()))
        return replace(self, content={k: v for k, v in self.content.items() if k in live})

    def __or__(self, other: "Store") -> "Store":
        return Store({**self.structure, **other.structure}, {**self.content, **other.content})


def from_dict(items: Mapping[str, Any]) -> Store:
    return Store().update(items)


if __name__ == "__main__":
    @dataclass
    class User:
        name: str
        tags: list

    store = from_dict({
        "title": "Hello",
        "count": 3,
        "config": {"debug": True, "retries": 3},
        "alice": User("Alice", ["admin", "dev"]),
        "bob": User("Bob", ["dev"]),
    })

    assert store["config"] == {"debug": True, "retries": 3}
    assert store["alice"] == User("Alice", ["admin", "dev"])

    # "dev" and 3 are stored once, no matter how often they appear
    assert list(store.content.values()).count("dev") == 1
    assert list(store.content.values()).count(3) == 1

    # immutable updates, and gc removes orphaned content
    smaller = store.delete("alice")
    assert "alice" not in smaller and "alice" in store
    assert "admin" in smaller.content.values()
    assert "admin" not in smaller.gc().content.values()

    print(f"{len(store)} entries, {len(store.content)} unique leaf values")
    print("structure of 'bob':", store.structure["bob"])
    print("all good")
