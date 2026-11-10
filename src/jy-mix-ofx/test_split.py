"""One real binary per OFX ID; mock host dispatches actual jobs."""
import pathlib,sys,json,time
name=sys.argv[1];mode=int(sys.argv[2])
root=pathlib.Path(r'D:\Ai-Files\Repos\jy-tools')
script=(root/'src/jy-mix-ofx/test_native_folder.py').read_text(encoding='utf-8').split('for key in [b')[0]
script=script.replace('build/ofx-native-v0.3','build/ofx-split-migration-20261028')
script=script.replace("os.environ['LOCALAPPDATA']=str(work/'appdata')","os.environ['LOCALAPPDATA']=str(work/'appdata');(work/'appdata').mkdir()")
script=script.replace("BUILD/'native-test.dll'",f"BUILD/'{name}-test.dll'")
exec(compile(script,'split-host-fixture','exec'))
def secret(key):return props[params[key]].get(b'OfxParamPropSecret',{0:0})[0]
expected={0:('local.jytools.AAFExport','剪映AAF导出 v0.8',b'export_aaf','aaf'),2:('local.jytools.TrackExport','剪映单集分轨 v0.8',b'export_stems','stems'),3:('local.jytools.BatchTrackExport','剪映多集分轨 v0.8',b'export_batch_stems','batch')}[mode]
assert p.identifier.decode()==expected[0] and p.minor==8
assert props[effect][b'OfxPropLabel'][0].decode()==expected[1]
for key in (b'export_aaf',b'export_stems',b'export_batch_stems'):
 assert secret(key)==(0 if key==expected[2] else 1)
 if key!=expected[2]:assert event(key)!=0,'hidden mode must not dispatch'
assert value(b'last_job')==b''
if mode==3:
 assert secret(b'source_path')==secret(b'choose_source')==1
 assert secret(b'batch_source_path')==0
 assert event(b'toggle_details')==0;assert secret(b'open_report')==1
 import shutil
 library=work/'episodes';library.mkdir()
 for n in ('1','2'):shutil.copytree(draft,library/n)
 dll.JYTestSetFolder(str(library));assert event(b'choose_batch_source')==0
else:
 assert secret(b'batch_source_path')==secret(b'choose_batch_source')==1
 assert secret(b'handles_mode')==(0 if mode==0 else 1)
 dll.JYTestSetFolder(str(draft));assert event(b'choose_source')==0
dll.JYTestSetFolder(str(output));assert event(b'choose_output')==0
assert event(expected[2])==0
jobs=pathlib.Path(os.environ['LOCALAPPDATA'])/'JYMixBridge';target=jobs/value(b'last_job').decode()/'result.json'
for _ in range(400):
 if target.is_file():
  try:result=json.loads(target.read_text(encoding='utf-8'));break
  except json.JSONDecodeError:pass
 time.sleep(.05)
else:raise AssertionError('job timed out')
assert result['ok'],result
if mode==0:assert pathlib.Path(result['result']['aaf']).is_file()
elif mode==2:assert result['result']['mode']=='stems' and len(result['result']['tracks'])==1
else:assert result['result']['mode']=='batch_stems' and result['result']['success']==2
memory=jobs/f'native-paths-{expected[3] if mode!=2 else "tracks"}.ini'
assert memory.is_file(),memory
report=dict(name=expected[1],identifier=expected[0],mode=mode,metadata='pass',dedicated_layout='pass',other_export_modes_rejected='pass',actual_output='pass',independent_memory='pass',result=result['result'],real_editor_ui=False)
(work/'split-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(name=expected[1],id=expected[0],checks='pass',evidence=str(work)),ensure_ascii=True))
