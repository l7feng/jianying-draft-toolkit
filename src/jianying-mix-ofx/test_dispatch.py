"""Native OFX button -> pythonw -> real embedded AAF in a synthetic host."""
import pathlib,ctypes as C,json,sys,time,wave,os,uuid
ROOT=pathlib.Path(__file__).resolve().parents[2];SRC=ROOT/'src/jianying-mix-ofx';BUILD=ROOT/'build/ofx-mix-aaf-v0.1'
prefix=(ROOT/'src/jianying-ofx-probe/test_probe.py').read_text(encoding='utf-8-sig').split('dll=C.CDLL')[0]
exec(compile(prefix,'synthetic-host','exec'),globals())
work=BUILD/('dispatch-'+uuid.uuid4().hex[:8]);work.mkdir();draft=work/'单集';draft.mkdir()
with wave.open(str(draft/'对白.wav'),'wb') as f:f.setparams((1,2,48000,0,'NONE',''));f.writeframes(b'\0\0'*48000)
data=dict(duration=2000000,materials=dict(audios=[dict(id='audio',path='对白.wav')]),tracks=[dict(type='audio',name='对白',segments=[dict(material_id='audio',source_timerange=dict(start=0,duration=1000000),target_timerange=dict(start=500000,duration=1000000))])])
(draft/'draft_content.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
qt[4]=cb(I,[V,PS],paramvalue)
def setvalue(h,v):props[h][b'OfxParamPropDefault']={0:v};return 0
qt[8]=cb(I,[V,S],setvalue)
dll=C.CDLL(str(BUILD/'dispatch-test.dll'));dll.OfxGetPlugin.argtypes=[I];dll.OfxGetPlugin.restype=C.POINTER(Plugin);p=dll.OfxGetPlugin(0).contents
hp=new({b'OfxPropName':{0:b'Synthetic AAF dispatch host'}});fc=FETCH(fetch);h=Host(hp,fc);p.setHost(C.byref(h));assert p.main(b'OfxActionLoad',None,None,None)==0
assert p.main(b'OfxActionDescribe',effect,None,None)==0
cx=new({b'OfxImageEffectPropContext':{0:b'OfxImageEffectContextFilter'}});assert p.main(b'OfxImageEffectActionDescribeInContext',effect,cx,None)==0
assert props[effect][b'OfxPropLabel'][0].decode('utf-8')=='剪映混音交互'
for key in params:
    label=props[params[key]][b'OfxPropLabel'][0].decode('utf-8')
    assert any('\u4e00'<=x<='\u9fff' for x in label) and ' / ' not in label,label
# Host default-string problem has an explicit user-action workaround, preserving existing paths.
props[params[b'output_path']][b'OfxParamPropDefault']={0:b''}
fill=new({b'OfxPropName':{0:b'fill_output'},b'OfxPropChangeReason':{0:b'OfxChangePluginEdited'}})
assert p.main(b'OfxActionInstanceChanged',effect,fill,None)==0
assert not props[params[b'output_path']][b'OfxParamPropDefault'][0]
props[fill][b'OfxPropChangeReason']={0:b'OfxChangeUserEdited'};assert p.main(b'OfxActionInstanceChanged',effect,fill,None)==0
assert props[params[b'output_path']][b'OfxParamPropDefault'][0].startswith(b'D:')
for key,value in {b'source_path':str(draft),b'output_path':str(work/'输出')}.items():props[params[key]][b'OfxParamPropDefault']={0:value.encode('utf-8')}
assert p.main(b'OfxActionInstanceChanged',effect,fill,None)==0
assert props[params[b'output_path']][b'OfxParamPropDefault'][0]==str(work/'输出').encode('utf-8')
jobs=pathlib.Path(os.environ['LOCALAPPDATA'])/'JYMixBridge';before=set(jobs.glob('*/result.json')) if jobs.exists() else set()
change=new({b'OfxPropName':{0:b'export_aaf'},b'OfxPropChangeReason':{0:b'OfxChangePluginEdited'}})
assert p.main(b'OfxActionInstanceChanged',effect,change,None)==0
assert set(jobs.glob('*/result.json'))==before
props[change][b'OfxPropChangeReason']={0:b'OfxChangeUserEdited'};assert p.main(b'OfxActionInstanceChanged',effect,change,None)==0
result=None
for _ in range(200):
    for path in set(jobs.glob('*/result.json'))-before:
        try:result=json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:pass
    if result:break
    time.sleep(.1)
assert result and result['ok'],result
assert pathlib.Path(result['result']['aaf']).is_file()
assert not list((work/'输出').rglob('*.wav')),'AAF must not require a standalone track export'
out=dict(native_button_to_aaf='pass',chinese_labels='pass',fill_empty_output_only='pass',non_user_events_do_not_dispatch='pass',no_track_wav_export='pass',real_jianying_ui=False,result=result)
(BUILD/'dispatch-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='result'},ensure_ascii=False))
