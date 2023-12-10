PYTEST = pytest -rs sanic_routing tests -vv --cache-clear --flake8

.PHONY: test
test:
	${PYTEST}

.PHONY: test-cov
test-cov:
	${PYTEST} --cov sanic_routing

.PHONY: fix
fix:
	ruff check sanic_routing --fix

.PHONY: format
format:
	ruff format sanic_routing

.PHONY: pretty
pretty: fix format
