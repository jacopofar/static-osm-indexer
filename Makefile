.PHONY: help
help:
	@echo 'Usage: make <subcommand>'
	@echo ''
	@echo 'Subcommands:'
	@echo '    install       Install locally'

.PHONY: install
install:
	python3 -m pip install .


.PHONY: test
test:
	python3 -m pip install -e ".[testing]"
	python3 -m pytest --cov=static_osm_indexer --cov-report html tests/

.PHONY: test-fe
test-fe:
	cd frontend && npm install && npm test


.PHONY: lint
lint:
	python3 -m pip install -e ".[testing]"
	python3 -m black static_osm_indexer
	python3 -m mypy --strict --explicit-package-bases static_osm_indexer

.PHONY: lint-fe
lint-fe:
	cd frontend && npm run prettier

.PHONY: update_bundled_build
update_bundled_build:
	cd frontend && npm install
	cd frontend && npm run build
	cp frontend/text_search.bundle.js static_osm_indexer/static_assets