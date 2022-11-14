# Static OSM indexer

__NOTE__ this project is not production ready at all,maybe never will, but it is still probably very useful.

This is a collection of scripts that can process data extracts from OpenStreetMap (PBF files) allowing the creation of __static sites__ (that is, a bunch of file hosted without any backend processing) to do a few useful operations:

* locate addresses and places based on an user query
* TODO: nearest neighbor
* TODO: routing

## Installation

Activate the virtual environment and then:

~~```pip install static_osm_indexer```~~

```
make install
```

this will make a set of CLI utilities, all prefixed with `soi_`, available. The library can also be used programmatically.

# Generate a map, single step

This command will generate a fully static map from a PBF extract

```soi_generate_full_map italy-latest.osm.pbf 3.8,36.2,20.2,47.8 test_italy_all```

it needs the name of the folder where to store it and the bounding box.

## Extract named locations

Run `soi_list_named_locations`, this will generate a file in which every line is a JSON with a `name` field and `lat`, `lon` coordinates (as EPSG:4326).

By default it will extract the `name` tag which generally corresponds to the local name, but you can add specific locales, for example with `--tags 'name,name:it'` you will get local names and Italian names when available. Duplicates are ignored.

## Index named locations

Once you have a file with the list of locations you need to index it using `soi_index_location_names`. This command requires an output folder for the output, and will rearrange the large location names file into smaller files quicker to retrieve on the fly. In this folder a file called `index_metadata.json` contains the metadata needed by the frontend to use the index.

The default config is fine for most cases, but there are two improvements you may want to look into:

* `--stopwords` allows you to ignore words that are very common in addresses, for example the word for *street* in your language. Using it you can create a more balanced index.

* `--token_length` is the amount of characters to be retrieved before fetching a file. By default 3, if you are processing Chinese or Japanese you should set it to 1 given the different statistical distribution of ideograms.
