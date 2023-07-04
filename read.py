import math
from typing import List
# lat / long
topleft=[47.3616,11.3420]
# lat / long
botright=[47.1141,11.7904]
scaling = 1/80500
cmperdegree = 11113900
size=[625 , 534]

#     x
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import svgwrite
import os

##
# track point class representing a track point of the gpx data
class trkpnt:
  def __init__(self, lat, lon, ele, time):
    self.lat = float(lat)
    self.lon = float(lon)
    self.ele = float(ele)
    self.time = time
    self.timestamp = datetime.strptime(self.time,'%Y-%m-%dT%H:%M:%SZ')+timedelta(hours=2, minutes=0)
    
  def scale(self):
    self.scaledlon = (self.lon-topleft[1])*(size[1]/(-topleft[1]+botright[1]))
    self.scaledlat = (topleft[0]-self.lat)*size[0]/(topleft[0]-botright[0])    
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
  def __init__(self, origin, target):
    self.orig=origin
    self.target=target
    self.distance=math.sqrt((origin.scaledlon-target.scaledlon)**2+(origin.scaledlat-target.scaledlat)**2)
    self.time = (target.timestamp-origin.timestamp).total_seconds()
    self.speed= self.distance/self.time
    self.avele = (origin.ele+target.ele)*0.5
  def __repr__(self):
    return "speed: "+str(self.speed)
  

##
# parse track points
def parsetrkpoints(gpxData):
  waypoints=[]
  trackpoints=[]
  ns = {"":"http://www.topografix.com/GPX/1/1"}
  tree = ET.parse(gpxData)
  root = tree.getroot()
  for wpt in root.findall('wpt',namespaces=ns):
    pass
    #waypoints.append(wypnt(wpt.get("lat"),wpt.get("lon"), wpt.find("ele", namespaces=ns).text,wpt.find("time", namespaces=ns).text,wpt.find("desc", namespaces=ns).text))
    #print(wypnt(wpt.get("lat"),wpt.get("lon"), wpt.find("ele", namespaces=ns).text,wpt.find("time", namespaces=ns).text,wpt.find("desc", namespaces=ns).text))
  
  for tpt in root.find("trk", namespaces=ns).find("trkseg", namespaces=ns).findall('trkpt', namespaces=ns):
    trackpoints.append(trkpnt(tpt.get("lat"),tpt.get("lon"), tpt.find("ele", namespaces=ns).text,tpt.find("time", namespaces=ns).text))
  
  return waypoints, trackpoints

##
# get a segment from the list of segments based on the timestamp  
def getSegment(segments, timestamp):
  if (timestamp==None):
    return None
  for segment in segments:
    if (segment.orig.timestamp<timestamp and segment.target.timestamp> timestamp):
      return segment
  return None

##
# gets a map link for the given track points
def getMapLink(trps:List[trkpnt]):
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
  scale = max((maxlong-minlong)*250000,(maxlat-minlat)*250000)
  global scaling, topleft, botright
  scaling=scale

  # add a margin
  margin = 0.01
  minlong = round(minlong,14)-margin
  minlat = round(minlat,14)-margin
  maxlat = round(maxlat,14)+margin
  maxlong = round(maxlong,14)+margin
  # update for selfscaling of trackpoints
  botright=[minlat, maxlong]
  topleft=[maxlat, minlong]
  # build url for streetmap
  return "https://render.openstreetmap.org/cgi-bin/export?bbox={botleftlong},{botleftlat},{toprightlong},{toprightlat}&scale={scale}&format=svg".format(botleftlong=minlong, botleftlat=minlat, toprightlong=maxlong, toprightlat=maxlat, scale=round(scale))

def createImageMap(map, pnts, segments, imageFolder):
  print("creating picture map")
  dwg = svgwrite.Drawing('picture.svg', size=(str(size[0])+"pt",str(size[1])+"pt"), viewBox=('0 0 {y} {x}'.format(x=size[0], y=size[1])))
  dwg.add(map)
  for segment in segments: 
    dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="0.5",stroke=svgwrite.rgb(10, 10, 10, '%')))
    contentscript = """
  // shows an image from source
  function show_image(src, width, height, alt, x, y) 
  {
    var svg = document.getElementsByTagName("svg")[0];
    var svgimg = document.createElementNS("http://www.w3.org/2000/svg","image"); 
    svgimg.setAttributeNS(null,"height",height); 
    svgimg.onclick=function(){
      svg.getElementById(src).remove(svgimg)
    }; 
    svgimg.setAttributeNS(null,"id",src), svgimg.setAttributeNS(null,"width",width);
    svgimg.setAttributeNS("http://www.w3.org/1999/xlink","href", src);
    svgimg.setAttributeNS(null,"x",x);
    svgimg.setAttributeNS(null,"y",y);
    svgimg.setAttributeNS(null, "visibility", "visible");
    svg.append(svgimg);}
  """  
  dwg.add(svgwrite.container.Script(content=contentscript))

  try:
    for root, dirs, files in os.walk(imageFolder):
      for f in files:
        if "jpg" in f:
          segment = getSegment(segments, getTimestamp(f))
          if (segment != None):
            dwg.add(svgwrite.shapes.Circle(
              center=(segment.orig.scaledlon,segment.orig.scaledlat),
              r=5,stroke=svgwrite.rgb(10,10,10,"%"), 
              onclick="show_image(\""+f+"\", 400, 300, 'test image',"+ str(segment.orig.scaledlon)+","+ str(segment.orig.scaledlat)+")"))
  except Exception as ex:
    print(ex)
  dwg.save()

def createEleMap(map, pnts, segments):
  print("creating elevation map")
  dwg = svgwrite.Drawing('elevation.svg', size=(str(size[0])+"pt",str(size[1])+"pt"), viewBox=('0 0 {y} {x}'.format(x=size[0], y=size[1])))
  dwg.add(map)
  minele = 100000
  maxele = 0 
  for segment in segments:
    if (segment.avele>00):
      minele = min(minele,segment.avele)
      maxele = max(maxele,segment.avele)
  for segment in segments:
    dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="0.4",stroke=svgwrite.rgb( min(255,segment.avele*255/(maxele-minele)),max(255-segment.avele*255/(maxele-minele),0), 0, '%')))
  dwg.save()

def createSpeedMap(map, pnts, segments):
  print("creating speed map")
  dwg = svgwrite.Drawing('speed.svg', size=(str(size[0])+"pt",str(size[1])+"pt"), viewBox=('0 0 {y} {x}'.format(x=size[0], y=size[1])))
  dwg.add(map)
  minspeed = 100000
  maxspeed = 0 
  for segment in segments:
    if (segment.speed<0.15):
      minspeed = min(minspeed,segment.speed)
      maxspeed = max(maxspeed,segment.speed)
  for segment in segments:
    dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="0.6",stroke=svgwrite.rgb( max(255-segment.speed*255/(maxspeed-minspeed),0),min(255,segment.speed*255/(maxspeed-minspeed)), 0, '%')))
  dwg.save()

def createlegMap(map, pnts, segments):
  print("creating leg map")
  dwg = svgwrite.Drawing('legs.svg', size=(str(size[0])+"pt",str(size[1])+"pt"), viewBox=('0 0 {y} {x}'.format(x=size[0], y=size[1])))
  dwg.add(map)
  legcount =0
  legcolor = [[0,0,0],[255,0,0],[0,255,0],[0,0,255],[120,120,0],[255,0,255]]
  for segment in segments:
    if (segment.time>600):
      legcount=legcount+1  
    dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="1.5",stroke=svgwrite.rgb(legcolor[legcount%6][0],legcolor[legcount%6][1],legcolor[legcount%6][2] , '%')))
  dwg.save()   
  
def createMaps(gpxData, imageFolder):
  pnts, trps = parsetrkpoints(gpxData)
  url = getMapLink(trps)
  # manual intervention neccessary, OSM doesn't like getting it via code
  print("download file and place the resulting file as map.svg in the working dir:")
  print(url)
  input("press enter once done")

  tree = ET.parse("map.svg")
  root = tree.getroot()
  global size
  size = [int(root.get("height").replace("pt","")), int(root.get("width").replace("pt",""))]
  print ("map size: ", size)
  map = svgwrite.image.Image("map.svg",insert=(0,0), size=(size[1],size[0]))
  # scale all trackpoints to the map
  trps = [trp for trp in trps if trp.scale()]
  
  segments=[]
  for i in range (0, len(trps)-1):
    segments.append(Segment(trps[i],trps[i+1]))
  
  # 255 min -> 0 max
  # 0 -> 255
      # print (segments[i])
 
  #createImageMap(map, pnts, segments, imageFolder)
  #createEleMap(map, pnts, segments)
  #createSpeedMap(map, pnts, segments)
  createlegMap(map, pnts, segments)

# get the timestamp of the filename  
def getTimestamp(name):
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

def main():
  import sys
  if len(sys.argv)!=3:
    print("usage info:")
    # TODO usage info
    print("")
    return
  createMaps(sys.argv[1], sys.argv[2])

if __name__=="__main__":
  main()
