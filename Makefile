.PHONY : help
help:
	@echo 'Usage: make <subcommand>'
	@echo ''
	@echo 'Subcommands:'
	@echo '    install       Install locally'

.PHONY : install
install:
	python3 -m pip install .

.PHONY : bundle_fe
bundle_fe:
	cd frontend && npm install && npm run build


.PHONY : test
test:
	python3 -m pip install -e ".[testing]"
	python3 -m pytest --cov=static_osm_indexer --cov-report html tests/

.PHONY : lint
lint:
	python3 -m pip install -e ".[linting]"
	python3 -m black static_osm_indexer
	cd frontend && npm run prettier
