import typing as t
from logging import getLogger

from .group import RouteGroup
from .line import Line
from .patterns import REGEX_PARAM_NAME

logger = getLogger("sanic.root")


class Node:
    def __init__(
        self, part: str = "", root: bool = False, parent=None, router=None
    ) -> None:
        self.root = root
        self.part = part
        self.parent = parent
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
        # indent = (self.level + 1) * 2 - 3 + self.offset
        siblings = self.parent.children if self.parent else {}
        prev_node: t.Optional[Node] = None
        next_node: t.Optional[Node] = None
        current: t.Optional[Node] = None
        first_sibling: t.Optional[Node] = None

        if not self.first:
            first_sibling = list(siblings.values())[0]

        for child in siblings.values():
            if current is self:
                next_node = child
                break
            prev_node = current
            current = child

        if self.parent:
            self.base_indent = (
                self.parent.base_indent
                + (not self.parent.dynamic)
                + bool(self.parent.groups)
            )

        if not self.first and self.groups:
            # self.base_indent += bool(prev_node and prev_node.group)
            # self.base_indent += bool(prev_node)
            self.base_indent += 1

        indent = self.base_indent
        delayed: t.List[Line] = []
        final: t.List[Line] = []
        src: t.List[Line] = []

        src.append(Line("", indent))
        src.append(Line(f"# {self}", indent))
        src.append(
            Line(
                f"# indent={self.base_indent} // parent={self.parent.base_indent}",
                indent,
            )
        )
        level = self.level
        idx = level - 1

        # len_check = ""
        return_bump = not self.dynamic

        # if self.first:
        #     if level == 0:
        #         if self.group:
        #             src.append(Line("if True:", indent))
        #         else:
        #             src.append(Line("if parts[0]:", indent))
        #     else:
        #         operation = ">"
        #         use_level = level
        #         conditional = "if"
        #         if (
        #             self.last
        #             and self.group
        #             and not self.children
        #             and not self.group.requirements
        #         ):
        #             use_level = self.level
        #             operation = "=="
        #             equality_check = True
        #             conditional = "elif"
        #             src.extend(
        #                 [
        #                     Line(f"if num > {use_level}:", indent),
        #                     Line("...", indent + 1)
        #                     if self._has_nested_path(self)
        #                     else Line("raise NotFound", indent + 1),
        #                 ]
        #             )
        #         src.append(
        #             Line(f"{conditional} num {operation} {use_level}:", indent)
        #         )

        if self.first:
            # operation = ">"
            operation = ">="
            conditional = "if"

            # raise Exception([sibling.depth for sibling in siblings.values()])
            if self.groups:
                operation = "==" if self.level == self.parent.depth else ">="
                self.equality_check = operation == "=="

            # if self.last and self.group and not self.group.requirements:
            #     equality_check = True
            #     operation = "=="
            #     conditional = "elif"
            #     src.extend(
            #         [
            #             Line(f"if num > {level}:", indent),
            #             # Line("...", indent + 1)
            #             # if self._has_nested_path(self)
            #             # else Line("raise NotFound", indent + 1),
            #             Line("raise NotFound", indent + 1),
            #         ]
            #     )
            src.append(
                Line(
                    f"{conditional} num {operation} {level}:  # CHECK 1",
                    indent,
                )
            )
            indent += 1
        elif (
            self.last
            and self.groups
            and all(not group.requirements for group in self.groups)
        ):
            if prev_node and prev_node.groups:
                ...
            else:
                operation = (
                    ">="
                    if any(
                        group.depth > self.level
                        for child in self.children.values()
                        for group in child.groups
                    )
                    else "=="
                )
                self.equality_check = operation == "=="
                src.append(
                    Line(f"if num {operation} {level}:  # CHECK 2", indent)
                )
            # delayed.extend(
            #     [
            #         Line(f"else:", indent),
            #         # Line("...", indent + 1)
            #         # if self._has_nested_path(self)
            #         # else Line("raise NotFound", indent + 1),
            #         Line("raise NotFound", indent + 1),
            #     ]
            # )
            if not (prev_node and prev_node.groups):
                indent += 1

        if self.dynamic:
            if not self.parent.children_basketed:
                self.parent.children_basketed = True
                if not self.groups:
                    src.append(Line(f"if num > {level}:  # CHECK 3", indent))
                    self.base_indent += 1
                    indent += 1
                src.append(Line(f"basket[{idx}] = parts[{idx}]", indent))
                # self.parent.apply_offset(-1, False, True)

                # if not self.children:
                #     return_bump -= 1
        else:
            if (
                not self.equality_check
                and self.groups
                and not self.first
                and first_sibling
            ):
                self.equality_check = first_sibling.equality_check
            # if_stmt = (
            #     "if"
            #     if self.first or (first_sibling and not first_sibling.group)
            #     else "elif"
            # )
            if_stmt = "if"
            len_check = (
                f" and num == {self.level}"
                if not self.children and not self.equality_check
                else ""
            )
            if len_check:
                self.equality_check = True
            src.append(
                Line(
                    f'{if_stmt} parts[{idx}] == "{self.part}"{len_check}:  # CHECK 4',
                    indent,
                )
            )
            # if self.children:
            #     return_bump += 1

        # if self.dynamic:
        #     if not self.parent.children_basketed:
        #         self.parent.children_basketed = True
        #         src.append(
        #             Line(f"basket[{level}] = parts[{level}]", indent + 1)
        #         )
        #         self.parent.apply_offset(-1, False, True)

        #         if not self.children:
        #             return_bump -= 1
        # else:
        #     if_stmt = "if" if self.first or self.root else "elif"
        #     len_check = (
        #         f" and num == {self.level}"
        #         if not self.children and not equality_check
        #         else ""
        #     )
        #     src.append(
        #         Line(
        #             f'{if_stmt} parts[{level}] == "{self.part}"{len_check}:',
        #             indent + 1,
        #         )
        #     )
        #     if self.children:
        #         return_bump += 1

        # if self.group:
        #     location = delayed if self.children else src
        #     route_idx: t.Union[int, str] = 0
        #     if self.group.requirements:
        #         route_idx = "route_idx"
        #         self._inject_requirements(
        #             location, indent + return_bump + bool(not self.children)
        #         )
        #     if self.group.params and not self.group.regex:
        #         if not self.last:
        #             return_bump += 1
        #         if self.parent.has_deferred:
        #             return_bump += 1
        #         self._inject_params(
        #             location,
        #             indent + return_bump + bool(not self.children),
        #             not self.parent.children_param_injected,
        #         )
        #         if not self.parent.children_param_injected:
        #             self.parent.children_param_injected = True
        #         if self._has_nested_regex(self):
        #             return_bump += 1
        #     param_offset = bool(self.group.params)
        #     return_indent = (
        #         indent + return_bump + bool(not self.children) + param_offset
        #     )
        #     if self.group.regex:
        #         if self._has_nested_path(self, recursive=False):
        #             location.append(Line("...", return_indent - 1))
        #             return_indent = 2
        #             location = final
        #             self._mark_parents_defer(self.parent)
        #         self._inject_regex(
        #             location,
        #             return_indent,
        #             not self.parent.children_param_injected,
        #         )
        #     if route_idx == 0 and len(self.group.routes) > 1:
        #         route_idx = "route_idx"
        #         for i, route in enumerate(self.group.routes):
        #             if_stmt = "if" if i == 0 else "elif"
        #             location.extend(
        #                 [
        #                     Line(
        #                         f"{if_stmt} method in {route.methods}:",
        #                         return_indent,
        #                     ),
        #                     Line(f"route_idx = {i}", return_indent + 1),
        #                 ]
        #             )
        #         location.extend(
        #             [
        #                 Line("else:", return_indent),
        #                 Line("raise NoMethod", return_indent + 1),
        #             ]
        #         )
        #     routes = "regex_routes" if self.group.regex else "dynamic_routes"
        #     route_return = (
        #         "" if self.group.router.stacking else f"[{route_idx}]"
        #     )
        #     location.extend(
        #         [
        #             Line(
        #                 (
        #                     f"return router.{routes}[{self.group.parts}]"
        #                     f"{route_return}, basket"
        #                 ),
        #                 return_indent,
        #             ),
        #         ]
        #     )
        if self.groups:
            location = delayed if self.children else src
            return_indent = indent + return_bump
            route_idx: t.Union[int, str] = 0

            if not self.equality_check:
                conditional = "elif" if self.children else "if"
                location.append(
                    Line(
                        f"{conditional} num == {level}:  # CHECK 5",
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
                    self._inject_regex(src, return_indent + group_bump, group)
                    group_bump += 1

                else:
                    if group.params:
                        self._inject_params(
                            location,
                            return_indent + group_bump,
                            group
                            # indent + return_bump + bool(not self.children),
                            # not self.parent.children_param_injected,
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
        else:
            # self.base_indent += bool(self.level > 1 or self.first)
            self.base_indent += bool(self.level > 1 or self.first)

        return src, delayed, final

    def add_child(self, child: "Node") -> None:
        self._children[child.part] = child

    def _mark_parents_defer(self, parent):
        parent.has_deferred = True
        if getattr(parent, "parent", None):
            self._mark_parents_defer(parent.parent)

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
                Line("# Return here", indent),
                Line(
                    (
                        f"return router.{routes}[{group.parts}]"
                        f"{route_return}, basket"
                    ),
                    indent,
                ),
            ]
        )

    def _inject_requirements(self, location, indent, group):
        for k, route in enumerate(group):
            # if k == 0:
            #     location.extend(
            #         [
            #             Line(f"if num > {self.level}:", indent),
            #             Line("raise NotFound", indent + 1),
            #         ]
            #     )

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

    # def _inject_params(self, location, indent, first_params):
    def _inject_params(self, location, indent, group):
        lines = []
        # if self.last:
        #     if self.parent.has_deferred:
        #         lines = [
        #             Line(f"if num == {self.level}:", indent - 1),
        #         ]
        #     else:
        #         if self._has_nested_regex(self):
        #             lines = [
        #                 Line(f"if num == {self.level}:", indent),
        #             ]
        #             indent += 1
        #         else:
        #             lines = [
        #                 Line(f"if num > {self.level}:", indent),
        #                 Line("raise NotFound", indent + 1),
        #             ]
        # else:
        #     lines = []
        #     if first_params:
        #         lines.append(
        #             Line(f"if num == {self.level}:", indent - 1),
        #         )
        lines.append(Line("try:", indent))
        for idx, param in group.params.items():
            unquote_start = "unquote(" if group.unquote else ""
            unquote_end = ")" if group.unquote else ""
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
                # Line("except (ValueError, KeyError):", indent),
                Line("except ValueError:", indent),
                Line("pass", indent + 1),
                Line("else:", indent),
            ]
        )

    # def _has_nested_path(self, node, recursive=True):
    #     if node.group and (
    #         (node.group.labels and "path" in node.group.labels)
    #         or (node.group.pattern and r"/" in node.group.pattern)
    #     ):
    #         return True
    #     if recursive and node.children:
    #         for child in node.children.values():
    #             if self._has_nested_path(child):
    #                 return True
    #     return False

    # def _has_nested_regex(self, node, recursive=True):
    #     if node.group and node.group.regex:
    #         return True
    #     if recursive and node.children:
    #         for child in node.children.values():
    #             if self._has_nested_regex(child):
    #                 return True
    #     return False

    def _sorting(self, item) -> t.Tuple[bool, int, str, bool, int]:
        key, child = item

        return (
            bool(child.groups),
            child.dynamic,
            child.depth * -1,
            len(child._children),
            not bool(
                child.groups and any(group.regex for group in child.groups)
            ),
            # type_ * -1,
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
        print(f"{segments=}")
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
                dynamic = False
                dynamic = part.startswith("<")
                if dynamic:
                    if not REGEX_PARAM_NAME.match(part):
                        raise ValueError(f"Invalid declaration: {part}")
                    part = "__dynamic__"
                if part not in current._children:
                    child = Node(part=part, parent=current, router=self.router)
                    child.dynamic = dynamic
                    current.add_child(child)
                current = current._children[part]
                current.level = level + 1

            current.groups.append(group)

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
