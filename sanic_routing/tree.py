import typing as t
from logging import getLogger

from .group import RouteGroup
from .line import Line
from .patterns import REGEX_PARAM_NAME, REGEX_TYPES

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
        self.group: t.Optional[RouteGroup] = None
        self.dynamic = False
        self.first = False
        self.last = False
        self.children_basketed = False
        self.children_param_injected = False

    def __str__(self) -> str:
        internals = ", ".join(
            f"{prop}={getattr(self, prop)}"
            for prop in ["part", "level", "group", "dynamic"]
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

    def render(self) -> t.Tuple[t.List[Line], t.List[Line]]:
        output: t.List[Line] = []
        delayed: t.List[Line] = []
        final: t.List[Line] = []

        if not self.root:
            output, delayed, final = self.to_src()
        for child in self.children.values():
            o, f = child.render()
            output += o
            final += f
        return output + delayed, final

    def apply_offset(self, amt, apply_self=True, apply_children=False):
        if apply_self:
            self.offset += amt
        if apply_children:
            for child in self.children.values():
                child.apply_offset(amt, apply_children=True)

    def to_src(self) -> t.Tuple[t.List[Line], t.List[Line], t.List[Line]]:
        indent = (self.level + 1) * 2 - 3 + self.offset
        delayed: t.List[Line] = []
        final: t.List[Line] = []
        src: t.List[Line] = []

        level = self.level - 1
        equality_check = False
        len_check = ""
        return_bump = 1

        if self.first:
            if level == 0:
                if self.group:
                    src.append(Line("if True:", indent))
                else:
                    src.append(Line("if parts[0]:", indent))
            else:
                operation = ">"
                use_level = level
                conditional = "if"
                if (
                    self.last
                    and self.group
                    and not self.children
                    and not self.group.requirements
                ):
                    use_level = self.level
                    operation = "=="
                    equality_check = True
                    conditional = "elif"
                    src.extend(
                        [
                            Line(f"if num > {use_level}:", indent),
                            Line("...", indent + 1)
                            if self._has_nested_path(self)
                            else Line("raise NotFound", indent + 1),
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

        if self.group:
            location = delayed if self.children else src
            route_idx: t.Union[int, str] = 0
            if self.group.requirements:
                route_idx = "route_idx"
                self._inject_requirements(
                    location, indent + return_bump + bool(not self.children)
                )
            if self.group.params and not self.group.regex:
                if not self.last:
                    return_bump += 1
                self._inject_params(
                    location,
                    indent + return_bump + bool(not self.children),
                    not self.parent.children_param_injected,
                )
                if not self.parent.children_param_injected:
                    self.parent.children_param_injected = True
            param_offset = bool(self.group.params)
            return_indent = (
                indent + return_bump + bool(not self.children) + param_offset
            )
            if route_idx == 0 and len(self.group.routes) > 1:
                route_idx = "route_idx"
                for i, route in enumerate(self.group.routes):
                    if_stmt = "if" if i == 0 else "elif"
                    location.extend(
                        [
                            Line(
                                f"{if_stmt} method in {route.methods}:",
                                return_indent,
                            ),
                            Line(f"route_idx = {i}", return_indent + 1),
                        ]
                    )
                location.extend(
                    [
                        Line("else:", return_indent),
                        Line("raise NoMethod", return_indent + 1),
                    ]
                )
            if self.group.regex:
                if self._has_nested_path(self, recursive=False):
                    location.append(Line("...", return_indent - 1))
                    return_indent = 2
                    location = final
                self._inject_regex(
                    location,
                    return_indent,
                    not self.parent.children_param_injected,
                )
            routes = "regex_routes" if self.group.regex else "dynamic_routes"
            route_return = (
                "" if self.group.router.stacking else f"[{route_idx}]"
            )
            location.extend(
                [
                    Line(
                        (
                            f"return router.{routes}[{self.group.parts}]"
                            f"{route_return}, basket"
                        ),
                        return_indent,
                    ),
                ]
            )

        return src, delayed, final

    def add_child(self, child: "Node") -> None:
        self._children[child.part] = child

    def _inject_requirements(self, location, indent):
        for k, route in enumerate(self.group):
            if k == 0:
                location.extend(
                    [
                        Line(f"if num > {self.level}:", indent),
                        Line("raise NotFound", indent + 1),
                    ]
                )

            conditional = "if" if k == 0 else "elif"
            location.extend(
                [
                    Line(
                        (
                            f"{conditional} extra == {route.requirements} "
                            f"and method in {route.methods}:"
                        ),
                        indent,
                    ),
                    Line((f"route_idx = {k}"), indent + 1),
                ]
            )

        location.extend(
            [
                Line(("else:"), indent),
                Line(("raise NotFound"), indent + 1),
            ]
        )

    def _inject_regex(self, location, indent, first_params):
        location.extend(
            [
                Line(
                    (
                        "match = router.matchers"
                        f"[{self.group.pattern_idx}].match(path)"
                    ),
                    indent - 1,
                ),
                Line("if match:", indent - 1),
                Line(
                    "basket['__params__'] = match.groupdict()",
                    indent,
                ),
            ]
        )

    def _inject_params(self, location, indent, first_params):
        if self.last:
            lines = [
                Line(f"if num > {self.level}:", indent),
                Line("raise NotFound", indent + 1),
            ]
        else:
            lines = []
            if first_params:
                lines.append(
                    Line(f"if num == {self.level}:", indent - 1),
                )
        lines.append(Line("try:", indent))
        for idx, param in self.group.params.items():
            unquote_start = "unquote(" if self.group.unquote else ""
            unquote_end = ")" if self.group.unquote else ""
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
                Line("except (ValueError, KeyError):", indent),
                Line("pass", indent + 1),
                Line("else:", indent),
            ]
        )

    def _has_nested_path(self, node, recursive=True):
        if node.group and (
            (node.group.labels and "path" in node.group.labels)
            or (node.group.pattern and r"/" in node.group.pattern)
        ):
            return True
        if recursive and node.children:
            for child in node.children:
                if self._has_nested_path(child):
                    return True
        return False

    @staticmethod
    def _sorting(item) -> t.Tuple[bool, int, str, bool, int]:
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
        return (
            child.dynamic,
            len(child._children),
            key,
            bool(child.group and child.group.regex),
            type_ * -1,
        )


class Tree:
    def __init__(self) -> None:
        self.root = Node(root=True)
        self.root.level = 0

    def generate(self, groups: t.Iterable[RouteGroup]) -> None:
        for group in groups:
            current = self.root
            for level, part in enumerate(group.parts):
                if part not in current._children:
                    current.add_child(Node(part=part, parent=current))
                current = current._children[part]
                current.level = level + 1

                current.dynamic = part.startswith("<")
                if current.dynamic and not REGEX_PARAM_NAME.match(part):
                    raise ValueError(f"Invalid declaration: {part}")

            current.group = group

    def display(self) -> None:
        """
        Debug tool to output visual of the tree
        """
        self.root.display()

    def render(self) -> t.List[Line]:
        o, f = self.root.render()
        return o + f

    def finalize(self):
        self.root.finalize_children()
