python script to analyze gpx data.

usage:

´´´
usage: GpxAnalyzer [-h] [--out OUT] [--createJekyllMd] {new,recreate} ...

analyses gpx data and gives a pretty output
  it will generate several map files, e.g.
  legs.svg for the legs that are detected in the gpx file
  picture.svg for an interactive map with the pictures taken on the trip
  elevation.svg for a display of elevation

positional arguments:
  {new,recreate}
    new             create a new tracks
    recreate        recreate existing tracks

optional arguments:
  -h, --help        show this help message and exit
  --out OUT         output destination, everything will be copied there
  --createJekyllMd  create a jekyll compatible md file instead of an index.html

Subparser 'new'
usage: GpxAnalyzer new [-h] [--margin MARGIN] [--shrinkImages] gpxFile imageFolder

positional arguments:
  gpxFile          gpx file to analyze, if provided requies image folder parameter
  imageFolder      folder of the images to include into the map file

optional arguments:
  -h, --help       show this help message and exit
  --margin MARGIN  margin to the side of the map from the track [° of latitude/longitude]
  --shrinkImages   shrink the images to use PILs thumbnails instead

Subparser 'recreate'
usage: GpxAnalyzer recreate [-h] recreateProjectsFrom

positional arguments:
  recreateProjectsFrom  recreate projects from this location

optional arguments:
  -h, --help            show this help message and exit
´´´