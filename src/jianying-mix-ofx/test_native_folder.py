"""Synthetic OFX host tests native selection/writeback and real AAF dispatch."""
import pathlib,ctypes as C,json,sys,time,wave,os,uuid
ROOT=pathlib.Path(r'D:\Ai-Files\Repos\GitHub\jianying-draft-toolkit');BUILD=ROOT/'build/ofx-native-v0.3'
work=BUILD/('native-'+uuid.uuid4().hex[:8]);work.mkdir();os.environ['LOCALAPPDATA']=str(work/'appdata')
prefix=(ROOT/'src/jianying-ofx-probe/test_probe.py').read_text(encoding='utf-8-sig').split('dll=C.CDLL')[0]
exec(compile(prefix,'synthetic-host','exec'),globals())
draft=work/'单集 中文 空格';draft.mkdir();output=work/'输出 中文 空格';output.mkdir()
with wave.open(str(draft/'对白.wav'),'wb') as f:f.setparams((1,2,48000,0,'NONE',''));f.writeframes(b'\0\0'*48000)
data=dict(duration=2000000,materials=dict(audios=[dict(id='a',path='对白.wav')]),tracks=[dict(type='audio',name='对白',segments=[dict(material_id='a',source_timerange=dict(start=0,duration=1000000),target_timerange=dict(start=500000,duration=1000000))])])
(draft/'draft_content.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
def setvalue(h,v):props[h][b'OfxParamPropDefault']={0:v};return 0
qt[8]=cb(I,[V,S],setvalue)
dll=C.CDLL(str(BUILD/'native-test.dll'));dll.OfxGetPlugin.argtypes=[I];dll.OfxGetPlugin.restype=C.POINTER(Plugin);p=dll.OfxGetPlugin(0).contents
dll.JYTestSetFolder.argtypes=[C.c_wchar_p];dll.JYTestSetFolder.restype=None
hp=new({b'OfxPropName':{0:b'Synthetic native folder host'}});fc=FETCH(fetch);h=Host(hp,fc);p.setHost(C.byref(h));assert p.main(b'OfxActionLoad',None,None,None)==0
assert p.main(b'OfxActionDescribe',effect,None,None)==0
cx=new({b'OfxImageEffectPropContext':{0:b'OfxImageEffectContextFilter'}});assert p.main(b'OfxImageEffectActionDescribeInContext',effect,cx,None)==0
def event(name,user=True):
 changed=new({b'OfxPropName':{0:name},b'OfxPropChangeReason':{0:b'OfxChangeUserEdited' if user else b'OfxChangePluginEdited'}})
 return p.main(b'OfxActionInstanceChanged',effect,changed,None)
def value(key):return props[params[key]][b'OfxParamPropDefault'][0]
for key in [b'source_path',b'output_path']:
 assert props[params[key]][b'OfxParamPropSecret'][0]==0
 assert props[params[key]][b'OfxParamPropPersistant'][0]==1
 assert props[params[key]][b'OfxParamPropStringMode'][0]==b'OfxParamStringIsLabel'
for key in [b'fill_output',b'open_panel']:assert props[params[key]][b'OfxParamPropSecret'][0]==1
assert value(b'output_path')==b'D:/Out'
dll.JYTestSetFolder(str(draft));assert event(b'choose_source',False)==0;assert value(b'source_path')==b''
assert event(b'choose_source')==0;assert value(b'source_path')==str(draft).encode('utf-8')
dll.JYTestSetFolder('');assert event(b'choose_source')==0;assert value(b'source_path')==str(draft).encode('utf-8')
dll.JYTestSetFolder(str(output));assert event(b'choose_output')==0;assert value(b'output_path')==str(output).encode('utf-8')
qt[8]=cb(I,[V,S],lambda h,v:1);dll.JYTestSetFolder(str(work));assert event(b'choose_source')!=0;assert value(b'source_path')==str(draft).encode('utf-8')
qt[8]=cb(I,[V,S],lambda h,v:0);assert event(b'choose_source')!=0,'ignored host writes must not report success'
qt[8]=cb(I,[V,S],setvalue)
jobs=pathlib.Path(os.environ['LOCALAPPDATA'])/'JYMixBridge';before=set(jobs.glob('*/result.json'))
assert event(b'open_panel')==0;assert event(b'export_aaf',False)==0;assert set(jobs.glob('*/result.json'))==before
assert event(b'export_aaf')==0
result=None
for _ in range(250):
 for path in set(jobs.glob('*/result.json'))-before:
  try:result=json.loads(path.read_text(encoding='utf-8'))
  except json.JSONDecodeError:pass
 if result:break
 time.sleep(.1)
assert result and result['ok'],result
aaf=pathlib.Path(result['result']['aaf']);assert aaf.is_file() and output in aaf.parents
assert result['result']['duration_samples']==96000
assert not list(output.rglob('*.wav'))
# Validate production dynamic APIs resolve on this Windows device, without showing UI.
shell=C.WinDLL('shell32.dll');ole=C.WinDLL('ole32.dll')
for name in ['SHBrowseForFolderW','SHGetPathFromIDListW','SHGetPathFromIDListEx']:assert getattr(shell,name)
for name in ['CoInitializeEx','CoUninitialize','CoTaskMemFree']:assert getattr(ole,name)
report=dict(native_selection_to_parameter='pass',chinese_and_spaces='pass',cancel_preserves_path='pass',explicit_and_ignored_write_failures='pass',non_user_actions_do_not_dispatch='pass',native_export_button_to_actual_aaf='pass',native_api_availability='pass',no_bat_cmd_or_panel_dispatch='pass',actual_folder_dialog_clicked=False,real_jianying_save_reopen=False,aaf=str(aaf))
(work/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
