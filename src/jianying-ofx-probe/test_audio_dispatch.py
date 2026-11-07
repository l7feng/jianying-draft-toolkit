"""Exercise native OFX user-action dispatch in a synthetic host, without dialog UI."""
import pathlib,ctypes as C,json,sys,time,wave,os,uuid
ROOT=pathlib.Path(__file__).resolve().parents[2]
SRC=ROOT/"src/jianying-ofx-probe";BUILD=ROOT/"build/ofx-audio-v0.1"
prefix=(SRC/"test_probe.py").read_text(encoding="utf-8-sig").split("dll=C.CDLL")[0]
exec(compile(prefix,"synthetic-host","exec"),globals())
work=BUILD/("dispatch-"+uuid.uuid4().hex[:8]);work.mkdir();media=work/"audio";media.mkdir()
with wave.open(str(media/"DX.wav"),"wb") as f:
    f.setparams((1,2,48000,0,"NONE","not compressed"));f.writeframes(b"\0\0"*48000)
def pvalue(h,out):
    value=props[h].get(b"OfxParamPropDefault",{0:b""})[0]
    if props[h][b"type"][0] in [b"OfxParamTypeChoice",b"OfxParamTypeInteger"]:C.cast(out,PI)[0]=value
    else:C.cast(out,PS)[0]=value
    return 0
qt[4]=cb(I,[V,V],pvalue)
dll=C.CDLL(str(BUILD/"dispatch-test.dll"));dll.OfxGetPlugin.argtypes=[I];dll.OfxGetPlugin.restype=C.POINTER(Plugin)
p=dll.OfxGetPlugin(0).contents
hprops=new({b"OfxPropName":{0:b"Synthetic dispatch test"}});fc=FETCH(fetch);h=Host(hprops,fc)
p.setHost(C.byref(h));assert p.main(b"OfxActionLoad",None,None,None)==0
assert p.main(b"OfxActionDescribe",effect,None,None)==0
cx=new({b"OfxImageEffectPropContext":{0:b"OfxImageEffectContextFilter"}})
assert p.main(b"OfxImageEffectActionDescribeInContext",effect,cx,None)==0
for key,value in {b"source_path":str(media),b"output_path":str(work/"exports"),b"manifest_path":"",b"copy_path":""}.items():
    props[params[key]][b"OfxParamPropDefault"]={0:value.encode("utf-8")}
props[params[b"export_mode"]][b"OfxParamPropDefault"]={0:1}
jobs=pathlib.Path(os.environ["LOCALAPPDATA"])/"JyOfxAudio"
before=set(jobs.glob("*/result.json")) if jobs.exists() else set()
change=new({b"OfxPropName":{0:b"export_audio"},b"OfxPropChangeReason":{0:b"OfxChangeUserEdited"}})
assert p.main(b"OfxActionInstanceChanged",effect,change,None)==0
result=None
for _ in range(150):
    for path in set(jobs.glob("*/result.json"))-before:
        try:r=json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:continue
        result=r
    if result:break
    time.sleep(0.1)
assert result and result["ok"],result
assert result["result"]["output"]==str(work/"exports")
assert len(list((work/"exports").rglob("*.wav")))==1
out=dict(native_button_callback_to_python_worker="pass",real_file_export="pass",
 source="synthetic-host",real_jianying_ui=False,test_root=str(work),job=result["job"])
(BUILD/"dispatch-test-results.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))

