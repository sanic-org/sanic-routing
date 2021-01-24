import typing as t

from .line import Line
from .route import Route


class Node:
    def __init__(
        self, part: str = "", root: bool = False, parent=None
    ) -> None:
        self.root = root
        self.part = part
        self.parent = parent
        self._children: t.Dict[str, "Node"] = {}
        self.children: t.Dict[str, "Node"] = {}
        self.level = 0
        self.route: t.Optional[Route] = None
        self.dynamic = False
        self.first = False
        self.last = False
        self.children_basketed = False

    def __repr__(self) -> str:
        internals = ", ".join(
            f"{prop}={getattr(self, prop)}"
            for prop in ["part", "level", "route", "dynamic"]
            if getattr(self, prop) or prop in ["level"]
        )
        return f"Node({internals})"

    def finalize_children(self):
        self.children = {
            k: v for k, v in sorted(self._children.items(), key=self._sorting)
        }
        if self.children:
            keys = list(self.children.keys())
            self.children[keys[0]].first = True
            self.children[keys[-1]].last = True

            for child in self.children.values():
                child.finalize_children()

    def display(self) -> None:
        """This is TEMP"""
        print(" " * 4 * self.level, self)
        for child in self.children.values():
            child.display()

    def render(self) -> t.List[Line]:
        if not self.root:
            output, delayed = self.to_src()
        else:
            output = []
            delayed = []
        for child in self.children.values():
            output += child.render()
        output += delayed
        return output

    def to_src(self) -> t.Tuple[t.List[Line], t.List[Line]]:
        indent = (self.level + 1) * 2 - 1
        delayed: t.List[Line] = []
        src: t.List[Line] = []
        # if self.dynamic:
        indent -= +2
        level = self.level - 1
        equality_check = False

        if self.first or self.root:
            operation = ">"
            use_level = level
            if self.last and not self.level == 1:
                use_level = self.level
                operation = "=="
                equality_check = True
            src = [Line(f"if num {operation} {use_level}:", indent)]

        if self.dynamic:
            if not self.parent.children_basketed:
                self.parent.children_basketed = True
                src.append(
                    Line(f"basket[{level}] = parts[{level}]", indent + 1)
                )
                # This is a control line to help control indentation, but
                # it should not be rendered
                src.append(Line("...", 0, offset=-1, render=False))
        else:
            # "if" if (self.parent and self.parent.first)
            # or self.root else "elif"
            if_stmt = "if" if self.first or self.root else "elif"
            len_check = (
                f" and num == {self.level}"
                if not self.children and not equality_check
                else ""
            )
            src.append(
                Line(
                    f'{if_stmt} parts[{level}] == "{self.part}"{len_check}:',
                    indent + 1,
                )
            )

        if self.route:
            location = delayed if self.children else src
            location.append(
                Line(
                    (
                        f"return router.dynamic_routes[{self.route.parts}]"
                        ", basket"
                    ),
                    indent + 1 + bool(not self.children),
                )
            )
        return src, delayed

    def add_child(self, child: "Node") -> None:
        self._children[child.part] = child

    @staticmethod
    def _sorting(item) -> t.Tuple[bool, int, str]:
        key, child = item
        return child.dynamic, len(child._children) * -1, key


class Tree:
    def __init__(self) -> None:
        self.root = Node(root=True)
        self.root.level = 0

    def generate(
        self, routes: t.Dict[t.Union[str, t.Tuple[str, ...]], Route]
    ) -> None:
        for route in routes.values():
            current = self.root
            for level, part in enumerate(route.parts):
                if part not in current._children:
                    current.add_child(Node(part=part, parent=current))
                current = current._children[part]
                current.level = level + 1

                # TODO:
                # - full evaluation to make sure that the part if it is dynamic
                #   is compliant and can be parsed by one of the known types
                current.dynamic = part.startswith("<")
            current.route = route

    def display(self) -> None:
        self.root.display()

    def render(self) -> t.List[Line]:
        return self.root.render()

    def finalize(self):
        self.root.finalize_children()
