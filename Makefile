# Asset Intelligence — Day 7 targets. eval lands with Day 8 (eval/run.py).
# Windows without make: use the `python -m ...` equivalents from
# AGENT_BUILD_GUIDE.md / AGENTS.md.
.PHONY: dev run test verify-meta-only lint demo

dev:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

run:
	docker compose up --build

test:
	python -m pytest tests/ -v

# app/ only, matching secret-scan.yml; tests/ is covered by
# tests/test_no_openai.py, which scans both trees minus itself.
verify-meta-only:
	! grep -r "import openai\|from openai" --include="*.py" app/
	! grep -rE "import (anthropic|cohere)|from (anthropic|cohere)" --include="*.py" app/
	! grep -rE "^\s*(openai|anthropic|cohere|streamlit|chromadb|faiss[^ ]*|pinecone)" requirements.txt requirements-dev.txt
	@echo "Meta-only OK"

lint:
	ruff check app/ tests/

demo: run
