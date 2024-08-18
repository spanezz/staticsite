PYTHON_ENVIRONMENT := PYTHONASYNCDEBUG=1 PYTHONDEBUG=1

check: flake8 mypy

format: pyupgrade autoflake isort black

pyupgrade:
	pyupgrade --exit-zero-even-if-changed --py311-plus ssite $(shell find staticsite tests -name "*.py")

black:
	black ssite staticsite tests

autoflake:
	autoflake --in-place --recursive ssite staticsite tests

isort:
	isort ssite staticsite tests

flake8:
	flake8 ssite staticsite tests

mypy:
	mypy ssite staticsite tests

unittest:
	$(PYTHON_ENVIRONMENT) nose2-3

coverage:
	$(PYTHON_ENVIRONMENT) nose2-3 --coverage staticsite --coverage-report html 

.PHONY: check pyupgrade black mypy unittest coverage

