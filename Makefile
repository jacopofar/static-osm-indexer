.PHONY : help
help:
	@echo 'Usage: make <subcommand>'
	@echo ''
	@echo 'Subcommands:'
	@echo '    install       Install Python-Markdown locally'
	@echo '    build         Build a source distribution'

.PHONY : install
install:
	python3 -m pip install .


.PHONY : build
build:
	rm -rf build
	rm -rf dist
	python3 -m build