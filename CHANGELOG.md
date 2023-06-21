# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2023-06-21

### Changed
- Include maplibre 3.1.0 assets as files in the project, instead of using a CDN

## [0.2.0] - 2022-11-17
### Added
- `--publish-address` flag to specify the URL prefix of the map
- `--name-tags` flag to specify name tags in single-step map generation
- `--stopwords` flag to specify stopwordss in single-step map generation

### Changed
- Show an error when the target folder is not empty
- Automatically put the OSM contribution note in the generated map
### Fixed
- Responsive layout, now working on mobile
## [0.1.0] - 2022-11-16

### Added
- First release