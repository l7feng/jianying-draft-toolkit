"""Independent synthetic OFX host. This is NOT a Jianying compatibility test."""
import ctypes as C
import json
import pathlib
import sys
V=C.c_void_p; I=C.c_int; D=C.c_double; S=C.c_char_p
PI=C.POINTER(I); PV=C.POINTER(V); PS=C.POINTER(S)
CB=C.CFUNCTYPE
keep=[]; props={}; serial=100; params={}; clips={}; images={}; releases=[]
def new(data=None):
    global serial
    serial+=1; props[serial]=data or {}; return serial
def cb(restype,args,fn):
    x=CB(restype,*args)(fn);keep.append(x);return C.cast(x,V).value
def table(size, entries):
    t=(V*size)()
    for idx,args,fn in entries:t[idx]=cb(I,args,fn)
    keep.append(t);return t
def setter(h,k,i,v):props[h].setdefault(k,{})[i]=v;return 0
def getter(h,k,i,out):
    try:out[0]=props[h][k][i];return 0
    except KeyError:return 11
def getn(h,k,n,out):
    for i in range(n):
        if getter(h,k,i,C.cast(C.byref(out.contents,i*C.sizeof(out._type_)),C.POINTER(out._type_))):return 11
    return 0
def dimension(h,k,out):
    if k not in props[h]:return 11
    out[0]=len(props[h][k]);return 0
pt=table(18,[
 (0,[V,S,I,V],setter),(1,[V,S,I,S],setter),(2,[V,S,I,D],setter),(3,[V,S,I,I],setter),
 (8,[V,S,I,PV],getter),(9,[V,S,I,PS],getter),(10,[V,S,I,C.POINTER(D)],getter),
 (11,[V,S,I,PI],getter),(15,[V,S,I,PI],getn),(17,[V,S,PI],dimension)])
effect=new(); pset=new()
def getprops(h,out):out[0]=h;return 0
def getparams(h,out):out[0]=pset;return 0
def clipdefine(h,name,out):
    ch=new();clips[name]=ch;out[0]=ch;return 0
def clipget(h,name,out,ps):
    if name not in clips:return 11
    out[0]=clips[name]
    if ps:ps[0]=clips[name]
    return 0
def imageget(ch,time,region,out):
    if ch not in images:return 1
    out[0]=images[ch];return 0
def release(h):releases.append(h);return 0
et=table(13,[
 (0,[V,PV],getprops),(1,[V,PV],getparams),(2,[V,S,PV],clipdefine),
 (3,[V,S,PV,PV],clipget),(4,[V,PV],getprops),(5,[V,D,V,PV],imageget),
 (6,[V],release),(8,[V],lambda h:0)])
def paramdefine(h,typ,name,out):
    ph=new({b"type":{0:typ}});params[name]=ph;out[0]=ph;return 0
def paramget(h,name,out,ps):
    if name not in params:return 11
    out[0]=params[name]
    if ps:ps[0]=params[name]
    return 0
def paramvalue(h,out):
    out[0]=props[h].get(b"OfxParamPropDefault",{0:b""})[0];return 0
qt=table(18,[
 (0,[V,S,S,PV],paramdefine),(1,[V,S,PV,PV],paramget),(4,[V,PS],paramvalue)])
fetches=[];missing=False
def fetch(h,name,ver):
    fetches.append((name.decode(),ver))
    if missing:return None
    suites={b"OfxPropertySuite":pt,b"OfxImageEffectSuite":et,b"OfxParameterSuite":qt}
    t=suites.get(name)
    return C.addressof(t) if t is not None and ver==1 else None
FETCH=CB(V,V,S,I)
class Host(C.Structure):_fields_=[("host",V),("fetch",FETCH)]
SET=CB(None,V); ENTRY=CB(I,S,V,V,V)
class Plugin(C.Structure):
    _fields_=[("api",S),("apiVersion",I),("identifier",S),("major",C.c_uint),
              ("minor",C.c_uint),("setHost",SET),("main",ENTRY)]
dll=C.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
dll.OfxGetNumberOfPlugins.restype=I
dll.OfxGetPlugin.argtypes=[I];dll.OfxGetPlugin.restype=C.POINTER(Plugin)
assert dll.OfxGetNumberOfPlugins()==1
assert not dll.OfxGetPlugin(-1) and not dll.OfxGetPlugin(1)
p=dll.OfxGetPlugin(0).contents
assert p.api==b"OfxImageEffectPluginAPI" and p.apiVersion==1
hostprops=new({b"OfxPropName":{0:b"Synthetic OFX test host"},
 b"OfxImageEffectPropSupportedContexts":{0:b"OfxImageEffectContextFilter"}})
fetchcb=FETCH(fetch);host=Host(hostprops,fetchcb);p.setHost(C.byref(host))
assert not fetches,"setHost must not fetch any suites"
missing=True
assert p.main(b"OfxActionLoad",None,None,None)!=0
missing=False
assert p.main(b"OfxActionLoad",None,None,None)==0
assert p.main(b"OfxActionDescribe",effect,None,None)==0
context=new({b"OfxImageEffectPropContext":{0:b"OfxImageEffectContextFilter"}})
assert p.main(b"OfxImageEffectActionDescribeInContext",effect,context,None)==0
assert set(params)=={b"probe_level",b"probe_button",b"param_draft_path"}
assert p.main(b"OfxActionCreateInstance",effect,None,None)==0
changed=new({b"OfxPropName":{0:b"probe_button"}})
assert p.main(b"OfxActionInstanceChanged",effect,changed,None)==0
assert p.main(b"UnknownAction",effect,None,None)==14
cases=[]
def img(buf,bounds,bpp,stride,offset=0):
    depth={4:b"OfxBitDepthByte",8:b"OfxBitDepthShort",16:b"OfxBitDepthFloat"}[bpp]
    return new({b"OfxImagePropData":{0:C.addressof(buf)+offset},
      b"OfxImagePropBounds":dict(enumerate(bounds)),
      b"OfxImagePropRowBytes":{0:stride},
      b"OfxImageEffectPropPixelDepth":{0:depth},
      b"OfxImageEffectPropComponents":{0:b"OfxImageComponentRGBA"}})
for bpp in [4,8,16]:
    for negative in [False,True]:
        stride=3*bpp+8
        src=(C.c_ubyte*(stride*2))(*[(i*17+3)%256 for i in range(stride*2)])
        dst=(C.c_ubyte*(stride*2))(*([199]*(stride*2)))
        sign=-1 if negative else 1;offset=stride if negative else 0
        ah=img(src,[5,7,8,9],bpp,sign*stride,offset)
        bh=img(dst,[5,7,8,9],bpp,sign*stride,offset)
        images[clips[b"Source"]]=ah;images[clips[b"Output"]]=bh
        args=new({b"OfxPropTime":{0:0.0},b"OfxImageEffectPropRenderWindow":dict(enumerate([4,6,10,11]))})
        releases.clear()
        assert p.main(b"OfxImageEffectActionRender",effect,args,None)==0
        for row in range(2):
            assert bytes(src)[row*stride:row*stride+3*bpp]==bytes(dst)[row*stride:row*stride+3*bpp]
            assert bytes(dst)[row*stride+3*bpp:(row+1)*stride]==bytes([199]*8),"row padding overwritten"
        assert releases==[ah,bh]
        cases.append({"bpp":bpp,"negative_stride":negative,"pixel_copy_and_bounds":"pass"})
# Output pixels outside source become transparent black.
src=(C.c_ubyte*4)(11,22,33,44);dst=(C.c_ubyte*12)(*([199]*12))
ah=img(src,[1,0,2,1],4,4);bh=img(dst,[0,0,3,1],4,12)
images[clips[b"Source"]]=ah;images[clips[b"Output"]]=bh
args=new({b"OfxPropTime":{0:0.0},b"OfxImageEffectPropRenderWindow":dict(enumerate([0,0,3,1]))})
assert p.main(b"OfxImageEffectActionRender",effect,args,None)==0
assert bytes(dst)==bytes([0,0,0,0,11,22,33,44,0,0,0,0])
# Reject incompatible image layouts and release all acquired handles.
props[bh][b"OfxImageEffectPropComponents"][0]=b"OfxImageComponentRGB"
releases.clear()
assert p.main(b"OfxImageEffectActionRender",effect,args,None)!=0
assert releases==[ah,bh]
images.pop(clips[b"Output"]);releases.clear()
assert p.main(b"OfxImageEffectActionRender",effect,args,None)!=0
assert releases==[ah]
assert p.main(b"OfxActionDestroyInstance",effect,None,None)==0
assert p.main(b"OfxActionUnload",None,None,None)==0
result={"plugin":p.identifier.decode(),"plugin_count":1,"metadata":"pass",
 "setHost_no_api_calls":"pass","missing_suites":"pass","parameter_events":"pass",
 "render_cases":cases,"transparent_outside_source":"pass",
 "unsupported_components_release":"pass","missing_output_release":"pass",
 "unknown_action":"pass","real_jianying_host_tested":False}
text=json.dumps(result,ensure_ascii=False,indent=2);print(text)
if len(sys.argv)>2:pathlib.Path(sys.argv[2]).write_text(text,encoding="utf-8")

