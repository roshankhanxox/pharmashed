.PHONY: setup fixtures data-check run run-strict freeze checks fhir fhir-validate release \
        hapi-up api web eval-assistant test demo-build

setup:
	uv sync
	cd web && pnpm install
	@echo "TODO M15: download HL7 FHIR validator jar into fhir/validator/"

fixtures:
	uv run python scripts/make_fixtures.py
	cd web && pnpm run gen:types

data-check:
	uv run pharmashed params check
	uv run pharmashed consumption check
	@echo "TODO M04: validate sites"

run:
	uv run pharmashed run --mode dev --out data/build

run-strict:
	uv run pharmashed run --mode strict --out data/build

freeze:
	uv run pharmashed freeze

checks:
	uv run pharmashed checks

fhir:
	uv run pharmashed fhir

fhir-validate:
	uv run python scripts/validate_fhir.py

release:
	uv run python scripts/make_release.py

hapi-up:
	docker compose -f infra/docker-compose.yml up -d

api:
	@echo "TODO M16: uv run uvicorn pharmashed_api.main:app --reload"

web:
	cd web && pnpm dev

eval-assistant:
	@echo "TODO M17: run assistant eval set"

test:
	uv run pytest
	cd web && pnpm test

demo-build:
	@echo "TODO M24: copy build artefacts into web/public/data"
