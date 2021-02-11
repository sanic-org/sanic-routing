import pytest

from sanic_routing.tree import Node


@pytest.fixture
def root():
    return Node(root=True)


def test_nesting(root):
    child = Node(part="a", parent=root)
    root.add_child(child)

    assert child == root._children["a"]
    assert not root.children

    root.finalize_children()

    assert child == root.children["a"]
