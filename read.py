import math
from typing import List
import argparse
from argparse import RawTextHelpFormatter
import shutil
from PIL import Image
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import svgwrite
import os
import json

class Config:
  def __init__(self, margin:float, shrink:bool) -> None:
    ## margin to side of map
    self.Margin = margin
    ## whether to shrink images
    self.Shrink = shrink

##
# track point class representing a track point of the gpx data
class trkpnt:
  def __init__(self, lat, lon, ele, time):
    self.lat = float(lat)
    self.lon = float(lon)
    self.ele = float(ele)
    self.time = time
    self.isScaled = False
    self.scaledlat=self.lat
    self.scaledlon=self.lon
    # 2023-07-02T07:14:01.154Z
    try:
      self.timestamp = datetime.strptime(self.time,'%Y-%m-%dT%H:%M:%SZ')+timedelta(hours=2, minutes=0)
    except:
      self.timestamp = datetime.strptime(self.time,'%Y-%m-%dT%H:%M:%S.%fZ')+timedelta(hours=2, minutes=0)
    self.date = self.time.split("T")[0]
    
  def scale(self, topleft, botright, size):
    self.scaledlon = (self.lon-topleft[1])*(size[1]/(-topleft[1]+botright[1]))
    self.scaledlat = (topleft[0]-self.lat)*size[0]/(topleft[0]-botright[0])  
    self.isScaled = True  
    return True
  
  def __repr__(self):
    return "[{lat}, {lon}, {ele}: {time}]".format(lat=self.scaledlat, lon=self.scaledlon, ele =self.ele, time = self.timestamp)
  
##
# waypoint class represening a waypoint of the gpx data  
class wypnt(trkpnt):
  def __init__(self, lat, lon, ele, time, desc):
    super().__init__(lat, lon, ele, time)
    self.desc =desc
    
  def __repr__(self):
    return self.desc + "-" + super().__repr__()

##
# track segment defined by origin track point and target track point    
class Segment:
  def __init__(self, origin:trkpnt, target:trkpnt):
    self.orig=origin
    self.target=target
    # dist in cm
    self.distance=math.sqrt((origin.lon-target.lon)**2+(origin.lat-target.lat)**2)/2*11113900
    self.time = (target.timestamp-origin.timestamp).total_seconds()
    # speed cm/s
    self.speed = self.distance/self.time
    self.avele = (origin.ele+target.ele)*0.5
  def __repr__(self):
    return "speed: "+str(self.speed)
  
class MapCreator:
  def __init__(self) -> None:
    # lat / long
    self.topleft=[47.3616,11.3420]
    self.botright=[47.1141,11.7904]
    self.scaling = 1/80500
    self.cmperdegree = 11113900
    self.size=[625 , 534]
    # margin of the map around the tour
    self.margin = 0.005
    # whether to shrink the images
    self.shrink = False
    # name of the tour from gpx file
    self.tourname = ""

  def getTrackName(self, gpxData):
    ns = {"":"http://www.topografix.com/GPX/1/1"}
    tree = ET.parse(gpxData)
    root = tree.getroot()
    return root.find("trk", namespaces=ns).find("name", namespaces=ns).text

  ##
  # parse track points
  def parsetrkpoints(self, gpxData):
    waypoints=[]
    trackpoints=[]
    ns = {"":"http://www.topografix.com/GPX/1/1"}
    tree = ET.parse(gpxData)
    root = tree.getroot()
    for wpt in root.findall('wpt',namespaces=ns):
      waypoints.append(wypnt(wpt.get("lat"),wpt.get("lon"), wpt.find("ele", namespaces=ns).text,wpt.find("time", namespaces=ns).text,wpt.find("desc", namespaces=ns).text))
      #print(wypnt(wpt.get("lat"),wpt.get("lon"), wpt.find("ele", namespaces=ns).text,wpt.find("time", namespaces=ns).text,wpt.find("desc", namespaces=ns).text))
    
    for tpt in root.find("trk", namespaces=ns).find("trkseg", namespaces=ns).findall('trkpt', namespaces=ns):
      trackpoints.append(trkpnt(tpt.get("lat"),tpt.get("lon"), tpt.find("ele", namespaces=ns).text,tpt.find("time", namespaces=ns).text))
    
    return waypoints, trackpoints

  ##
  # get a segment from the list of segments based on the timestamp  
  def getSegment(self, segments, timestamp):
    # TODO segments are sorted by time -> binary search? 
    if (timestamp==None):
      return None
    for segment in segments:
      if (segment.orig.timestamp<timestamp and segment.target.timestamp> timestamp):
        return segment
    return None

  ##
  # gets a map link for the given track points
  def getMapLink(self, trps:List[trkpnt]):
    # get min & max long/lat from track points
    minlat, minlong = 360, 360 
    maxlat, maxlong = -360, -360
    for trp in trps:
      minlat = min(minlat, trp.lat)
      minlong = min(minlong, trp.lon)
      maxlat = max(maxlat, trp.lat)
      maxlong = max(maxlong, trp.lon)
    
    # do scaling based on min/max values
    # TODO better scaling based on size?
    scale = max((maxlong-minlong)*400000,(maxlat-minlat)*400000)
    self.scaling=scale

    # add a margin
    minlong = round(minlong,14)-self.margin
    minlat = round(minlat,14)-self.margin
    maxlat = round(maxlat,14)+self.margin
    maxlong = round(maxlong,14)+self.margin
    # update for selfscaling of trackpoints
    self.botright=[minlat, maxlong]
    self.topleft=[maxlat, minlong]
    # build url for streetmap
    return "https://render.openstreetmap.org/cgi-bin/export?bbox={botleftlong:.15f},{botleftlat:.15f},{toprightlong:.15f},{toprightlat:.15f}&scale={scale}&format=svg ".format(botleftlong=minlong, botleftlat=minlat, toprightlong=maxlong, toprightlat=maxlat, scale=round(scale))

  def createImageMap(self, map, pnts:List[trkpnt], segments:List[Segment], imageFolder, out):
    print("creating picture map")
    print("shrinking images: ", self.shrink)
    dwg = svgwrite.Drawing(os.path.join(out,'picture.svg'),  viewBox=('0 0 {y} {x}'.format(x=self.size[0], y=self.size[1])))
    for segment in segments: 
      dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="2",stroke=svgwrite.rgb(10, 10, 10, '%')))
      contentscript = """
  // shows an image from source
  function show_image(src, width, height, alt, x, y) 
  {
    if (window._shownImages.has(src)){
      console.log(src  + " alread open");
      return;
    }
    var svg = document.getElementsByTagName("svg")[0];
    var svgimg = document.createElementNS("http://www.w3.org/2000/svg","image"); 
    svgimg.setAttributeNS(null,"height",height); 
    svgimg.onclick=function(){
      svg.getElementById(src).remove(svgimg)
      window._shownImages.delete(src)
      console.log("closing " + src);
    }; 
    svgimg.setAttributeNS(null,"id",src), svgimg.setAttributeNS(null,"width",width);
    svgimg.setAttributeNS("http://www.w3.org/1999/xlink","href", src);
    svgimg.setAttributeNS(null,"x",x);
    svgimg.setAttributeNS(null,"y",y);
    svgimg.setAttributeNS(null, "visibility", "visible");
    svg.append(svgimg);
    window._shownImages.add(src);
  }
  """  
    dwg.add(svgwrite.container.Script(content=contentscript))
    initscript = """
      function init(){
        window._shownImages = new Set();
      }
      init();
      """  
    dwg.add(svgwrite.container.Script(content=initscript))
    try:
      for root, dirs, files in os.walk(imageFolder):
        for f in files:
          if "jpg" in f:
            segment = self.getSegment(segments, self.getTimestamp(f))
            if (segment != None):
              x=(segment.orig.scaledlon+segment.target.scaledlon)/2
              y=(segment.orig.scaledlat+segment.target.scaledlat)/2
              imageSize=[400, 400]
              if x+imageSize[1]>self.size[1]:
                x = self.size[1]-imageSize[1]
              if y+imageSize[0]>self.size[0]:
                y = self.size[0]-imageSize[0]

              dwg.add(svgwrite.shapes.Circle(
                center=(segment.orig.scaledlon,segment.orig.scaledlat),
                r=5,stroke=svgwrite.rgb(10,10,10,"%"),               
                onclick="show_image(\""+f+"\", "+str(imageSize[0])+", "+str(imageSize[1])+", 'image "+f+"',"+ str(x)+","+ str(y)+")"))
              if (not self.recreate and self.shrink):
                image = Image.open(os.path.join(root, f))
                image.thumbnail((400,300))
                image.save(os.path.join(out, f))
              else:
                if not self.recreate:
                  shutil.copyfile(os.path.join(root, f), os.path.join(out, f))
    except Exception as ex:
      print(ex)
    dwg.save()

  def createEleMap(self, map, pnts:List[trkpnt], segments:List[Segment], out):
    print("creating elevation map")
    dwg = svgwrite.Drawing(os.path.join(out,'elevation.svg'), viewBox=('0 0 {y} {x}'.format(x=self.size[0], y=self.size[1])))
    minele = 100000
    maxele = 0 
    for segment in segments:
      if (segment.avele>00):
        minele = min(minele,segment.avele)
        maxele = max(maxele,segment.avele)
    for segment in segments:
      # TODO more complex color scheme? -> new func getColorFor
      dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="2",stroke=self.getColorForElevation(segment.avele, minele, maxele)))
    i =0
    for x in range(int(minele), int(maxele), int((maxele-minele)/5)):
      # TODO use getColorFor
      dwg.add(dwg.line((5,10+i*20),(20,10+i*20),stroke_width="3",stroke=self.getColorForElevation(x, minele, maxele)))
      dwg.add(dwg.text(f"{x} m",insert=(25, 14+i*20)))
      i=i+1
    dwg.save()
  
  def getColorForElevation(self, ele, minele, maxele):
    # TODO more complex color scheme?
    return svgwrite.rgb(min(255,(ele-minele)*255/(maxele-minele)),max(255-(ele-minele)*255/(maxele-minele),0), 0, '%')


  def createSpeedMap(self, map, pnts:List[trkpnt], segments:List[Segment], out):
    print("creating speed map")
    dwg = svgwrite.Drawing(os.path.join(out,'speed.svg'), viewBox=('0 0 {y} {x}'.format(x=self.size[0], y=self.size[1])))
    minspeed = 100000
    maxspeed = 0 
    for segment in segments:
      if segment.speed<200:
        minspeed = min(minspeed,segment.speed)
        maxspeed = max(maxspeed,segment.speed)
    for segment in segments:
      dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="2",stroke=self.getColorForSpeed(segment.speed, minspeed, maxspeed)))
    i=0
    for x in range(int(minspeed), int(maxspeed), int((maxspeed-minspeed)/5)):
      dwg.add(dwg.line((5,10+i*20),(20,10+i*20),stroke_width="3",stroke=self.getColorForSpeed(x, minspeed, maxspeed)))
      dwg.add(dwg.text(f"{x} cm/s",insert=(25, 14+i*20)))
      i=i+1
    dwg.save()

  def getColorForSpeed(self, speed, minspeed, maxspeed):
    # TODO more complex color scheme?
    return svgwrite.rgb(max(255-speed*255/(maxspeed-minspeed),0),min(255,speed*255/(maxspeed-minspeed)), 0, '%')

  def createlegMap(self, map, pnts:List[trkpnt], segments:List[Segment], out):
    print("creating leg map")
    dwg = svgwrite.Drawing(os.path.join(out,'legs.svg'), viewBox=('0 0 {y} {x}'.format(x=self.size[0], y=self.size[1])))
    legcount = 0
    legcolor = [[0,0,0],[255,0,0],[0,255,0],[0,0,255],[120,120,0],[255,0,255]]
    legdates=[]
    legdates.append(segments[0].orig.date)
    for segment in segments:
      if (segment.time>3000):
        legcount=legcount+1
        if not segment.target.date in legdates:
          legdates.append(segment.target.date)
      dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="2",stroke=svgwrite.rgb(legcolor[legcount%6][0],legcolor[legcount%6][1],legcolor[legcount%6][2] , '%')))
    for i in range (0, legcount+1):
      dwg.add(dwg.line((5,10+i*20),(20,10+i*20),stroke_width="3",stroke=svgwrite.rgb(legcolor[i%6][0],legcolor[i%6][1],legcolor[i%6][2] , '%')))
      dwg.add(dwg.text(f"{legdates[i]}",insert=(25, 14+i*20)))
    dwg.save()   
    
  def createMaps(self, gpxData, imageFolder, out, cfg:Config):
    pnts, trps = self.parsetrkpoints(gpxData)
    url = self.getMapLink(trps)
    targetMap = os.path.join(out, "map.svg")
    # manual intervention neccessary, OSM doesn't like getting it via code
    if not self.recreate:
      print("download file and place the resulting file as map.svg in the working dir:")
      print(url)
      print("you might need to download any map manually first for openstreetmap to accept the link")
      input("press enter once done")

      if not os.path.exists(out):
        os.makedirs(out)
      shutil.copyfile("map.svg", targetMap)
      shutil.copyfile(gpxData, os.path.join(out, os.path.basename(gpxData)))
      with open(os.path.join(out, "cfg.json"),"w") as f:
          f.write(json.dumps(cfg.__dict__))
    tree = ET.parse(targetMap)
    root = tree.getroot()
    self.size = [int(root.get("height").replace("pt","")), int(root.get("width").replace("pt",""))]
    print ("map size: ", self.size)
    map = svgwrite.image.Image("map.svg",insert=(0,0), size=(self.size[1],self.size[0]))
    # scale all trackpoints to the map
    trps = [trp for trp in trps if trp.scale(self.topleft, self.botright, self.size)]
    
    segments=[]
    for i in range (0, len(trps)-1):
      segments.append(Segment(trps[i],trps[i+1]))
  
    self.createPage(out)
    self.createImageMap(map, pnts, segments, imageFolder, out)
    self.createEleMap(map, pnts, segments, out)
    self.createSpeedMap(map, pnts, segments, out)
    self.createlegMap(map, pnts, segments, out)

  def createPage(self, out):
    lines = open("template.html","r").readlines()
    newLines = []
    for line in lines:
      line = line.replace("{{TOURTITLE}}",self.tourname)
      newLines.append(line)
    open(os.path.join(out,"index.html"),"w").writelines(newLines)


  # get the timestamp of the filename  
  def getTimestamp(self, name):
    try:
      return datetime.strptime(name,'%Y%m%d_%H%M%S.jpg')
    except :
      pass
    try:
      return datetime.strptime(name,'IMG_%Y%m%d_%H%M%S_%f.jpg')
    except :
      pass
    try:
      return datetime.strptime(name,'MVIMG_%Y%m%d_%H%M%S_%f.jpg')
    except :
      pass
    try:
      return datetime.strptime(name,'PXL_%Y%m%d_%H%M%S%f.jpg')+timedelta(hours=2, minutes=0)
    except :
      pass
    try:
      return datetime.strptime(name,'PXL_%Y%m%d_%H%M%S%f.NIGHT.jpg')+timedelta(hours=2, minutes=0)
    except :
      pass
    try:
      return datetime.strptime(name,'PXL_%Y%m%d_%H%M%S%f.PANO.jpg')+timedelta(hours=2, minutes=0)
    except:
      print ("could not match date of image name:", name)

  def main(self, gpxFile, imageFolder, out, cfg:Config, recreate=False):
    self.tourname = self.getTrackName(gpxFile)
    if out is None:
      out = "./tours/" + self.tourname
    self.margin = cfg.Margin
    self.shrink = cfg.Shrink
    self.recreate = recreate
    self.createMaps(gpxFile, imageFolder, out, cfg)

def recreateExistingProjects(toursDir):
  for root, dirs, _ in os.walk(toursDir):
    if root == toursDir:
      for dir in dirs:
        print("recreating tour " + dir)
        gpxFile = ""
        cfgFile = ""
        projDir = os.path.join(root, dir)
        for r, _, files  in os.walk(projDir):
          for file in files:
            if file.lower().endswith("gpx"):
              gpxFile = os.path.join(projDir, file) 
            if file.lower()=="cfg.json":
              cfgFile = os.path.join(projDir, file) 
        mc = MapCreator()
        # create cfg with defaults
        cfg = Config(0.005, True)
        with open(cfgFile, "r") as f:
          s = f.read()
          # override saved config
          cfg.__dict__ = json.loads(s)
        mc.main(gpxFile, projDir, projDir, cfg, recreate=True)

if __name__=="__main__":
  parser = argparse.ArgumentParser(prog="GpxAnalyzer", description="""analyses gpx data and gives a pretty output
  it will generate several map files, e.g.\r
  legs.svg for the legs that are detected in the gpx file\r
  picture.svg for an interactive map with the pictures taken on the trip\r
  elevation.svg for a display of elevation""", epilog="", formatter_class=RawTextHelpFormatter)  
  parser.add_argument("--gpxFile", help="gpx file to analyze, if provided requies image folder parameter; if not provided will regenerate existing tracks")
  parser.add_argument("--imageFolder", help="folder of the images to include into the map file")
  parser.add_argument("--margin", help="margin to the side of the map from the track [° of latitude/longitude]", default=0.005, type=float)
  parser.add_argument("--shrinkImages", help="shrink the images to use PILs thumbnails instead", action='store_true')
  parser.add_argument("--out", help="output destination, everything will be copied there")
  args = parser.parse_args()
  if args.gpxFile is not None:
    cfg = Config(args.margin, args.shrinkImages)
    out = args.out
    mc = MapCreator()
    mc.main(args.gpxFile, args.imageFolder, out, cfg)
  else:
    recreateExistingProjects("./tours")
  
