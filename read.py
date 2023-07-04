#import numpy as np
#import matplotlib.pyplot as plt

#from svgutils.transform import from_mpl
#from svgutils.templates import VerticalLayout

#layout = VerticalLayout()
#
#fig1 = plt.figure()
#plt.plot([1, 2])
#fig2 = plt.figure()
#plt.plot([2, 1])
#
#layout.add_figure(from_mpl(fig1))
#layout.add_figure(from_mpl(fig2))

#layout.save("stack_plots.svg")

#from svglib.svglib import svg2rlg
#from reportlab.graphics import renderPDF, renderPM

# 11.1515, 47.3565

# 12.1265 47.0626

#drawing = svg2rlg("map.svg")
#renderPM.drawToFile(drawing, "file.png", fmt="PNG")

import math
topleft=[47.3616,11.3420]
botright=[47.1141,11.7904]
scaling = 1/80500
cmperdegree = 11113900
size=[625 , 534]
#625 x 534
# ----

dist = math.sqrt((topleft[0]-botright[0])**2+(topleft[1]-botright[1])**2)

#print (dist*cmperdegree*scaling)
#     x
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import svgwrite
import os
  
class trkpnt:
  def __init__(self, lat, lon, ele, time):
    self.lat = float(lat)
    self.lon = float(lon)
    self.ele = float(ele)
    self.time = time
    self.timestamp = datetime.strptime(self.time,'%Y-%m-%dT%H:%M:%SZ')+timedelta(hours=2, minutes=0)
    self.scale()
    
  def scale(self):
    self.scaledlon = (self.lon-topleft[1])*(size[1]/(-topleft[1]+botright[1]))
    self.scaledlat = (topleft[0]-self.lat)*size[0]/(topleft[0]-botright[0])    
  
  def __repr__(self):
    return "[{lat}, {lon}, {ele}: {time}]".format(lat=self.scaledlat, lon=self.scaledlon, ele =self.ele, time = self.timestamp)
  
  
class wypnt(trkpnt):
  def __init__(self, lat, lon, ele, time, desc):
    super().__init__(lat, lon, ele, time)
    self.desc =desc
    
  def __repr__(self):
    return self.desc + "-" + super().__repr__()
    
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
  


def parsetrkpoints():
  waypoints=[]
  trackpoints=[]
  ns = {"":"http://www.topografix.com/GPX/1/1"}
  tree = ET.parse("Inntaler Höhenweg 2022.gpx")
  root = tree.getroot()
  for wpt in root.findall('wpt',namespaces=ns):
    
    #waypoints.append(wypnt(wpt.get("lat"),wpt.get("lon"), wpt.find("ele", namespaces=ns).text,wpt.find("time", namespaces=ns).text,wpt.find("desc", namespaces=ns).text))
    print(wypnt(wpt.get("lat"),wpt.get("lon"), wpt.find("ele", namespaces=ns).text,wpt.find("time", namespaces=ns).text,wpt.find("desc", namespaces=ns).text))
  
  for tpt in root.find("trk", namespaces=ns).find("trkseg", namespaces=ns).findall('trkpt', namespaces=ns):
    trackpoints.append(trkpnt(tpt.get("lat"),tpt.get("lon"), tpt.find("ele", namespaces=ns).text,tpt.find("time", namespaces=ns).text))
  
  return waypoints, trackpoints
  
def getSegment(segments, timestamp):
  if (timestamp==None):
    return None
  for segment in segments:
    if (segment.orig.timestamp<timestamp and segment.target.timestamp> timestamp):
      return segment
  return None
  
def createMaps():
  tree = ET.parse("map.svg")
  root = tree.getroot()
  global size
  size = [int(root.get("height").replace("pt","")), int(root.get("width").replace("pt",""))]
  print (size)
  image = svgwrite.image.Image("map.svg",insert=(0,0), size=(size[1],size[0]))
  #size = [image.height,image.width] 
  dwg = svgwrite.Drawing('test.svg', size=(str(size[0])+"pt",str(size[1])+"pt"), viewBox=('0 0 {y} {x}'.format(x=size[0], y=size[1])))
  dwg.add(image)
  pnts, trps = parsetrkpoints()
  segments=[]
  for pnt  in pnts:
    dwg.add(dwg.line((pnt.scaledlon+5,pnt.scaledlat+5),(pnt.scaledlon-5,pnt.scaledlat-5),stroke=svgwrite.rgb(10, 10, 16, '%')))
    dwg.add(dwg.line((pnt.scaledlon+5,pnt.scaledlat-5),(pnt.scaledlon-5,pnt.scaledlat+5),stroke=svgwrite.rgb(10, 10, 16, '%')))
  minspeed, minele = 10000 , 10000
  maxspeed, maxele = 0,0
  for i in range (0, len(trps)-1):
    segments.append(Segment(trps[i],trps[i+1]))
    # print (segments[i])
    if (segments[i].speed<0.15):
      minspeed = min(minspeed,segments[i].speed)
      maxspeed = max(maxspeed,segments[i].speed)
    if (segments[i].avele>00):
      minele = min(minele,segments[i].avele)
      maxele = max(maxele,segments[i].avele)
  print (minele, maxele)
  
  # 255 min -> 0 max
  # 0 -> 255
  
  etappencount = 0
  etappencolor = [[10,10,10],[255,0,0],[0,255,0],[0,0,255],[120,120,0],[255,0,255]]
    
  for segment in segments: 
    if (segment.time>600):
      etappencount=etappencount+1  
    dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="0.5",stroke=svgwrite.rgb(10, 10, 10, '%')))
    #dwg = svgwrite.Drawing('test.svg')
    # color over etappe
    # dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="1",stroke=svgwrite.rgb(etappencolor[etappencount][0],etappencolor[etappencount][1],etappencolor[etappencount][2] , '%')))
    # ele over distance
    # dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="0.4",stroke=svgwrite.rgb( min(255,segment.avele*255/(maxele-minele)),max(255-segment.avele*255/(maxele-minele),0), 0, '%')))
    # speed over distance
    # dwg.add(dwg.line((segment.orig.scaledlon,segment.orig.scaledlat),(segment.target.scaledlon,segment.target.scaledlat),stroke_width="0.4",stroke=svgwrite.rgb( max(255-segment.speed*255/(maxspeed-minspeed),0),min(255,segment.speed*255/(maxspeed-minspeed)), 0, '%')))
    
  dwg.add(svgwrite.container.Script(content='function show_image(src, width, height, alt, x, y) {var svg = document.getElementsByTagName("svg")[0];  var svgimg = document.createElementNS("http://www.w3.org/2000/svg","image"); svgimg.setAttributeNS(null,"height",height); svgimg.onclick=function(){svg.getElementById(src).remove(svgimg)}; svgimg.setAttributeNS(null,"id",src), svgimg.setAttributeNS(null,"width",width);svgimg.setAttributeNS("http://www.w3.org/1999/xlink","href", src);svgimg.setAttributeNS(null,"x",x);svgimg.setAttributeNS(null,"y",y);svgimg.setAttributeNS(null, "visibility", "visible");svg.append(svgimg);}'))
    
  try:
    for root, dirs, files in os.walk("D:/Bilder/2022/Inntaler Höhenweg"):
      for f in files:
        if "jpg" in f:
          segment = getSegment(segments, getTimestamp(f))
          if (segment != None):
            dwg.add(svgwrite.shapes.Circle(center=(segment.orig.scaledlon,segment.orig.scaledlat),r=5,stroke=svgwrite.rgb(10,10,10,"%"), onclick="show_image(\""+f+"\", 400, 300, 'test image',"+ str(segment.orig.scaledlon)+","+ str(segment.orig.scaledlat)+")"))
  except Exception as ex:
    print(ex)
  #dwg.save()
  
  dwg.save()
  
  print (minspeed, maxspeed)
  
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
  except Exception as ex:
    print (ex)

def main():
  createMaps()
  

  
  


if __name__=="__main__":
  main()
