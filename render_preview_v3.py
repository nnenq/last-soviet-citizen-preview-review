"""Preview revision 3. Clean, separate render; previous artifacts remain intact."""
from pathlib import Path
import argparse,copy,hashlib,json,math,os,subprocess,wave,colorsys,inspect
import cairo,numpy as np
from PIL import Image
from scipy import signal
from shapely import affinity
from shapely.ops import unary_union
from shapely.geometry import Polygon
import pyloudnorm as pyln
import render_preview as B
import render_preview_v2 as V
import projection_v3 as G
# Reuse the established canonical face/rig, applying pose-only repairs locally.
# The v2 source on disk is preserved as review evidence.
_rig_source=inspect.getsource(V.rig)
_start=_rig_source.index('    aa=math.radians(')
_end=_rig_source.index('    if FLAGS.get("gravity_pose"):',_start)
_rig_source=_rig_source[:_start]+'''    elbow_far=(-52,-205+1.2*math.sin(t*.6))
    hand_far=(-59,-245+1.2*math.sin(t*.6))
'''+_rig_source[_end:]
_rig_source=_rig_source.replace('C.translate(2,-301);C.scale(.95,.98)','C.translate(2,-301);C.rotate(-.10);C.scale(.95,.98)')
_rig_source=_rig_source.replace('ellipse(-15,-1,4.3,bl,B.INK);ellipse(12,-2,4.3,bl,B.INK)','ellipse(-25,-1,4.3,bl,B.INK);ellipse(-2,-2,4.3,bl,B.INK)')
_rig_source=_rig_source.replace('M-23 -17 Q-15 -20 -7 -18 M9 -19 Q18 -20 26 -16','M-33 -17 Q-25 -20 -17 -18 M-1 -19 Q8 -20 16 -16')
exec(compile(_rig_source,'<v3-local-canonical-rig>','exec'),V.__dict__)
P=Path(__file__).resolve().parent;O=P/'preview-v3';Q=O/'qa'
for d in [O,Q,Q/'source',Q/'frames',Q/'mutations']:d.mkdir(parents=True,exist_ok=True)
W,H,FPS,N=1920,1080,30,690
SAMPLES=[0,75,78,150,270,345,414,495,600,660]
C=None;FLAGS={};META={};TEXT_BOXES=[]
METER=pyln.Meter(48000)
PALETTE=[]
# Adjacent regions get different lightness bands, spaced by 9 percentage points.
LEVELS=[.41,.68,.50,.77,.86,.59,.77,.68,.86,.50,.59,.77,.41,.68,.86]
for i,l in enumerate(LEVELS):
    rgb=colorsys.hls_to_rgb((.96+.003*i)%1,l,.63)
    PALETTE.append('#'+''.join(f'{round(c*255):02x}' for c in rgb))
CENT=np.array([G.UNION.centroid.x,G.UNION.centroid.y])
# The small 1991 republics need negative space. Keep every traced island,
# shrink their picture footprints equally and open a radial exploded view.
BASE=[]
for name,g in G.PIECES:
    BASE.append((name,affinity.scale(g,.78,.78,origin='centroid')))
OFFSETS=[]
for name,g in BASE:
    d=np.array([g.centroid.x,g.centroid.y])-CENT
    OFFSETS.append(d/(np.linalg.norm(d)+1e-12)*34)

def setup(sf):
    global C
    C=cairo.Context(sf);B.C=C;V.C=C
    C.set_line_cap(cairo.LINE_CAP_ROUND);C.set_line_join(cairo.LINE_JOIN_ROUND)
def path(g):V.geopath(g)
def rect(*a,**k):B.rect(*a,**k)
def line(*a,**k):B.line(*a,**k)
def ellipse(*a,**k):B.ellipse(*a,**k)
def svg(*a,**k):B.svg(*a,**k)
def rgb(sf):
    sf.flush();return np.asarray(Image.frombuffer('RGB',(W,H),bytes(sf.get_data()),'raw','BGRX',0,1)).copy()
def camera(t):
    # A restrained but visible orbiting-camera drift, not temporal grain.
    s=1+.026*t
    return (s,-21*t,7*t)
def world_transform(t):
    s,dx,dy=camera(t);C.translate(980+dx,660+dy);C.scale(s,s);C.translate(-980,-660)
def globe_base():
    sf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H);setup(sf)
    B.src(B.BG);C.paint()
    ellipse(980,945,705,705,None,'#466b88',3,alpha=.65)
    C.save();C.arc(980,945,700,0,math.tau);C.clip()
    grad=cairo.RadialGradient(710,580,40,980,945,850)
    for pos,col in [(0,'#1d4163'),(.55,'#142c46'),(1,'#070d18')]:grad.add_color_stop_rgb(pos,*B.rgba(col)[:3])
    C.set_source(grad);C.paint()
    # Modern polygons provide only dim geographic land silhouettes. Their
    # borders are dissolved, and NEVER substitute the 1991 republic map.
    continents=[]
    for feat in B.GEO:
        geom=feat['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            ring=np.array(poly[0]);dl=np.radians(ring[:,0]-85);la=np.radians(ring[:,1]);la0=np.radians(23)
            vis=np.sin(la0)*np.sin(la)+np.cos(la0)*np.cos(la)*np.cos(dl)
            if (vis>0).mean()<.98:continue
            x,y=G.orthographic(ring[:,0],ring[:,1]);p=Polygon(np.column_stack([x,y])).buffer(0)
            if not p.is_empty:continents.append(p)
    path(unary_union(continents));B.fillstroke('#213544',None)
    shade=cairo.LinearGradient(470,530,1630,1100)
    shade.add_color_stop_rgba(0,0,0,0,0);shade.add_color_stop_rgba(.65,0,0,0,.2);shade.add_color_stop_rgba(1,0,0,0,.84)
    C.set_source(shade);C.paint()
    # Schematic night settlements, not a claimed satellite lights dataset.
    rng=np.random.default_rng(1991)
    for lon,lat in [(2.35,48.86),(13.4,52.5),(28.98,41),(31.2,30),(77.2,28.6),(121.5,31.2),(139.7,35.7),(37.6,55.75),(30.5,50.5)]:
        for j in range(16):
            x,y=G.orthographic(lon+rng.normal(0,1),lat+rng.normal(0,.6))
            ellipse(float(x),float(y),.8+(j%3)*.2,.8+(j%3)*.2,'#c0a675',alpha=.25+.1*(j%3))
    C.restore();return sf
EARTH=globe_base()

def pieces_at(t,flags=None):
    flags=flags or {};phase=B.ease((t-2.5)/.42)
    pieces=[]
    for i,(name,g) in enumerate(G.PIECES):
        shrink=1-.22*phase
        g=affinity.scale(g,shrink,shrink,origin='centroid')
        off=OFFSETS[i]*phase
        g=affinity.translate(g,*off)
        # Resolve nonconvex overlap in screen-space by a common thin cut.
        # The retained shapes are inspected in the pixel diagnostic, not just
        # accepted because this operation claims to have separated them.
        pieces.append([name,g,off])
    # Radial motion can cross non-convex coastline indentations. Open a 3 px
    # cut on BOTH touching regions, never leave a hidden overpainted overlap.
    for i in range(len(pieces)):
        for j in range(i):
            overlap=pieces[i][1].intersection(pieces[j][1])
            if overlap.area>.001:
                cut=overlap.buffer(1.6)
                pieces[i][1]=pieces[i][1].difference(cut)
                pieces[j][1]=pieces[j][1].difference(cut)
    if phase>.001:
        # Reserve a real antialiasing gap as well as mathematical non-overlap.
        # This prevents painter-order colour mixing on sub-pixel boundaries.
        for item in pieces:item[1]=item[1].buffer(-.85*phase)
    if flags.get('map_overlap'):
        a=pieces[5][1];b=pieces[6][1]
        pieces[5][1]=affinity.translate(a,b.centroid.x-a.centroid.x,b.centroid.y-a.centroid.y)
    if flags.get('map_count'):pieces=pieces[:-1]
    return pieces

def map_picture(t):
    C.save();world_transform(t)
    C.set_source_surface(EARTH,0,0);C.paint()
    revealed=t>=2.5 or FLAGS.get('map_reveal')
    if not revealed:
        path(G.OUTLINE);B.fillstroke('#38232b',B.RED,3)
    else:
        pieces=pieces_at(t if t>=2.5 else 3.2,FLAGS)
        if FLAGS.get('map_displacement'):
            pieces=[[name,affinity.translate(g,*(-off*.95)),off*.05] for name,g,off in pieces]
        indexed=list(enumerate(pieces))
        if FLAGS.get('reverse_map'):indexed=indexed[::-1]
        for i,(name,g,off) in indexed:
            path(g)
            B.fillstroke(PALETTE[i] if not FLAGS.get('map_tints') else '#ad4149',None)
        # The WHITE border flash is a brief graphic accent on the cracks.
        if 75<=round(t*30)<=77 and not FLAGS.get('no_flash'):
            for _,g,_ in pieces:path(g);B.fillstroke(None,'#fff7e8',2)
        META['map_offsets']=[o.tolist() for _,_,o in pieces]
    C.restore()
    # Close Mir pass is above the sphere, independent of map camera drift.
    x=1125+82*t;y=295+17*math.sin(t*.6)
    C.save();C.translate(x,y);C.rotate(-.08+.012*t);C.scale(1.3 if not FLAGS.get('small_mir') else .3,1.3 if not FLAGS.get('small_mir') else .3)
    draw_mir();C.restore()

def draw_mir():
    rect(-17,-8,35,16,'#8d9698','#d2d1c7',1.3)
    rect(-6,-24,12,48,'#637581','#a9bbc2',1.1)
    ellipse(-22,0,6,9,'#aeb6b4','#d4d6cb',1)
    for side in [-1,1]:
        line([(side*17,0),(side*24,0)],'#c2c8bd',2)
        rect(side*37-13,-21,26,42,'#274663','#7fabbc',1.2)
        for j in range(1,6):line([(side*37-13,-21+7*j),(side*37+13,-21+7*j)],'#5d849a',.9)
        line([(side*37,-21),(side*37,21)],'#7399ac',.8)
    ellipse(17,-5,3,3,'#fff3c4')

def cabin(t,home=False):
    # Kept clear above y=215 even at the end of the move.
    zoom=1.19+.025*t
    C.save();C.translate(960-5*t,710);C.scale(zoom,zoom);C.translate(-960,-570)
    rect(517,212,886,886,'#11151b',B.LINE,3,r=156)
    rect(544,240,832,832,None,'#303943',2,r=139)
    for x in [590,742,1135,1286]:line([(x,264),(x,990)],'#2e3740',1.5)
    for y in [365,730,950]:line([(546,y),(1374,y)],'#29353f',1.5)
    for x,y in [(575,340),(1165,390),(1165,760)]:
        rect(x,y,140,105,'#171d25','#46535b',2,r=9)
        for j in range(4):line([(x+15,y+25+j*17),(x+105,y+25+j*17)],'#3c4953',2)
        ellipse(x+118,y+24,2.5,2.5,'#88b3be',alpha=.75)
    wx,wy,wr=700,493,42
    if FLAGS.get('scale'):wr=15
    ellipse(wx,wy,wr+10,wr+10,'#181f27','#606d76',3)
    C.save();C.arc(wx,wy,wr,0,math.tau);C.clip()
    rect(wx-wr,wy-wr,2*wr,2*wr,'#080e19')
    ellipse(wx-9+t*2,wy+34,61,61,'#244966')
    ellipse(wx-9+t*2,wy+34,62,62,None,'#b6d2d7',2)
    line([(wx-60,wy+13),(wx-25,wy-5),(wx+7,wy+8),(wx+35,wy-1)],'#487681',6)
    C.restore();ellipse(wx,wy,wr,wr,None,'#a2afb4',2)
    # Same canonical rig, with a compact free arm and a face turned LEFT to
    # the window. It is not a redesigned face: the contour/hair are reused.
    V.FLAGS={'gravity_pose':bool(FLAGS.get('gravity_pose')),'rail_brackets':bool(FLAGS.get('rail_brackets')),'detached_hand':bool(FLAGS.get('detached_hand'))}
    V.EXTRA={}
    C.save()
    if FLAGS.get('hero_scale'):
        C.translate(930,500);C.scale(.60,.60);C.translate(-930,-500)
    V.rig(t);C.restore()
    META['body']=copy.deepcopy(V.EXTRA.get('body',{}))
    C.restore()

def vehicle():
    # Four boosters with conical shoulders, slim central upper stages.
    for x,far in [(934,True),(986,True),(909,False),(1011,False)]:
        svg(f'M{x} 591 L{x+14} 660 L{x+20} 862 L{x+24} 900 L{x-22} 900 L{x-16} 858 L{x-13} 661 Z','#798085' if far else '#b6bbb9','#535c63',2)
    svg('M960 367 L966 400 L979 441 L979 482 L973 497 L973 791 L986 900 L934 900 L947 791 L947 497 L941 482 L941 441 L954 400 Z','#dbd8c9','#626c70',2)
    for y in [481,507,604,786]:line([(948,y),(972,y)],'#7a8689',2)
    for x in [909,960,1011]:ellipse(x,905,13,5,'#222831','#777d80',1)

def support(t):
    opening=B.ease((t-5.5)/.60)
    # Four arms shown as two rear and two front perspective members.
    for side,depth in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        base=np.array([960+side*(185 if depth==1 else 147),925+(13 if depth==1 else -18)])
        closed=np.array([960+side*(64 if depth==1 else 46),609+(14 if depth==1 else -5)])
        vec=closed-base;angle=side*math.radians(67)*opening
        rot=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
        tip=base+rot@vec
        width=16 if depth==1 else 11;col='#747f82' if depth==1 else '#414d54'
        line([tuple(base),tuple(tip)],'#222a30',width+4);line([tuple(base),tuple(tip)],col,width)
        mid=(base+tip)/2
        line([tuple(base+[-side*24,0]),tuple(mid),tuple(tip)],'#4d5960',3)
        ellipse(*base,15,11,'#2a333a','#9aa2a1',2)
        rect(base[0]-side*33-18,base[1]-3,36,23,'#515c61','#85918e',1)

def masts(t):
    retract=B.ease(t/1.8)
    for side,top in [(-1,491),(1,690)]:
        x=960+side*140;y=923
        C.save();C.translate(x,y);C.rotate(side*math.radians(71)*retract)
        line([(0,0),(0,top-y)],'#4c5860',13)
        line([(0,top-y),(-side*124,top-y)],'#a1aaa7',6)
        for yy in range(round(top-y)+12,-10,55):line([(-7,yy),(7,yy+40)],'#79868b',2)
        C.restore()

def pad():
    # Trench and table are visible in ALL launch compositions.
    svg('M0 925 L1920 925 L1920 1080 L0 1080 Z','#1b2228')
    line([(0,925),(1920,925)],'#647176',3)
    svg('M765 925 L833 986 L1090 986 L1155 925 Z','#070b11','#566169',3)
    svg('M804 925 L852 963 L1070 963 L1116 925 Z','#38424b')
    # Split table rims leave the engine/exhaust opening physically open.
    rect(754,917,74,12,'#647076','#9caaa8',1)
    rect(1092,917,74,12,'#647076','#9caaa8',1)
    for x in [780,1114]:rect(x,929,24,67,'#434c52','#6a777c',1)
    # Converging ground rays reinforce the low-view perspective.
    for x in [40,300,570,1340,1610,1870]:line([(960+(x-960)*.35,927),(x,1080)],'#2c373f',2)

def smoke(age):
    if age<0:return
    # Successive puffs originate at the two trench exits at ground level.
    # Hard-edged low-alpha lobes with highlights replace blurry floating ovals.
    for layer in range(3):
        for side in [-1,1]:
            for k in range(65):
                a=age-k*.095-layer*.04
                if a<=0:continue
                dist=60+180*a
                r=21+30*a+layer*3
                x=960+side*dist;y=956-r*.12-7*layer-7*math.sin(a*1.7+k*.8)
                opacity=min(.60,.22+.1*layer)*min(1,a/.12)
                col=['#8a8a90','#a7a8ad','#d0d0d4'][layer]
                ellipse(x,y-r*.34,r*1.22,r*.61,col,alpha=opacity)
                ellipse(x-side*r*.38,y-r*.71,r*.66,r*.47,col,alpha=opacity*.85)
    # Bright continuous stream connects the trench to the first billows.
    for side in [-1,1]:
        svg(f'M{960+side*22} 947 Q{960+side*95} 936 {960+side*169} 950 L{960+side*169} 969 L{960+side*25} 969 Z','#aaacb0',alpha=min(.6,age*2))

def exhaust(t,length):V.FLAGS={'red_flame':FLAGS.get('red_flame',False)};V.EXTRA={};V.exhaust(t,length)
def launch(local,phase):
    # All three cameras are continuous in the same launch-table coordinates.
    C.save();C.rectangle(0,215,W,H-215);C.clip()
    if phase=='wide':
        s=1.1+.030*local;C.translate(960-8*local,670);C.scale(s,s);C.translate(-960,-670)
        pad();masts(local);vehicle();support(local)
    elif phase=='engine':
        # Ground is at 830 screen px, not outside the close-up.
        s=2.15+.06*local;C.translate(960,830);C.scale(s,s);C.translate(-960,-925)
        pad();masts(local+3);vehicle();support(local+3)
        exhaust(local,65+20*local);smoke(local+.04)
    else:
        t=local;rise=37+145*t+28*t*t
        # Ground/horizon sit in bottom quarter. Vertical perspective narrows
        # the rocket upwards and moves the viewpoint below the table.
        C.translate(960+3*math.sin(t*57),880+.90*rise+2*math.sin(t*48))
        C.translate(-960,-925)
        pad();masts(t+5.5);support(t+5.5);smoke(t+2.5)
        C.save();C.translate(0,-rise)
        # Projective taper is approximated piecewise by a Cairo group warp
        # in the separate perspective vehicle surface below.
        draw_perspective_vehicle(t);C.restore()
    C.restore()

_rocket_source=None
def draw_perspective_vehicle(t):
    global _rocket_source,C
    # Non-affine, upward perspective: top width 62% of the base width.
    # Thin horizontal strips implement the projective illustration transform.
    if _rocket_source is None:
        old=C;sf=cairo.ImageSurface(cairo.FORMAT_ARGB32,W,H);setup(sf);vehicle();_rocket_source=sf
        sf.flush()
        from scipy.ndimage import map_coordinates
        import io
        a=np.asarray(Image.frombuffer('RGBA',(W,H),bytes(sf.get_data()),'raw','BGRA',0,1)).copy()
        yy,xx=np.mgrid[360:915,850:1070];f=.62+.38*(yy-364)/(913-364)
        srcx=960+(xx-960)/f
        warped=np.stack([map_coordinates(a[:,:,ch],[yy,srcx],order=1,mode='constant') for ch in range(4)],axis=2).astype('uint8')
        stream=io.BytesIO();Image.fromarray(warped).save(stream,format='PNG');stream.seek(0)
        _rocket_source=cairo.ImageSurface.create_from_png(stream)
        C=old;B.C=C;V.C=C
    C.set_source_surface(_rocket_source,850,360);C.paint()
    exhaust(t,240)

def docking(t):
    # The hook's USSR map is absent: a different scale and narrative action.
    B.stars(t)
    C.save();C.rectangle(0,220,W,H-220);C.clip()
    # Earth is background context only, much lower than the docking silhouettes.
    C.save();C.translate(-50-8*t,450-5*t);C.scale(1.12+.008*t,1.12+.008*t);C.set_source_surface(EARTH,0,0);C.paint();C.restore()
    # Camera eases in throughout the actual approach.
    C.translate(1070-5*t,540+3*t);C.scale(3.4+.080*t,3.4+.080*t)
    rect(-35,-14,70,28,'#8d999a','#d1d7cb',1.2,r=4)
    ellipse(-35,0,7,14,'#9faeac','#d4d8cb',1)
    line([(-48,0),(-40,0)],'#d3d0bd',3)
    rect(13,-39,17,78,'#6b8089','#bccac9',1)
    for side in [-1,1]:
        line([(21,side*39),(21,side*48)],'#c4d1ce',2)
        rect(-11,side*66-17,64,34,'#274663','#7fabbc',1.2)
        for j in range(1,7):line([(-11+j*9,side*66-17),(-11+j*9,side*66+17)],'#6c90a3',.7)
        line([(-11,side*66),(53,side*66)],'#7ba1b2',.8)
    ellipse(33,-9,2,2,'#fff3c4')
    # Approach from left, nose facing the fore docking port of Mir.
    distance=127-58*B.ease(t/6.5)
    C.save();C.translate(-distance,0)
    # Service module, descent capsule and spherical orbital module.
    rect(-50,-12,22,24,'#647e88','#b7c4c4',1,r=3)
    svg('M-28 -12 L-10 -10 L-6 10 L-28 12 Z','#b6beb4','#d5d8ca',1)
    ellipse(2,0,11,12,'#bac7be','#e0dfd2',1)
    line([(13,0),(21,0)],'#d3d0bd',2)
    for side in [-1,1]:
        rect(-48,side*28-10,27,20,'#243e59','#648ba5',.9)
        line([(-35,side*10),(-35,side*19)],'#a3b5ba',1)
        for j in range(3):line([(-48+j*9,side*28-10),(-48+j*9,side*28+10)],'#5c8298',.6)
    if t>5.65:
        # Docking light pulses before the physical contact, no magical snap.
        ellipse(19,0,1.1,1.1,'#f3e0a4',alpha=.5+.4*math.sin(t*9))
    C.restore();C.restore()

def day(n,shot):
    # Editorial prologue is not assigned a false mission date. At the first
    # launch shot chronology starts and remains visible through docking.
    if shot<3:return
    d=1 if n<480 else 3
    date='18 MAY 1991' if d==1 else '20 MAY 1991'
    if FLAGS.get('missing_day') and n>=480:return
    if FLAGS.get('date'):d=0
    B.text('DAY',64,104,40,'#878991',font='mono',center=False,role='counter')
    B.text(str(d),153,104,60,B.RED,font='mono',center=False,role='counter')
    B.text(date,64,164,32,'#9b9da4',font='mono',center=False,role='date')

def draw(n,flags=None,picture_only=False):
    global FLAGS,META,C
    FLAGS=flags or {};META={};t=n/30
    sf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H);setup(sf);B.BOUNDS=[];B.SCALES=[]
    B.src(B.BG);C.paint()
    shot=1 if n<120 else 2 if n<240 else 3 if n<330 else 4 if n<405 else 5 if n<480 else 6
    if shot==1:
        B.stars(t);C.save()
        if 75<=n<80:C.translate(3*math.sin((n-75)*2.3),2*math.sin((n-75)*2.9))
        map_picture(t);C.restore()
    elif shot==2:cabin(t-4)
    elif shot==3:launch(t-8,'wide')
    elif shot==4:launch(t-11,'engine')
    elif shot==5:launch(t-13.5,'low')
    else:docking(t-16)
    if FLAGS.get('stroke'):line([(600,128),(1320,128)],'#727d84',3)
    picture=rgb(sf)
    if not picture_only:
        day(n,shot)
        if shot==1:B.caption('He left Earth from one country.',t,0,4)
        elif shot==2:B.caption('He came back to another.',t,4,8)
        elif shot in [3,4,5]:
            B.caption(['May 1991. Sergei Krikalev flies','to the space station Mir.'],t,8.05,15.9)
            if shot==3:B.text(str(3-int(t-8)),1260,594,96,B.RED,font='mono',role='countdown')
        else:B.caption('The plan: five months in orbit.',t,16.1,23)
        if FLAGS.get('text_head'):B.text('OVERLAP',930,450,56,role='caption')
        if FLAGS.get('head_crop'):ellipse(1908,430,47,50,B.SKIN,B.INK,3)
    META.update(frame=n,time=t,shot=shot,bounds=copy.deepcopy(B.BOUNDS))
    if n in SAMPLES and not FLAGS and not picture_only:
        # Exact lossless pixels entering the H.264 encoder.
        sf.write_to_png(str(Q/'source'/f'frame-{n:04d}.png'))
    return sf,META,picture

def audio():
    sr=48000;T=np.arange(sr*23)/sr;rng=np.random.default_rng(19910518)
    def band(lo,hi):
        x=rng.normal(size=len(T));sos=signal.butter(3,[lo,hi],fs=sr,btype='bandpass',output='sos')
        y=signal.sosfilt(sos,x);return y/(y.std()+1e-9)
    # Sparse tonal atmosphere; its noise component is low-passed at 420 Hz.
    hum=.07*band(80,420)
    score=np.zeros(len(T))
    for tm,hz in [(0,130.81),(3.4,164.81),(7.3,196),(10.8,146.83),(16,164.81),(19.5,196)]:
        age=T-tm;env=np.maximum(0,1-np.exp(-np.maximum(age,0)*9))*np.exp(-np.maximum(age,0)*.42)*(age>=0)
        score+=env*(.11*np.sin(math.tau*hz*T)+.035*np.sin(math.tau*hz*2.003*T)+.015*np.sin(math.tau*hz*3.01*T))
    base=hum+score+.028*np.sin(math.tau*98*T)
    bed=np.column_stack([base,hum*.96+score*.98+.028*np.sin(math.tau*98*T+.03)])
    # Quiet bed is normalized as ONE stem, never one constant-volume movie.
    bed*=10**((-19.5-METER.integrated_loudness(bed))/20)
    # Slow musical level variation remains audible from the first frame.
    bed*=np.interp(T,[0,4,8,11,13.5,16,19,23],[1.03,.90,.98,.9,.9,.98,1.06,.96])[:,None]
    cues=[];stemdir=O/'event-templates';stemdir.mkdir(exist_ok=True)
    def event(tm,dur,name,kind,amp):
        l=round(sr*dur);tt=np.arange(l)/sr
        if kind=='beep':s=np.sin(math.tau*740*tt)*np.minimum(1,tt/.003)*np.exp(-tt*14)
        elif kind=='crack':
            raw=rng.normal(size=l);s=signal.sosfilt(signal.butter(2,3200,fs=sr,output='sos'),raw)*np.exp(-tt*17)+.45*np.sin(math.tau*95*tt)*np.exp(-tt*23)
        else:s=np.sin(math.tau*120*tt)*np.exp(-tt*28)+.3*rng.normal(size=l)*np.exp(-tt*40)
        s*=amp;template=stemdir/(name.replace(' ','-')+'.wav')
        writewav(template,s)
        k=round(tm*sr);bed[k:k+l]+=s[:,None]
        cues.append({'name':name,'time':tm,'visual_frame':round(tm*30),'template':template.relative_to(P).as_posix()})
    event(2.5,.45,'map fracture','crack',.13)
    for tm,i in [(8,3),(9,2),(10,1)]:event(tm,.15,f'countdown {i}','beep',.09)
    event(13.5,.25,'support release','clunk',.13)
    # Saturated, low-mid-dominant engine body has a controlled crest factor.
    roar=.8*band(35,520)+.20*band(600,1800)
    roar=np.tanh(roar*1.6)
    stereo=np.column_stack([roar,np.roll(roar,47)*.98])
    stereo*=10**((-10.0-METER.integrated_loudness(stereo))/20)
    env=np.interp(T,[0,10.999,11.08,12.5,13.5,14.7,15.95,16.07,23],[0,0,.68,.81,.96,1.13,1.03,0,0])
    bed+=stereo*env[:,None]
    bed[-240:]*=np.linspace(1,.8,240)[:,None]
    # Initial master gain, followed by measured scene automation. Quiet
    # atmosphere and the launch have separate targets, approximately 9 LU
    # apart. This is not the old constant -14 LUFS wall across the whole film.
    gain=10**((-14-METER.integrated_loudness(bed))/20);bed*=gain
    levels=np.array([METER.integrated_loudness(bed[i*sr:(i+1)*sr]) for i in range(23)])
    targets=np.array([-18.15]*11+[-9.75,-9.25,-9.3,-9.1,-9.2]+[-18.15]*7)
    automation=np.interp(T,np.arange(23)+.5,10**((targets-levels)/20))
    bed*=automation[:,None]
    # Small final scene trims, retaining roughly 9 LU cabin/launch contrast.
    trim_db=np.interp(T,[0,10.98,11.08,15.98,16.08,23],[.22,.22,.04,.04,.22,.22])
    bed*=10**(trim_db[:,None]/20)
    # Keep ALL pure atmosphere/score passages at or below -18 LUFS short-term,
    # and put the extra energy into a deliberate countdown music crescendo.
    # This supplies integrated loudness without making the cabin loud.
    scene_db=np.interp(T,[0,10.98,11.08,15.98,16.08,23],[-.35,-.35,-.32,-.32,-.35,-.35])
    bed*=10**(scene_db[:,None]/20)
    swell_env=np.interp(T,[0,7.999,8.04,10.95,11,23],[0,0,.4,1.1,0,0])
    swell=(np.sin(math.tau*196*T)+.5*np.sin(math.tau*293.665*T)+.3*np.sin(math.tau*392*T+.1))*swell_env
    swell=np.column_stack([swell,swell*.98])
    swell*=10**((-13.5-METER.integrated_loudness(swell[8*sr:11*sr]))/20)
    bed+=swell
    writewav(O/'mix.wav',bed)
    (O/'audio-cues.json').write_text(json.dumps(cues,indent=2))
    (Q/'audio-stem-design.json').write_text(json.dumps({'bed_lowpass_Hz':420,'engine_band_Hz':[35,1800],'global_gain_dB':20*math.log10(gain),'scene_automation_targets':targets.tolist(),'normalization':'separate quiet and launch targets with smooth gain automation; no dynamic loudnorm'},indent=2))
    print('AUDIO SOURCE integrated',METER.integrated_loudness(bed),'sample peak',20*np.log10(np.max(np.abs(bed))),flush=True)
def writewav(path,data):
    data=np.asarray(data);channels=1 if data.ndim==1 else data.shape[1]
    # Float WAV via ffmpeg avoids accidental int16 clipping.
    subprocess.run(['ffmpeg','-y','-v','error','-f','f32le','-ar','48000','-ac',str(channels),'-i','pipe:0','-c:a','pcm_f32le',str(path)],input=data.astype('<f4').tobytes(),check=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stills',action='store_true');parser.add_argument('--audio-only',action='store_true');args=parser.parse_args()
    (Q/'projection-provenance.json').write_text(json.dumps(G.REPORT,indent=2))
    if args.stills:
        for n in sorted(set(SAMPLES+[30,60,90,105,210,300,390,450,570,689])):
            sf,m,pic=draw(n);sf.write_to_png(str(Q/f'design-{n:04d}.png'))
        print('stills complete');return
    if not args.audio_only:
        cmd=['ffmpeg','-y','-hide_banner','-loglevel','info','-f','rawvideo','-pixel_format','bgr0','-video_size','1920x1080','-framerate','30','-i','pipe:0','-an','-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p','-profile:v','high','-tune','animation',str(O/'picture.mp4')]
        print('COMMAND',subprocess.list2cmdline(cmd),flush=True)
        metas=[]
        with open(Q/'encode-full.txt','w') as logfile:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=logfile)
            for n in range(N):
                sf,m,pic=draw(n);proc.stdin.write(bytes(sf.get_data()));metas.append(m)
                if n%60==0:print(f'RENDER {n}/690',flush=True)
            proc.stdin.close()
            if proc.wait():raise RuntimeError('encode failed')
        (Q/'frame-metadata.json').write_text(json.dumps(metas,separators=(',',':')))
    audio()
    final=P/'preview-v3.mp4'
    subprocess.run(['ffmpeg','-y','-v','warning','-i',str(O/'picture.mp4'),'-i',str(O/'mix.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','23','-movflags','+faststart',str(final)],check=True)
    print('RENDER COMPLETE',str(final),flush=True)
if __name__=='__main__':main()
