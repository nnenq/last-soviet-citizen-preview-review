"""Trace flat colour regions from the July 1991 CIA republic map.
The historical raster, vectorization overlays and simplified output are retained
so reviewers can inspect the boundary source. No modern country boundary data.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
from skimage.measure import find_contours
from skimage.morphology import remove_small_holes
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
P=Path(__file__).resolve().parent
im=Image.open(P/"assets/ussr-republics-1991.jpg").resize((1370,1824),Image.Resampling.LANCZOS)
# Work in the main printed map only, excluding heading, legend and library stamp.
a=np.asarray(im.crop((100,140,1340,1010))).astype(float)
# Seed positions measured on the source image resized to 1370 px width.
seeds=[
("Russian SFSR",800,610,0),("Ukrainian SSR",225,610,2),
("Byelorussian SSR",240,525,3),("Moldavian SSR",173,600,3),
("Estonian SSR",293,461,1),("Latvian SSR",269,480,4),
("Lithuanian SSR",241,480,5),("Georgian SSR",241,753,4),
("Armenian SSR",242,802,5),("Azerbaijan SSR",273,821,3),
("Kazakh SSR",570,780,1),("Uzbek SSR",456,881,4),
("Turkmen SSR",389,912,2),("Kirghiz SSR",583,921,5),
("Tajik SSR",531,965,3)]
# Stable interior colour samples, not dark print/line pixels.
samples=[(800,610),(600,790),(228,613),(245,533),(451,865),(580,919)]
palette=[]
for x,y in samples:
    patch=np.asarray(im)[y-4:y+5,x-4:x+5].reshape(-1,3).astype(float)
    good=patch[(patch.max(1)-patch.min(1)>30)&(patch.mean(1)>100)]
    palette.append(np.median(good,axis=0))
palette=np.array(palette)
dist=((a[:,:,None,:]-palette[None,None,:,:])**2).sum(3)
classes=dist.argmin(2)
chroma=a.max(2)-a.min(2)
colored=(chroma>29)&(a.mean(2)>90)&(a.min(2)<220)
L=np.zeros(a.shape[:2],np.uint8)
for cls in range(6):
    mask=ndi.binary_closing((classes==cls)&colored,iterations=2)
    lab,n=ndi.label(mask)
    candidates=[(i+1,x-100,y-140) for i,(name,x,y,c) in enumerate(seeds) if c==cls]
    sizes=np.bincount(lab.ravel())
    if cls==0:
        keep=np.flatnonzero(sizes>12); keep=keep[keep!=0]
        L[np.isin(lab,keep)]=1
    else:
        good=(lab>0)&(sizes[lab]>35)
        _,nearest=ndi.distance_transform_edt(~good,return_indices=True)
        for rid,x,y in candidates:
            yy,xx=nearest[:,int(y),int(x)]
            component=int(lab[yy,xx])
            L[ndi.binary_fill_holes(lab==component)]=rid
land=ndi.binary_closing(L>0,iterations=2)
land=remove_small_holes(land,max_size=1100)
_,inds=ndi.distance_transform_edt(L==0,return_indices=True)
L=np.where(land,L[tuple(inds)],0).astype(np.uint8)
pieces=[]
for i,(name,x,y,c) in enumerate(seeds):
    mask=L==i+1
    contours=find_contours(np.pad(mask,1),.5)
    polys=[]
    for contour in contours:
        coords=[(float(v[1]-1),float(v[0]-1)) for v in contour]
        pol=Polygon(coords).buffer(0)
        if pol.area>8:
            # 0.45 source px is sub-pixel at delivery display size.
            pol=pol.simplify(.45,preserve_topology=True)
            polys.append(pol)
    geom=unary_union(polys)
    if geom.is_empty: raise RuntimeError("Missing republic "+name)
    pieces.append({"name":name,"geometry":mapping(geom),"area_source_px":geom.area})
    print(name,round(geom.area,1))
data={"source":"CIA 801727 (B01272) 7-91, LOC 2005626536",
"source_url":"https://www.loc.gov/item/2005626536/",
"method":"Colour-region vectorization of the actual July 1991 map. Simplified at 0.45 source pixel; tiny print, border strokes and enclaves below scan resolution cannot support survey-level precision.",
"source_work_size":[1240,870],"pieces":pieces}
(P/"assets/ussr-1991-traced.json").write_text(json.dumps(data),encoding="utf-8")
# Diagnostic overlay: coloured region IDs plus silhouettes against the source.
overlay=Image.fromarray(a.astype("uint8")).convert("RGBA")
color=np.random.default_rng(15).integers(70,255,(16,3),dtype=np.uint8)
out=np.zeros((*L.shape,4),np.uint8);out[:,:,:3]=color[L];out[:,:,3]=(L>0)*140
overlay=Image.alpha_composite(overlay,Image.fromarray(out))
dr=ImageDraw.Draw(overlay)
for i,(name,x,y,c) in enumerate(seeds):dr.text((x-100,y-140),str(i+1),fill="black",stroke_width=1,stroke_fill="white")
overlay.convert("RGB").save(P/"assets/1991-trace-overlay.jpg",quality=95)
np.save(P/"assets/1991-region-labels.npy",L)

