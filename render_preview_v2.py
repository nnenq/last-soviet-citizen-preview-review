import os
"""Revised 23-second preview. Uses shared Cairo primitives/face from render_preview.py.
Run python render_preview_v2.py --stills first; then python render_preview_v2.py.
QA, real mutation evidence, media probes and review exports: preview-v2/qa/.
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,subprocess,wave,io
import cairo,numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as ndi
from shapely.geometry import shape,Polygon,box as sbox,mapping
from shapely.ops import unary_union
from shapely import affinity
import pyloudnorm as pyln
import render_preview as B
P=Path(__file__).resolve().parent
O=P/"preview-v2"; Q=O/"qa"
for d in [O,Q,Q/"mutations",Q/"frames"]:d.mkdir(exist_ok=True)
W,H,FPS,N=1920,1080,30,690
BG=B.BG;RED=B.RED
C=None; FLAGS={}; ART=None; EXTRA={}
METER=pyln.Meter(48000)
SOURCE=json.loads((P/"assets/ussr-1991-traced.json").read_text())
PIECES=[]; used=Polygon()
for f in SOURCE["pieces"]:
    g=affinity.translate(affinity.scale(shape(f["geometry"]),1.25,.65,origin=(0,0)),180,400)
    g=g.difference(used);used=unary_union([used,g])
    PIECES.append((f["name"],g))
UNION=unary_union([g for _,g in PIECES])
_closed=UNION.buffer(3).buffer(-3)
_outer=list(_closed.geoms) if hasattr(_closed,"geoms") else [_closed]
SOLID_UNION=unary_union([Polygon(g.exterior) for g in _outer if g.geom_type=="Polygon"])
CENT=np.array([UNION.centroid.x,UNION.centroid.y])
# A narrow fracture seam is a fixed cut in the map. Subsequent movement is rigid.
FRACTURED=[(n,g.buffer(-1.5)) for n,g in PIECES]
def geopath(g):
    polys=list(g.geoms) if hasattr(g,"geoms") else [g]
    C.new_path()
    for p in polys:
        if p.is_empty or p.geom_type!="Polygon":continue
        for ring in [p.exterior,*p.interiors]:
            pts=list(ring.coords);C.move_to(*pts[0])
            for v in pts[1:]:C.line_to(*v)
            C.close_path()
    C.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)

def shifted(phase):
    ans=[]
    for name,g in FRACTURED:
        v=np.array([g.centroid.x,g.centroid.y])-CENT
        v=v/(np.linalg.norm(v)+1e-9)
        # Small rigid movement; max total displacement 8 px, not 8 per axis.
        off=v*8*phase
        ans.append((name,affinity.translate(g,*off),off.tolist()))
    return ans

# Check every actual fracture phase before rendering; if nonconvex neighbours
# would intersect, reduce the rigid displacement until all phases are safe.
DISPLACEMENT=8.
def separated(phase):
    ans=[]
    for name,g in FRACTURED:
        v=np.array([g.centroid.x,g.centroid.y])-CENT
        off=v/(np.linalg.norm(v)+1e-9)*DISPLACEMENT*phase
        ans.append((name,affinity.translate(g,*off),off.tolist()))
    return ans
for trial in [8.,6.,4.,2.,1.,.5]:
    DISPLACEMENT=trial
    bad=False
    for ph in np.linspace(0,1,31):
        gs=separated(ph)
        if any(gs[i][1].intersection(gs[j][1]).area>.02 for i in range(15) for j in range(i)):
            bad=True;break
    if not bad:break
if bad:raise RuntimeError("Map fracture cannot satisfy non-overlap")
_mask_surface=cairo.ImageSurface(cairo.FORMAT_A8,W,H)
_old_c=C;C=cairo.Context(_mask_surface)
_seams=unary_union([g.boundary for _,g in PIECES]).difference(SOLID_UNION.boundary.buffer(8))
geopath(_seams.buffer(1.5));C.set_source_rgba(1,1,1,1);C.fill();_mask_surface.flush()
INTERNAL_MASK=np.frombuffer(_mask_surface.get_data(),np.uint8).reshape(H,_mask_surface.get_stride())[:,:W]>0
C=_old_c

def ellipse(*a,**kw):return B.ellipse(*a,**kw)
def line(*a,**kw):return B.line(*a,**kw)
def rect(*a,**kw):return B.rect(*a,**kw)
def svg(*a,**kw):return B.svg(*a,**kw)
def text(*a,**kw):return B.text(*a,**kw)
def caption(*a,**kw):return B.caption(*a,**kw)

def earth(t,crack=False):
    ellipse(960,1940,1708,1708,None,"#3b5d73",2,alpha=.25)
    ellipse(960,1940,1702,1702,None,"#739aaf",2,alpha=.5)
    C.save();C.new_path();C.arc(960,1940,1700,0,math.tau);C.clip()
    grad=cairo.LinearGradient(0,240,0,1080)
    grad.add_color_stop_rgb(0,.06,.105,.17);grad.add_color_stop_rgb(1,.015,.025,.045)
    C.set_source(grad);C.paint()
    phase=B.ease((t-2.5)/.6) if crack else 0
    internal=(crack and t>=2.5) or FLAGS.get("internal_borders",False)
    if not internal:
        geopath(SOLID_UNION)
        B.fillstroke("#15263b",RED,3)
        EXTRA["map"]={"internal":False,"piece_count":1,"max_displacement":0}
    else:
        pieces=separated(phase)
        if FLAGS.get("map_displacement"):
            name,g,off=pieces[1]
            pieces[1]=(name,affinity.translate(g,20,0),[20,0])
        if FLAGS.get("map_overlap"):
            # Move a whole real republic onto its neighbour in the temp frame.
            na,ga,oa=pieces[4];target=pieces[5][1]
            ga=affinity.translate(ga,target.centroid.x-ga.centroid.x,target.centroid.y-ga.centroid.y)
            pieces[4]=(na,ga,oa)
        if FLAGS.get("piece_count"):pieces=pieces[:-1]
        for i,(name,g,offset) in enumerate(pieces):
            geopath(g)
            tint=(1.,.22+.012*(i%5),.22+.013*((i*3)%7),1)
            B.fillstroke(tuple(v*.16 if k<3 else .7 for k,v in enumerate(tint)),tint,2)
        EXTRA["map"]={"internal":True,"piece_count":len(pieces),
            "max_displacement":max(math.hypot(*o) for _,g,o in pieces),
            "polygons":[{"name":na,"geometry":mapping(g)} for na,g,o in pieces]}
    # Very faint fixed night lights; points are editorial, not a city inventory.
    for x,y in [(360,675),(390,650),(445,640),(575,720),(820,760),(1120,695)]:
        ellipse(x,y,1.3,1.3,"#d1b77d",alpha=.45)
    C.restore()

def station(t,hook=False):
    x=(1120+88*t) if hook else (1160+31*t)
    y=310+9*math.sin(t*.8)
    C.save();C.translate(x,y);C.rotate(-.08+.012*t)
    sf=.35 if FLAGS.get("small_mir") else 1.
    C.scale(sf,sf)
    rect(-12,-5,24,10,"#647681","#c4c8c7",1)
    rect(-4,-13,8,26,"#546875","#a7bac7",1)
    rect(-6,-17,12,5,"#4f626f","#a7bac7",1)
    for side in [-1,1]:
        line([(side*12,0),(side*20,0)],"#d8d4bf",1.5)
        rect(side*28-10,-13,20,26,"#223f57","#91afc5",1)
        for j in range(1,5):
            line([(side*28-10,-13+5.2*j),(side*28+10,-13+5.2*j)],"#7593a7",.6)
        line([(side*28,-13),(side*28,13)],"#8aa1b5",.7)
    ellipse(12,-3,3,3,"#fff3c4")
    B.box("prop","Mir",-39,-19,39,19,scale="O",minimum_width=60)
    EXTRA["mir_width"]=78*sf
    C.restore()

def rig(t):
    # Neutral-body posture, not a standing/walking pose: hip flexion 30 deg,
    # knee flexion 45 deg, arms raised, elbow flexion approx. 45 deg.
    root=(930+2.5*t,740-1.3*t)
    ang=math.radians(-12+.55*math.sin(t*.7))
    C.save();C.translate(*root);C.rotate(ang)
    hips=[(-18,-126),(18,-126)]
    legpts=[]
    for i,hip in enumerate(hips):
        thigh=math.radians(60+.6*math.sin(t*.7+i*.15))
        shank=thigh+math.radians(45)
        knee=(hip[0]+55*math.cos(thigh),hip[1]+55*math.sin(thigh))
        foot=(knee[0]+57*math.cos(shank),knee[1]+57*math.sin(shank))
        legpts.append((hip,knee,foot))
    shoulder_far=(-25,-236)
    aa=math.radians(155+1*math.sin(t*.6))
    elbow_far=(shoulder_far[0]+55*math.cos(aa),shoulder_far[1]+55*math.sin(aa))
    hand_far=(elbow_far[0]+55*math.cos(aa+math.pi/4),elbow_far[1]+55*math.sin(aa+math.pi/4))
    if FLAGS.get("gravity_pose"):
        legpts=[(hips[0],(-18,-70),(-18,-13)),(hips[1],(18,-70),(18,-13))]
        elbow_far=(-35,-180);hand_far=(-38,-126)
    B.limb(legpts[0],True);B.limb([shoulder_far,elbow_far,hand_far],True)
    svg("M-29 -255 Q-43 -188 -30 -119 Q0 -108 31 -120 Q40 -180 29 -255 Z",B.SUIT,B.INK,3)
    B.limb(legpts[1],False)
    line([(-20,-229),(20,-229)],"#a4a59e",2)
    line([(1,-222),(1,-134)],"#9a9d98",1.5)
    # Patch is attached to this same left-shoulder transform in every shot.
    rect(-26,-222,20,12,RED,None,r=2)
    C.save();C.translate(2,-301);C.scale(.95,.98)
    svg("M-45 -34 Q-37 -56 -10 -53 Q23 -58 42 -34 Q56 -1 40 26 Q25 48 -5 47 Q-42 44 -49 17 Q-58 -14 -45 -34 Z",B.SKIN,B.INK,3)
    svg("M-46 -24 C-58 -51 -31 -70 -8 -61 C1 -72 19 -68 24 -57 C34 -57 43 -48 41 -39 C23 -45 12 -43 2 -34 C-2 -47 -12 -45 -21 -37 C-27 -30 -35 -28 -46 -24 Z","#30343a")
    svg("M-32 -47 Q-19 -60 -5 -54 M8 -55 Q18 -59 27 -49",None,"#454950",2.5)
    bl=.7 if abs(t-1.65)<.075 else 4.5
    ellipse(-15,-1,4.3,bl,B.INK);ellipse(12,-2,4.3,bl,B.INK)
    svg("M-23 -17 Q-15 -20 -7 -18 M9 -19 Q18 -20 26 -16",None,B.INK,3.4)
    svg("M-5 19 Q5 17 16 19",None,B.INK,3)
    B.box("head","hero",-53,-71,51,49)
    C.restore()
    co,si=math.cos(ang),math.sin(ang)
    contact=(1004,471)
    dx,dy=contact[0]-root[0],contact[1]-root[1]
    hand=(co*dx+si*dy,-si*dx+co*dy)
    if FLAGS.get("detached_hand"):hand=(hand[0]-15,hand[1]-15)
    shoulder=(28,-233);elbow=B.ik(shoulder,hand,55,55,1)
    B.limb([shoulder,elbow,hand],False)
    world_hand=(root[0]+co*hand[0]-si*hand[1],root[1]+si*hand[0]+co*hand[1])
    C.restore()
    # Rail mounting brackets visibly terminate in bolted back-wall plates.
    for yy in [441,589]:
        if not FLAGS.get("rail_brackets"):
            rect(1032,yy+3,19,28,"#2a2d35","#777f87",2,r=3)
            ellipse(1041,yy+10,2,2,"#b4bac0");ellipse(1041,yy+24,2,2,"#b4bac0")
            line([(1004,yy),(1041,yy+11),(1041,yy+17)],"#858e97",5)
    line([(1004,441),(1004,589)],"#292e36",13)
    line([(1004,441),(1004,589)],"#a0a7af",8)
    if not FLAGS.get("detached_hand"):
        ellipse(*contact,8.8,8.8,B.SUIT,B.INK,2)
    EXTRA["body"]={"root":root,"angle_deg":math.degrees(ang),
        "hand":world_hand,"rail":contact,"rail_brackets":0 if FLAGS.get("rail_brackets") else 2,
        "hip_flex_deg":0 if FLAGS.get("gravity_pose") else 30,
        "knee_flex_deg":0 if FLAGS.get("gravity_pose") else 45,
        "free_elbow_flex_deg":45,"free_hand_local_y":hand_far[1],
        "root_accel_y":0,"speed":math.hypot(2.5,1.3),"rotation_speed":.55*.7,
        "leg_joints":legpts,"free_arm_joints":[shoulder_far,elbow_far,hand_far]}
    B.SCALES.extend([{"name":"hero","value":370,"expected":370},
        {"name":"window","value":63,"expected":63},{"name":"module","value":886,"expected":886}])

def cabin(t):
    zoom=1.25+.1*B.ease(t/4)
    C.save();C.translate(960,710);C.scale(zoom,zoom);C.translate(-960,-570)
    rect(517,212,886,886,"#111115",B.LINE,3,r=156)
    rect(544,240,832,832,None,"#303239",2,r=139)
    for x in [590,742,1135,1286]:line([(x,264),(x,990)],"#2e3037",1.5)
    for y in [365,730,950]:line([(546,y),(1374,y)],"#292c32",1.5)
    for x,y in [(575,340),(1165,390),(1165,760)]:
        rect(x,y,140,105,"#17191f","#464952",2,r=9)
        for j in range(4):line([(x+15,y+25+j*17),(x+105,y+25+j*17)],"#3c414a",2)
        ellipse(x+118,y+24,2.5,2.5,"#81939a",alpha=.6+.1*math.sin(t*.8))
    wx,wy=700,493
    wr=15 if FLAGS.get("scale") else 31.5
    ellipse(wx,wy,wr+8.5,wr+8.5,"#181b21","#60636b",3)
    C.save();C.new_path();C.arc(wx,wy,wr,0,math.tau);C.clip()
    rect(wx-wr,wy-wr,2*wr,2*wr,"#090e16")
    ellipse(wx-10+t,wy+34,54,54,B.BLUE)
    ellipse(wx-10+t,wy+34,55,55,None,"#78a1b2",1)
    C.restore()
    ellipse(wx,wy,wr,wr,None,"#a2a7a8",2)
    rig(t)
    B.SCALES[-2]["value"]=2*wr
    C.restore()

def vehicle():
    # The geometric rocket is always 500 px / 50 m tall in base scale R.
    svg("M941 592 L952 653 L951 861 L945 894 L925 894 L932 851 L934 659 Z","#656973",B.LINE,2)
    svg("M979 592 L990 659 L994 851 L1001 894 L981 894 L975 861 L974 653 Z","#656973",B.LINE,2)
    svg("M920 591 L934 651 L938 860 L931 900 L895 900 L903 860 L907 659 Z","#aaaeb1",B.LINE,2)
    svg("M1000 591 L1013 659 L1017 860 L1025 900 L989 900 L982 860 L986 651 Z","#aaaeb1",B.LINE,2)
    svg("M960 400 L978 445 L978 480 L972 496 L972 791 L984 900 L936 900 L948 791 L948 496 L942 480 L942 445 Z","#d1d0c8",B.LINE,2)
    for y in [480,507,605,786]:line([(949,y),(971,y)],"#747a80",2)
    for x in [913,960,1007]:
        ellipse(x,904,12,4,"#22242b",B.LINE,1)
    B.box("prop","rocket",895,400,1025,900,scale="R",height_px=500)
    B.SCALES.append({"name":"rocket","value":500,"expected":500})

def tower(retract=0):
    rect(803,353,34,553,"#191b20","#626774",2)
    for j in range(7):
        yy=365+j*76
        line([(805,yy),(835,yy+69),(805,yy+69),(835,yy)],"#525965",2)
    for yy,sgn in [(498,-1),(681,1)]:
        aa=math.radians(80*retract)*sgn
        line([(837,yy),(837+109*math.cos(aa),yy+109*math.sin(aa))],"#818891",6)
    rect(770,901,105,12,"#2b2e35","#656b74",2)

def exhaust(t,length=170):
    core="#fff3c4";warm="#ffb347"
    if FLAGS.get("red_flame"):core="#ff4646";warm="#d71927"
    for i,off in enumerate([-47,0,47]):
        x=960+off;y=906
        L=length*(1+.045*math.sin(t*53+i))
        grad=cairo.LinearGradient(x,y,x,y+L)
        grad.add_color_stop_rgba(0,*B.rgba(core)[:3],.95)
        grad.add_color_stop_rgba(.46,*B.rgba(warm)[:3],.9)
        grad.add_color_stop_rgba(1,*B.rgba(warm)[:3],0)
        C.new_path();C.move_to(x-13,y)
        C.curve_to(x-21,y+L*.3,x-8,y+L*.86,x,y+L)
        C.curve_to(x+8,y+L*.8,x+22,y+L*.3,x+13,y);C.close_path()
        C.set_source(grad);C.fill()
        svg(f"M{x-5} {y} Q{x-5} {y+L*.3} {x} {y+L*.65} Q{x+6} {y+L*.25} {x+5} {y} Z",core)
    EXTRA["flame"]={"core":core,"outer":warm}

def smoke(age):
    if age<=0:return
    strength=B.ease(age/.28)
    for side in [-1,1]:
        for i in range(11):
            delay=i*.11;a=max(0,age-delay)
            if a<=0:continue
            x=960+side*(35+100*a+i*20);y=926-8*math.sin(i*1.7+a)
            rx=25+46*a+i*1.5;ry=20+31*a
            g=cairo.RadialGradient(-rx*.25,-rx*.3,0,0,0,rx)
            g.add_color_stop_rgba(0,.816,.816,.831,.6*strength)
            g.add_color_stop_rgba(.65,.54,.54,.565,.6*strength)
            g.add_color_stop_rgba(1,.54,.54,.565,0)
            C.save();C.translate(x,y);C.scale(1,ry/rx);C.arc(0,0,rx,0,math.tau)
            C.set_source(g)
            C.fill();C.restore()
    EXTRA["smoke"]={"alpha":.6,"colors":["#8a8a90","#d0d0d4"]}

def launch(t,phase):
    if phase=="wide":
        C.save();C.translate(-t*.8,0)
        line([(0,910),(1920,910)],"#666a72",2)
        tower(0);vehicle();C.restore()
    elif phase=="engine":
        # Explicit engine insert: the upper rocket is intentionally outside this
        # detail composition. Same base scale, common camera zoom exactly 2x.
        C.save();C.rectangle(0,220,W,H-220);C.clip()
        C.translate(960,570);C.scale(2,2);C.translate(-960,-900)
        vehicle();exhaust(t,180+30*B.ease(t/2.5));smoke(t+.03)
        C.restore()
    else:
        progress=t/2.5
        dy=-180*progress-110*progress*progress
        shake=4.5*math.sin(t*63)*math.exp(-t*.4)
        C.save();C.translate(960+shake,610+3.6*math.sin(t*54))
        C.scale(1.2,1.2);C.translate(-960,-650-dy*.82)
        line([(0,910),(1920,910)],"#666a72",2);tower(1)
        smoke(t+2.5)
        C.save();C.translate(0,dy);vehicle();exhaust(t,190);C.restore()
        C.restore()
    EXTRA["launch"]={"phase":phase,"total_seconds":8}

def day(t):
    # Prelaunch only. Orbit/cabin are undated prologue or general routine.
    n=1
    if FLAGS.get("date"):n=9
    if FLAGS.get("backwards"):n=0
    text("DAY",64,104,40,"#878991",font="mono",center=False,role="counter")
    text(str(n),153,104,60,RED,font="mono",center=False,role="counter")
    text("18 MAY 1991",64,164,40,"#9b9da4",font="mono",center=False,role="date")
    EXTRA["day"]={"day":n,"date":"1991-05-18"}

def draw(n,flags=None):
    global C,FLAGS,EXTRA,ART
    FLAGS=flags or {};EXTRA={}
    actual_n=n
    if FLAGS.get("freeze") and 240<=n<=305:n=270
    t=n/30
    sf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H);C=cairo.Context(sf)
    B.C=C;B.BOUNDS=[];B.SCALES=[]
    C.set_line_cap(cairo.LINE_CAP_ROUND);C.set_line_join(cairo.LINE_JOIN_ROUND)
    B.src(BG);C.paint()
    if t<4:
        shot=1;B.stars(t)
        shake_age=t-2.5
        C.save()
        if 0<=shake_age<.15:
            C.translate(5*math.sin(shake_age*110),4*math.sin(shake_age*95))
        earth(t,True);station(t,True);C.restore()
    elif t<8:
        shot=2;cabin(t-4)
    elif t<11:
        shot=3;launch(t-8,"wide")
    elif t<13.5:
        shot=4;launch(t-11,"engine")
    elif t<16:
        shot=5;launch(t-13.5,"low")
    else:
        shot=6;B.stars(t)
        C.save();C.translate(-(t-16)*2,1.1*(t-16));earth(t-16,False)
        station(t-16,False);C.restore()
    if FLAGS.get("stroke"):
        line([(600,128),(1320,128)],B.LINE,3)
    if FLAGS.get("margin_stroke"):
        font=ImageFont.truetype(str(B.FONTS["caption"]),56)
        bb=font.getbbox("He left Earth from one country.",anchor="ls")
        xx=960-(bb[2]-bb[0])/2-6
        line([(xx,110),(xx,145)],B.LINE,3)
    sf.flush()
    world=np.asarray(Image.frombuffer("RGB",(W,H),bytes(sf.get_data()),"raw","BGRX",0,1)).copy()
    art=np.max(np.abs(world.astype(np.int16)-np.array([13,13,16])),axis=2)>2
    internal_red=0
    if shot==1 and actual_n<75:
        red=(world[:,:,0]>100)&(world[:,:,0]>2*world[:,:,1])
        internal_red=int(np.count_nonzero(red&INTERNAL_MASK))
    # Editorial graphics are now added separately, after the picture snapshot.
    if shot==1:caption("He left Earth from one country.",t,0,1 if FLAGS.get("short_caption") else 4)
    elif shot==2:
        if FLAGS.get("text_head"):
            text("He came back to another.",890,600,56,role="caption")
        else:caption("He came back to another.",t,4,8)
    elif shot in [3,4,5]:
        day(t)
        caption(["May 1991. Sergei Krikalev flies","to the space station Mir."],t,8.05,15.9)
        if shot==3:text(str(3-int(t-8)),1210,594,96,RED,font="mono",role="countdown")
    else:caption("The plan: five months in orbit.",t,16.1,23)
    if FLAGS.get("text_text"):text("OVERLAP",960,152,56,role="caption")
    if FLAGS.get("text_margin"):text("OUT",1900,152,56,center=False,role="caption")
    if FLAGS.get("text_zone"):text("WRONG ZONE",960,290,56,role="caption")
    if FLAGS.get("head_crop"):
        # A rendered duplicate from the same canonical face is moved outside
        # the frame specifically to exercise the head-bound rule.
        ellipse(1908,430,47,50,B.SKIN,B.INK,3)
        B.box("head","mutated head",1861,380,1955,480)
    if FLAGS.get("earth_foot"):
        # Earth-contact fixture, drawn in a temporary frame. It is not a shot in
        # this orbit-only preview.
        line([(300,950),(700,950)],B.LINE,3)
        line([(470,850),(480,910),(480,935)],B.SUIT,20)
        EXTRA["earth_contacts"]=[{"foot_y":945,"ground_y":950}]
    if FLAGS.get("zero_g_accel") and "body" in EXTRA:
        # The shifted free prop is genuinely drawn; its trajectory metadata
        # uses these same physical world coordinates in the motion test.
        y=380+.5*8*(t-4)*(t-4)
        rect(650,y,24,16,"#a2a8aa")
        EXTRA.setdefault("free_props",[]).append({"position":[650,y],"velocity":[0,8*(t-4)],"acceleration":[0,8],"rotation_speed":0})
    if FLAGS.get("zero_g_speed") and "body" in EXTRA:
        rect(650+30*t,380,24,16,"#a2a8aa")
        EXTRA.setdefault("free_props",[]).append({"position":[650+30*t,380],"velocity":[30,0],"acceleration":[0,0],"rotation_speed":0})
    if FLAGS.get("rotation") and "body" in EXTRA:
        C.save();C.translate(650,420);C.rotate(math.radians(10*t));rect(-12,-8,24,16,"#a2a8aa");C.restore()
        EXTRA.setdefault("free_props",[]).append({"position":[650,420],"velocity":[0,0],"acceleration":[0,0],"rotation_speed":10})
    bounds=copy.deepcopy(B.BOUNDS)
    for b in bounds:
        if b["role"]=="text" and b.get("text_role")=="caption":
            x0,y0,x1,y1=b["box"];pad=8
            x0=max(0,int(x0-pad));y0=max(0,int(y0-pad));x1=min(W,math.ceil(x1+pad));y1=min(H,math.ceil(y1+pad))
            b["art_pixels_padded"]=int(art[y0:y1,x0:x1].sum())
    sf.flush()
    meta={"frame":actual_n,"time":actual_n/30,"shot":shot,"bounds":bounds,
        "scales":copy.deepcopy(B.SCALES),"reserved_zone_art_pixels":int(art[:200,380:1540].sum()),
        "caption_id":0 if shot==1 else 1 if shot==2 else 2 if shot in [3,4,5] else 3,
        "premature_internal_red_pixels":internal_red,**EXTRA}
    return sf,meta

def audio():
    sr=48000;tt=np.arange(23*sr)/sr;rng=np.random.default_rng(19910518)
    def noise(lo,hi):
        v=rng.normal(size=len(tt));s=np.fft.rfft(v);f=np.fft.rfftfreq(len(v),1/sr)
        s*=1/(1+(lo/np.maximum(1,f))**6)/(1+(f/hi)**6)
        v=np.fft.irfft(s,n=len(v));return v/(v.std()+1e-9)
    # Phone-audible mid-band editorial air. Never model the vacuum as literal
    # audible air. Cabin ventilation and launch roar have distinct spectra.
    air=noise(240,1600)
    bed=.17*air+.08*np.sin(2*np.pi*196*tt)+.055*np.sin(2*np.pi*294*tt)
    bed*=1+.06*np.sin(tt*.9)
    cabinmask=((tt>=4)&(tt<8))
    bed+=cabinmask*.055*noise(360,2300)
    signal=bed
    cues=[]
    stemdir=O/"event-templates";stemdir.mkdir(exist_ok=True)
    def save_template(name,s):
        file=stemdir/(name+".wav")
        with wave.open(str(file),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr)
            f.writeframes((np.clip(s,-1,1)*32767).astype("<i2").tobytes())
        return str(file)
    def event(tm,duration,name,typ,amp):
        nonlocal signal
        k=round(tm*sr);l=round(duration*sr);t=np.arange(l)/sr
        if typ=="beep":s=np.sin(math.tau*740*t)*np.minimum(1,t/.003)*np.exp(-t*12)
        elif typ=="crack":
            s=rng.normal(size=l)*np.exp(-t*16)+.3*np.sin(math.tau*110*t)*np.exp(-t*22)
        else:s=rng.normal(size=l)*np.exp(-t*21)+.4*np.sin(math.tau*160*t)*np.exp(-t*20)
        signal[k:k+l]+=amp*s[:min(l,len(signal)-k)]
        template=save_template(name.replace(" ","-"),amp*s)
        cues.append({"name":name,"time":tm,"visual_frame":round(tm*30),"sound_frame":round(tm*30),"offset_frames":0,"template":template})
    event(2.5,.44,"map fracture","crack",.19)
    for tm,v in [(8,3),(9,2),(10,1)]:event(tm,.16,f"countdown {v}","beep",.20)
    event(13.5,.3,"launch release","clunk",.14)
    roar=noise(35,800)*.22+noise(600,3500)*.12
    env=np.clip((tt-11)/.12,0,1)*np.clip((16.03-tt)/.03,0,1)
    signal+=roar*env
    start=11*sr
    template=save_template("ignition",(roar*env)[start:start+round(.25*sr)])
    cues.append({"name":"engine ignition","time":11,"visual_frame":330,"sound_frame":330,"offset_frames":0,"template":template})
    stereo=np.column_stack([signal,signal*.99])
    # Smooth each-second energy corrections, with gradual transitions rather
    # than hard gain jumps. Then loudnorm sets integrated/true-peak delivery.
    levels=[METER.integrated_loudness(stereo[i*sr:(i+1)*sr]) for i in range(23)]
    targets=np.array([-14.5]*11+[-13.5]*5+[-14.5]*7)
    gains=10**((targets-np.array(levels))/20)
    envelope=np.interp(tt,np.arange(23)+.5,gains,left=gains[0],right=gains[-1])
    stereo*=envelope[:,None]
    # Do not introduce a fade-in that makes the hook silent.
    stereo[-240:]*=np.linspace(1,0,240)[:,None]
    with wave.open(str(O/"mix.wav"),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr)
        f.writeframes((np.clip(stereo,-1,1)*32767).astype("<i2").tobytes())
    (O/"audio-cues.json").write_text(json.dumps(cues,indent=2))
    (O/"silence-policy.json").write_text(json.dumps({"preview_allowed_intervals":[],
        "full_film_planned_interval":{"start":86.0,"end":87.0,"duration":1.0,"label":"USSR-collapse intentional silence",
        "status":"reserved; full timeline must keep this explicit interval"}} ,indent=2))

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--stills",action="store_true")
    args=parser.parse_args()
    if args.stills:
        for n in [0,75,90,150,270,360,420,480,660]:
            sf,m=draw(n);sf.write_to_png(str(Q/f"design-{n:04d}.png"))
        print("stills done; fracture displacement",DISPLACEMENT);return
    from qa_preview_v2 import check_frame,check_pixels,verify_media,mutations,exports,observed_caption_rules,observed_launch_rule
    log=[]
    def say(s):print(s,flush=True);log.append(s)
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","info","-f","rawvideo","-pixel_format","bgr0",
        "-video_size","1920x1080","-framerate","30","-i","pipe:0","-an","-c:v","libx264",
        "-crf","16","-preset","slow","-pix_fmt","yuv420p","-profile:v","high","-tune","animation",
        "-minrate","10000k","-maxrate","10000k","-bufsize","20000k",
        "-x264-params","nal-hrd=vbr:filler=1",str(O/"picture.mp4")]
    say("COMMAND "+subprocess.list2cmdline(cmd))
    logfile=open(Q/"encode-full.txt","w")
    enc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=logfile)
    metas=[];issues=[];hashes=[];prev=None
    for n in range(N):
        sf,m=draw(n)
        issues.extend(check_frame(m,prev));prev=m;metas.append(m)
        data=bytes(sf.get_data());hashes.append(hashlib.sha256(data).hexdigest())
        enc.stdin.write(data)
        if n%90==0:say(f"RENDER {n}/{N}")
    enc.stdin.close()
    if enc.wait()!=0:raise RuntimeError("encode failed; see encode-full.txt")
    logfile.close()
    issues.extend(check_pixels(hashes))
    issues.extend(observed_caption_rules(metas))
    issues.extend(observed_launch_rule(metas))
    say("Geometry / timeline / picture issues: "+str(len(issues)))
    (Q/"frame-metadata.json").write_text(json.dumps(metas))
    (Q/"render-issues.json").write_text(json.dumps(issues,indent=2))
    if issues:raise RuntimeError("Fix geometry before delivery")
    audio()
    res=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(O/"mix.wav"),"-af",
        "loudnorm=I=-14:TP=-1.7:LRA=7:print_format=json","-f","null",os.devnull],capture_output=True,text=True,check=True)
    (Q/"loudness-source.txt").write_text(res.stderr)
    j=json.JSONDecoder().raw_decode(res.stderr[res.stderr.rfind("{"):])[0]
    af=("loudnorm=I=-14:TP=-1.7:LRA=7:linear=true:measured_I="+j["input_i"]+
        ":measured_TP="+j["input_tp"]+":measured_LRA="+j["input_lra"]+
        ":measured_thresh="+j["input_thresh"]+":offset="+j["target_offset"])
    final=P/"preview-v2.mp4"
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","warning","-i",str(O/"picture.mp4"),
        "-i",str(O/"mix.wav"),"-af",af,"-map","0:v:0","-map","1:a:0","-c:v","copy",
        "-c:a","aac","-b:a","192k","-ar","48000","-t","23","-movflags","+faststart",str(final)],check=True)
    result=verify_media(final,Q)
    say(json.dumps(result,indent=2))
    issues.extend(result["issues"])
    mut=mutations(draw,metas,hashes,final,Q)
    say("Mutation test output:\n"+"\n".join(mut["lines"]))
    if mut["failed"]:issues.extend({"rule":"mutation_not_caught","detail":s} for s in mut["failed"])
    exports(final,Q)
    say("QA issues: "+str(len(issues)))
    (Q/"QA-FULL-OUTPUT.txt").write_text("\n".join(log)+"\n",encoding="utf-8")
    (Q/"qa-result.json").write_text(json.dumps({"issues":issues,"mutations":mut,"media":result,
        "scope":"23-second revised preview; full film awaits user approval"},indent=2),encoding="utf-8")
    if issues:raise RuntimeError("QA failed; see report")
if __name__=="__main__":main()

