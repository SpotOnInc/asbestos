.PHONY: tests docs docs_clean

tests:
	poetry run pytest

docs:
	if [ -d ".docsvenv" ]; \
	then \
		.docsvenv/bin/mkdocs serve; \
	else \
		echo "Docs environment not found. Please wait..." \
		&& /usr/bin/env python3 -m venv .docsvenv \
		&& .docsvenv/bin/python -m pip install --upgrade pip \
		&& .docsvenv/bin/python -m pip install wheel \
		&& .docsvenv/bin/python -m pip install -r docs/requirements.txt \
		&& .docsvenv/bin/mkdocs serve; \
	fi

docs_clean:
	@echo "Removing docs environment..." && rm -rf .docsvenv
