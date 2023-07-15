python script to analyze gpx data.

usage:

´´´
usage: GpxAnalyzer [-h] [--gpxFile GPXFILE] [--imageFolder IMAGEFOLDER] [--margin MARGIN] [--shrinkImages] [--out OUT] [--createJekyllMd]
                   [--recreateProjectsFrom RECREATEPROJECTSFROM]

analyses gpx data and gives a pretty output
  it will generate several map files, e.g.
  legs.svg for the legs that are detected in the gpx file
  picture.svg for an interactive map with the pictures taken on the trip

optional arguments:
  -h, --help            show this help message and exit
  --gpxFile GPXFILE     gpx file to analyze, if provided requies image folder parameter; if not provided will regenerate existing tracks
  --imageFolder IMAGEFOLDER
                        folder of the images to include into the map file
  --margin MARGIN       margin to the side of the map from the track [° of latitude/longitude]
  --shrinkImages        shrink the images to use PILs thumbnails instead
  --out OUT             output destination, everything will be copied there
  --createJekyllMd      create a jekyll compatible md file instead of an index.html
  --recreateProjectsFrom RECREATEPROJECTSFROM
                        recreate projects from this location#
´´´