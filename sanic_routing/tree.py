import typing as t
from logging import getLogger

from .line import Line
from .patterns import REGEX_PARAM_NAME, REGEX_TYPES
from .route import Route

logger = getLogger("sanic.root")


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
        self.offset = 0
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
        return f"<Node: {internals}>"

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
        """
        Visual display of the tree of nodes
        """
        logger.info(" " * 4 * self.level + str(self))
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

    def apply_offset(self, amt, apply_self=True, apply_children=False):
        if apply_self:
            self.offset += amt
        if apply_children:
            for child in self.children.values():
                child.apply_offset(amt, apply_children=True)

    def to_src(self) -> t.Tuple[t.List[Line], t.List[Line]]:
        indent = (self.level + 1) * 2 - 3 + self.offset
        delayed: t.List[Line] = []
        src: t.List[Line] = []

        level = self.level - 1
        equality_check = False
        return_bump = 1

        if self.first or self.root:
            src = []
            operation = ">"
            use_level = level
            conditional = "if"
            if (
                self.last
                and self.route
                and not self.children
                and not self.route.requirements
            ):
                use_level = self.level
                operation = "=="
                equality_check = True
                conditional = "elif"
                src.extend(
                    [
                        Line(f"if num > {use_level}:", indent),
                        Line("raise NotFound", indent + 1),
                    ]
                )
            src.append(
                Line(f"{conditional} num {operation} {use_level}:", indent)
            )

        if self.dynamic:
            if not self.parent.children_basketed:
                self.parent.children_basketed = True
                src.append(
                    Line(f"basket[{level}] = parts[{level}]", indent + 1)
                )
                self.parent.apply_offset(-1, False, True)

                if not self.children:
                    return_bump -= 1
        else:
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
            if self.children:
                return_bump += 1

        if self.route and not self.route.regex:
            location = delayed if self.children else src
            if self.route.requirements:
                self._inject_requirements(
                    location, indent + return_bump + bool(not self.children)
                )
            if self.route.params:
                self._inject_params(
                    location, indent + return_bump + bool(not self.children)
                )
            param_offset = bool(self.route.params)
            return_indent = (
                indent + return_bump + bool(not self.children) + param_offset
            )
            location.extend(
                [
                    Line(
                        (f"basket['__raw_path__'] = '{self.route.path}'"),
                        return_indent,
                    ),
                    Line(
                        (
                            f"return router.dynamic_routes[{self.route.parts}]"
                            ", basket"
                        ),
                        return_indent,
                    ),
                    # Line("...", return_indent - 1, render=True),
                ]
            )
            if self.route.params:
                location.append(Line("...", return_indent - 1, render=False))
                if self.last:
                    location.append(
                        Line("...", return_indent - 2, render=False),
                    )
        return src, delayed

    def add_child(self, child: "Node") -> None:
        self._children[child.part] = child

    def _inject_requirements(self, location, indent):
        for k, (idx, reqs) in enumerate(self.route.requirements.items()):
            conditional = "if" if k == 0 else "elif"
            location.extend(
                [
                    Line((f"{conditional} extra == {reqs}:"), indent),
                    Line((f"basket['__handler_idx__'] = {idx}"), indent + 1),
                ]
            )
        location.extend(
            [
                Line(("else:"), indent),
                Line(("raise NotFound"), indent + 1),
            ]
        )

    def _inject_params(self, location, indent):
        lines = [
            Line(f"if num > {self.level}:", indent),
            Line("raise NotFound", indent + 1),
        ]
        lines.append(Line("try:", indent))
        for idx, param in self.route.params.items():
            unquote_start = "unquote(" if self.route.unquote else ""
            unquote_end = ")" if self.route.unquote else ""
            lines.append(
                Line(
                    f"basket['__params__']['{param.name}'] = "
                    f"{unquote_start}{param.cast.__name__}(basket[{idx}])"
                    f"{unquote_end}",
                    indent + 1,
                )
            )

        location.extend(
            lines
            + [
                Line("except ValueError:", indent),
                Line("pass", indent + 1),
                Line("else:", indent),
            ]
        )

    @staticmethod
    def _sorting(item) -> t.Tuple[bool, int, str, int]:
        key, child = item
        type_ = 0
        if child.dynamic:
            key = key[1:-1]
            if ":" in key:
                key, param_type = key.split(":")
                try:
                    type_ = list(REGEX_TYPES.keys()).index(param_type)
                except ValueError:
                    type_ = len(list(REGEX_TYPES.keys()))
        return child.dynamic, len(child._children) * -1, key, type_ * -1


class Tree:
    def __init__(self) -> None:
        self.root = Node(root=True)
        self.root.level = 0

    def generate(self, routes: t.Dict[t.Tuple[str, ...], Route]) -> None:
        for route in routes.values():
            current = self.root
            for level, part in enumerate(route.parts):
                if part not in current._children:
                    current.add_child(Node(part=part, parent=current))
                current = current._children[part]
                current.level = level + 1

                current.dynamic = part.startswith("<")
                if current.dynamic and not REGEX_PARAM_NAME.match(part):
                    raise ValueError(f"Invalid declaration: {part}")

            current.route = route

    def display(self) -> None:
        """
        Debug tool to output visual of the tree
        """
        self.root.display()

    def render(self) -> t.List[Line]:
        return self.root.render()

    def finalize(self):
        self.root.finalize_children()
