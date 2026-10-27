"""Approximate scan georeferencing, followed by true spherical orthographic projection.
The 1991 boundaries come ONLY from the retained CIA scan trace, not modern borders.
"""
from pathlib import Path
import json, math
import numpy as np
from scipy.optimize import least_squares
from shapely.geometry import shape,Polygon,MultiPolygon
from shapely.ops import transform,unary_union
P=Path(__file__).resolve().parent
CONTROL=[ # scan-crop px, longitude/latitude of printed city symbols
 (221,430,37.617,55.75),(126,440,30.52,50.45),(130,375,27.56,53.9),
 (180,310,24.75,59.44),(172,638,44.8,41.72),(148,669,44.5,40.18),
 (198,700,49.87,40.4),(388,787,69.24,41.3),(288,780,58.38,37.96),
 (408,811,68.78,38.56),(487,784,74.57,42.87),(518,758,76.89,43.24)]
def conic(lon,lat,n,lon0):
    lon,lat=np.radians(lon),np.radians(lat)
    rho=np.tan(np.pi/4-lat/2)**n
    theta=n*(lon-np.radians(lon0))
    return rho*np.sin(theta),-rho*np.cos(theta)
def residual(v):
    n,lon0,scale,rot,tx,ty=v
    c=np.array(CONTROL);x,y=conic(c[:,2],c[:,3],n,lon0)
    return np.column_stack([tx+scale*(x*np.cos(rot)-y*np.sin(rot)),ty-scale*(x*np.sin(rot)+y*np.cos(rot))])-c[:,:2]
fit=least_squares(lambda v:residual(v).ravel(),[.75,100,2200,0,600,-300],
    bounds=([.3,40,500,-.25,-2000,-2000],[.98,160,6000,.25,3000,5000]))
N,LON0,SCALE,ROT,TX,TY=fit.x
def scan_lonlat(x,y,z=None):
    dx=(np.asarray(x)-TX)/SCALE;dy=-(np.asarray(y)-TY)/SCALE
    xx=dx*np.cos(ROT)+dy*np.sin(ROT);yy=-dx*np.sin(ROT)+dy*np.cos(ROT)
    rho=np.sqrt(xx*xx+yy*yy);theta=np.arctan2(xx,-yy)
    return np.degrees(theta/N)+LON0,np.degrees(np.pi/2-2*np.arctan(rho**(1/N)))
def orthographic(lon,lat,z=None):
    dl=np.radians(np.asarray(lon)-85);la=np.radians(lat);la0=np.radians(23)
    xx=np.cos(la)*np.sin(dl)
    yy=np.cos(la0)*np.sin(la)-np.sin(la0)*np.cos(la)*np.cos(dl)
    return 980+700*xx,945-700*yy
RAW=json.loads((P/'assets/ussr-1991-traced.json').read_text())
PIECES=[];used=Polygon()
for item in RAW['pieces']:
    g=transform(orthographic,transform(scan_lonlat,shape(item['geometry']))).buffer(0)
    g=g.difference(used);used=unary_union([used,g])
    PIECES.append((item['name'],g))
UNION=unary_union([g for _,g in PIECES])
def closed_outline():
    g=UNION.buffer(2).buffer(-2)
    return unary_union([Polygon(p.exterior) for p in (list(g.geoms) if hasattr(g,'geoms') else [g]) if p.geom_type=='Polygon'])
OUTLINE=closed_outline()
REPORT={'method':'Spherical Lambert-conic fit to printed city control points; inverse scan projection then orthographic sphere. Approximate illustration, not survey georeferencing.',
 'source':RAW['source'],'controls':CONTROL,'fit_parameters':fit.x.tolist(),
 'control_residual_px':np.linalg.norm(residual(fit.x),axis=1).round(3).tolist(),
 'rms_control_error_px':float(np.sqrt(np.mean(residual(fit.x)**2))),
 'sphere':{'longitude':85,'latitude':23,'radius_px':700,'centre':[980,945]}}
