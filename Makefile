.PHONY: test lint audit
test:
	pytest --cov=app --cov-report=term-missing
lint:
	ruff check app tests
audit:
	pip-audit -r requirements.txt
