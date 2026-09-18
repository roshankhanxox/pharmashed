.PHONY: setup fixtures data-check run run-strict freeze checks fhir fhir-validate \
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
	@echo "TODO M03-M04: validate consumption, sites"

run:
	@echo "TODO M08-M11: engine run (dev mode) -> data/build/"

run-strict:
	@echo "TODO M08-M11: engine run (strict mode)"

freeze:
	@echo "TODO M11: strict run -> data/frozen/ + git tag"

checks:
	@echo "TODO M12: consistency checks against frozen predictions"

fhir:
	@echo "TODO M14: build FHIR bundles"

fhir-validate:
	@echo "TODO M15: run HL7 validator"

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
