# Static OSM indexer

This is a collection of scripts that can process data extracts from OpenStreetMap (PBF files) allowing the creation of __static sites__ (that is, a bunch of file hosted without any backend processing) to do a few useful operations:

* locate addresses and places based on an user query
* TODO: nearest neighbor
* TODO: routing

## Installation

Activate the virtual environment and then:

```
pip install static_osm_indexer
```

this will make a set of CLI utilities all prefixed with `soi_` available.

## Extract named locations

Run INSERT COMMAND HERE, this will generate a file in which every line is a JSON reporting a name and EPSG:4326 coordinates

By default it will extract the `name` tag which generally corresponds to the local name, but you can add specific locales, e.g. with `--tags 'name,name:it'` you will get local names and Italian names when available.

## Index named locations