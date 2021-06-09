PYTEST = pytest -rs sanic_routing tests -vv --cache-clear --flake8

.PHONY: test
test:
	${PYTEST}

.PHONY: test-cov
test-cov:
	${PYTEST} --cov sanic_routing

.PHONY: pretty
pretty:
	black --line-length 79 sanic_routing tests
	isort --line-length 79 sanic_routing tests --profile=black
