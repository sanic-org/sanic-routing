import typing as t
from logging import getLogger

from .group import RouteGroup
from .line import Line
from .patterns import REGEX_PARAM_NAME

logger = getLogger("sanic.root")


class Node:
    def __init__(
        self,
        part: str = "",
        root: bool = False,
        parent=None,
        router=None,
        param=None,
    ) -> None:
        self.root = root
        self.part = part
        self.parent = parent
        self.param = param
        self._children: t.Dict[str, "Node"] = {}
        self.children: t.Dict[str, "Node"] = {}
        self.level = 0
        self.base_indent = 0
        self.offset = 0
        self.groups: t.List[RouteGroup] = []
        self.dynamic = False
        self.first = False
        self.last = False
        self.children_basketed = False
        self.children_param_injected = False
        self.has_deferred = False
        self.equality_check = False
        self.unquote = False
        self.router = router

    def __str__(self) -> str:
        internals = ", ".join(
            f"{prop}={getattr(self, prop)}"
            for prop in ["part", "level", "groups", "dynamic"]
            if getattr(self, prop) or prop in ["level"]
        )
        return f"<Node: {internals}>"

    def __repr__(self) -> str:
        return str(self)

    @property
    def ident(self) -> str:
        prefix = (
            f"{self.parent.ident}."
            if self.parent and not self.parent.root
            else ""
        )
        return f"{prefix}{self.idx}"

    @property
    def idx(self) -> int:
        if not self.parent:
            return 1
        return list(self.parent.children.keys()).index(self.part) + 1

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
        siblings = self.parent.children if self.parent else {}
        # prev_node: t.Optional[Node] = None
        # next_node: t.Optional[Node] = None
        current: t.Optional[Node] = None
        first_sibling: t.Optional[Node] = None

        if not self.first:
            first_sibling = list(siblings.values())[0]

        for child in siblings.values():
            if current is self:
                # next_node = child
                break
            # prev_node = current
            current = child

        self.base_indent = (
            bool(self.level >= 1 or self.first) + self.parent.base_indent
            if self.parent
            else 0
        )

        indent = self.base_indent
        delayed: t.List[Line] = []
        final: t.List[Line] = []
        src: t.List[Line] = []

        src.append(Line("", indent))
        src.append(Line(f"# node={self.ident} // part={self.part}", indent))

        level = self.level
        idx = level - 1

        return_bump = not self.dynamic

        operation = ">"
        conditional = "if"

        if self.groups:
            operation = "==" if self.level == self.parent.depth else ">="
            self.equality_check = operation == "=="

        src.append(
            Line(
                f"{conditional} num {operation} {level}:  # CHECK 1",
                indent,
            )
        )
        indent += 1

        if self.dynamic:
            self._inject_param_check(src, indent, idx)
            indent += 1

        else:
            if (
                not self.equality_check
                and self.groups
                and not self.first
                and first_sibling
            ):
                self.equality_check = first_sibling.equality_check

            if_stmt = "if"
            len_check = (
                f" and num == {self.level}"
                if not self.children and not self.equality_check
                else ""
            )

            self.equality_check = self.equality_check or bool(len_check)

            src.append(
                Line(
                    f'{if_stmt} parts[{idx}] == "{self.part}"{len_check}:'
                    "  # CHECK 4",
                    indent,
                )
            )
            self.base_indent += 1

        if self.groups:
            return_indent = indent + return_bump
            route_idx: t.Union[int, str] = 0
            location = delayed

            if not self.equality_check:
                conditional = "elif" if self.children else "if"
                operation = "=="
                location.append(
                    Line(
                        f"{conditional} num {operation} {level}:  # CHECK 5",
                        return_indent,
                    )
                )
                return_indent += 1

            for group in sorted(self.groups, key=self._group_sorting):
                group_bump = 0

                if group.requirements:
                    route_idx = "route_idx"
                    self._inject_requirements(
                        location, return_indent + group_bump, group
                    )

                if group.regex:
                    self._inject_regex(
                        location, return_indent + group_bump, group
                    )
                    group_bump += 1

                if route_idx == 0 and len(group.routes) > 1:
                    route_idx = "route_idx"
                    self._inject_method_check(
                        location, return_indent + group_bump, group
                    )

                self._inject_return(
                    location, return_indent + group_bump, route_idx, group
                )

        return src, delayed, final

    def add_child(self, child: "Node") -> None:
        self._children[child.part] = child

    def _mark_parents_defer(self, parent):
        parent.has_deferred = True
        if getattr(parent, "parent", None):
            self._mark_parents_defer(parent.parent)

    def _inject_param_check(self, location, indent, idx):
        unquote_start = "unquote(" if self.unquote else ""
        unquote_end = ")" if self.unquote else ""
        lines = [
            Line("try:", indent),
            Line(
                f"basket['__matches__'][{idx}] = "
                f"{unquote_start}{self.param.cast.__name__}(parts[{idx}])"
                f"{unquote_end}",
                indent + 1,
            ),
            Line("except ValueError:", indent),
            Line("pass", indent + 1),
            Line("else:", indent),
        ]
        self.base_indent += 1

        location.extend(lines)

    def _inject_method_check(self, location, indent, group):
        for i, route in enumerate(group.routes):
            if_stmt = "if" if i == 0 else "elif"
            location.extend(
                [
                    Line(
                        f"{if_stmt} method in {route.methods}:",
                        indent,
                    ),
                    Line(f"route_idx = {i}", indent + 1),
                ]
            )
        location.extend(
            [
                Line("else:", indent),
                Line("raise NoMethod", indent + 1),
            ]
        )

    def _inject_return(self, location, indent, route_idx, group):
        routes = "regex_routes" if group.regex else "dynamic_routes"
        route_return = "" if group.router.stacking else f"[{route_idx}]"
        location.extend(
            [
                Line(f"# Return {self.ident}", indent),
                Line(
                    (
                        f"return router.{routes}[{group.segments}]"
                        f"{route_return}, basket"
                    ),
                    indent,
                ),
            ]
        )

    def _inject_requirements(self, location, indent, group):
        for k, route in enumerate(group):
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

    def _inject_regex(self, location, indent, group):
        location.extend(
            [
                Line(
                    (
                        "match = router.matchers"
                        f"[{group.pattern_idx}].match(path)"
                    ),
                    indent,
                ),
                Line("if match:", indent),
                Line(
                    "basket['__params__'] = match.groupdict()",
                    indent + 1,
                ),
            ]
        )

    def _sorting(self, item) -> t.Tuple[bool, bool, int, int, int, bool, str]:
        key, child = item
        type_ = 0
        if child.dynamic:
            type_ = child.param.priority

        return (
            bool(child.groups),
            child.dynamic,
            type_ * -1,
            child.depth * -1,
            len(child._children),
            not bool(
                child.groups and any(group.regex for group in child.groups)
            ),
            key,
        )

    def _group_sorting(self, item) -> t.Tuple[int, ...]:
        def get_type(segment):
            type_ = 0
            if segment.startswith("<"):
                key = segment[1:-1]
                if ":" in key:
                    key, param_type = key.split(":", 1)
                    try:
                        type_ = list(self.router.regex_types.keys()).index(
                            param_type
                        )
                    except ValueError:
                        type_ = len(list(self.router.regex_types.keys()))
            return type_ * -1

        segments = tuple(map(get_type, item.parts))
        return segments

    @property
    def depth(self):
        if not self._children:
            return self.level
        return max(child.depth for child in self._children.values())


class Tree:
    def __init__(self, router) -> None:
        self.root = Node(root=True, router=router)
        self.root.level = 0
        self.router = router

    def generate(self, groups: t.Iterable[RouteGroup]) -> None:
        for group in groups:
            current = self.root
            for level, part in enumerate(group.parts):
                param = None
                dynamic = part.startswith("<")
                if dynamic:
                    if not REGEX_PARAM_NAME.match(part):
                        raise ValueError(f"Invalid declaration: {part}")
                    part = f"__dynamic__:{group.params[level].label}"
                    param = group.params[level]
                if part not in current._children:
                    child = Node(
                        part=part,
                        parent=current,
                        router=self.router,
                        param=param,
                    )
                    child.dynamic = dynamic
                    current.add_child(child)
                current = current._children[part]
                current.level = level + 1

            current.groups.append(group)
            current.unquote = current.unquote or group.unquote

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
