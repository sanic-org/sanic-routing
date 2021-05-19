# Sanic Routing

## Background

Beginning in v21.3, Sanic makes use of this new AST-style router in two use cases:

1. Routing paths; and
2. Routing signals.

Therefore, this package comes with a `BaseRouter` that needs to be subclassed in order to be used for its specific needs. 

Most Sanic users should never need to concern themselves with the details here.

## Basic Example

A simple implementation:

```python
import logging

from sanic_routing import BaseRouter

logging.basicConfig(level=logging.DEBUG)


class Router(BaseRouter):
    def get(self, path, *args, **kwargs):
        return self.resolve(path, *args, **kwargs)


router = Router()

router.add("/<foo>", lambda: ...)
router.finalize()
router.tree.display()
logging.info(router.find_route_src)

route, handler, params = router.get("/matchme", method="BASE", extra=None)
```

The above snippet uses `router.tree.display()` to show how the router has decided to arrange the routes into a tree. In this simple example:

```
<Node: level=0>
    <Node: part=__dynamic__:str, level=1, groups=[<RouteGroup: path=<foo:str> len=1>], dynamic=True>
```

We can can see the code that the router has generated for us. It is available as a string at `router.find_route_src`.

```python
def find_route(path, method, router, basket, extra):
    parts = tuple(path[1:].split(router.delimiter))
    num = len(parts)
    
    # node=1 // part=__dynamic__:str
    if num == 1:  # CHECK 1
        try:
            basket['__matches__'][0] = str(parts[0])
        except ValueError:
            pass
        else:
            # Return 1
            return router.dynamic_routes[('<__dynamic__:str>',)][0], basket
    raise NotFound
```

_FYI: If you are on Python 3.9, you can see a representation of the source after compilation at `router.find_route_src_compiled`_

## What's it doing?

Therefore, in general implementation requires you to:

1. Define a router with a `get` method;
2. Add one or more routes;
3. Finalize the router (`router.finalize()`); and
4. Call the router's `get` method.

_NOTE: You can call `router.finalize(False)` if you do not want to compile the source code into executable form. This is useful if you only intend to review the generated output._

Every time you call `router.add` you create one (1) new `Route` instance. Even if that one route is created with multiple methods, it generates a single instance. If you `add()` another `Route` that has a similar path structure (but, perhaps has differen methods) they will be grouped together into a `RouteGroup`. It is worth also noting that a `RouteGroup` is created the first time you call `add()`, but subsequent similar routes will reuse the existing grouping instance.


When you call `finalize()`, it is taking the defined route groups and arranging them into "nodes" in a hierarchical tree. A single node is a path segment. A `Node` instance can have one or more `RouteGroup` on it where the `Node` is the termination point for that path.

Perhaps an example is easier:

```python
router.add("/path/to/<foo>", lambda: ...)
router.add("/path/to/<foo:int>", lambda: ...)
router.add("/path/to/different/<foo>", lambda: ...)
router.add("/path/to/different/<foo>", lambda: ..., methods=["one", "two"])
```

The generated `RouteGroup` instances (3):

```
<RouteGroup: path=path/to/<foo:str> len=1>
<RouteGroup: path=path/to/<foo:int> len=1>
<RouteGroup: path=path/to/different/<foo:str> len=2>
```

The generated `Route` instances (4):

```
<Route: path=path/to/<foo:str>>
<Route: path=path/to/<foo:int>>
<Route: path=path/to/different/<foo:str>>
<Route: path=path/to/different/<foo:str>>
```

The Node Tree:

```
<Node: level=0>
    <Node: part=path, level=1>
        <Node: part=to, level=2>
            <Node: part=different, level=3>
                <Node: part=__dynamic__:str, level=4, groups=[<RouteGroup: path=path/to/different/<foo:str> len=2>], dynamic=True>
            <Node: part=__dynamic__:int, level=3, groups=[<RouteGroup: path=path/to/<foo:int> len=1>], dynamic=True>
            <Node: part=__dynamic__:str, level=3, groups=[<RouteGroup: path=path/to/<foo:str> len=1>], dynamic=True>
```

And, the generated source code:

```python
def find_route(path, method, router, basket, extra):
    parts = tuple(path[1:].split(router.delimiter))
    num = len(parts)
    
    # node=1 // part=path
    if num > 1:  # CHECK 1
        if parts[0] == "path":  # CHECK 4
            
            # node=1.1 // part=to
            if num > 2:  # CHECK 1
                if parts[1] == "to":  # CHECK 4
                    
                    # node=1.1.1 // part=different
                    if num > 3:  # CHECK 1
                        if parts[2] == "different":  # CHECK 4
                            
                            # node=1.1.1.1 // part=__dynamic__:str
                            if num == 4:  # CHECK 1
                                try:
                                    basket['__matches__'][3] = str(parts[3])
                                except ValueError:
                                    pass
                                else:
                                    if method in frozenset({'one', 'two'}):
                                        route_idx = 0
                                    elif method in frozenset({'BASE'}):
                                        route_idx = 1
                                    else:
                                        raise NoMethod
                                    # Return 1.1.1.1
                                    return router.dynamic_routes[('path', 'to', 'different', '<__dynamic__:str>')][route_idx], basket
                    
                    # node=1.1.2 // part=__dynamic__:int
                    if num >= 3:  # CHECK 1
                        try:
                            basket['__matches__'][2] = int(parts[2])
                        except ValueError:
                            pass
                        else:
                            if num == 3:  # CHECK 5
                                # Return 1.1.2
                                return router.dynamic_routes[('path', 'to', '<__dynamic__:int>')][0], basket
                    
                    # node=1.1.3 // part=__dynamic__:str
                    if num >= 3:  # CHECK 1
                        try:
                            basket['__matches__'][2] = str(parts[2])
                        except ValueError:
                            pass
                        else:
                            if num == 3:  # CHECK 5
                                # Return 1.1.3
                                return router.dynamic_routes[('path', 'to', '<__dynamic__:str>')][0], basket
    raise NotFound
```

## Special cases

The above example only shows routes that have a dynamic path segment in them (example: `<foo>`). But, there are other use cases that are covered differently:

1. *fully static paths* - These are paths with no parameters (example: `/user/login`). These are basically matched against a key/value store.
2. *regex paths* - If a route as a single regular expression match, then the whole route will be matched via regex. In general, this happens inline not too dissimilar than what we see in the above example.
3. *special regex paths* - The router comes with a special `path` type (example: `<foo:path>`) that can match on an expanded delimiter. This is also true for any regex that uses the path delimiter in it. These cannot be matched in the normal course since they are of unknown length.

## What's next?

The current plan is for this code to live outside of the main project, and be merged into `sanic-org/sanic` for the Sanic 21.9 release.
