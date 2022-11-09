.PHONY : help
help:
	@echo 'Usage: make <subcommand>'
	@echo ''
	@echo 'Subcommands:'
	@echo '    install       Install locally'

.PHONY : install
install:
	python3 -m pip install .


.PHONY : test
test:
	python3 -m pip install -e ".[testing]"
	python3 -m pytest --cov=static_osm_indexer --cov-report html tests/


