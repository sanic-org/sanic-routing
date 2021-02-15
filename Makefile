pretty:
	black --line-length 79 sanic_routing tests
	isort --line-length 79 sanic_routing tests --profile=black
