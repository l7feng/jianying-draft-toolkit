from pathlib import Path
import json
root=Path(r'D:\Ai-Files\Repos\jy-tools')
script=(root/'src/jy-mix-ofx/test_native_folder.py').read_text(encoding='utf-8')
script=script.replace("BUILD=ROOT/'build/ofx-native-v0.3'","BUILD=ROOT/'build/ofx-memory-v0.4'")
script=script.replace("os.environ['LOCALAPPDATA']=str(work/'appdata')", "os.environ['LOCALAPPDATA']=str(work/'appdata');(work/'appdata').mkdir()")
# Reuse native selection and actual AAF dispatch checks, then add memory/preflight tests.
namespace={};exec(compile(script,'native-memory-regression','exec'),namespace)
g=namespace;dll=g['dll'];event=g['event'];props=g['props'];params=g['params'];value=g['value'];C=g['C'];work=g['work'];effect=g['effect'];p=g['p'];cx=g['cx'];draft=g['draft'];output=g['output'];jobs=g['jobs'];time=g['time'];qt=g['qt'];cb=g['cb'];I=g['I'];V=g['V'];S=g['S'];setvalue=g['setvalue']
memory=jobs/'native-paths.ini';assert memory.is_file();content=memory.read_text(encoding='utf-16');assert str(draft) in content and str(output) in content
before=memory.read_bytes();dll.JYTestSetFolder('');assert event(b'choose_output')==0;assert memory.read_bytes()==before
# Fresh parameter descriptors restore the device's last selected folders.
assert p.main(b'OfxImageEffectActionDescribeInContext',effect,cx,None)==0
assert value(b'source_path')==str(draft).encode('utf-8');assert value(b'output_path')==str(output).encode('utf-8')
other=work/'another-existing-project';other.mkdir()
setvalue(params[b'source_path'],str(other).encode());setvalue(params[b'output_path'],str(other).encode())
assert p.main(b'OfxActionCreateInstance',effect,None,None)==0
assert value(b'source_path')==str(other).encode(),'must not overwrite a saved project value'
assert event(b'restore_paths')==0;assert value(b'source_path')==str(draft).encode()
# A failed host write must never modify device memory.
qt[8]=cb(I,[V,S],lambda h,v:1);dll.JYTestSetFolder(str(other));assert event(b'choose_source')!=0;assert memory.read_bytes()==before
qt[8]=cb(I,[V,S],setvalue)
dll.JYTestInitial.argtypes=[S,S,C.c_char_p,I];buf=C.create_string_buffer(32768)
dll.JYTestInitial(str(draft/'missing'/'deeper').encode(),b'source_path',buf,len(buf));assert Path(buf.value.decode()).resolve()==draft.resolve()
# Preflight launches from the native button, creates a report and no AAF.
assert event(b'inspect_project')==0
job_id=value(b'last_job').decode();job=jobs/job_id;result=None
for _ in range(200):
 try:result=json.loads((job/'result.json').read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError):pass
 if result:break
 time.sleep(.1)
assert result and result['ok'],result
assert result['result']['can_export'];assert Path(result['result']['report']).is_file();assert not list(job.rglob('*.aaf'))
for _ in range(50):
 if (job/'任务结果.txt').exists():break
 time.sleep(.02)
assert event(b'refresh_status')==0;assert value(b'task_status').decode()=='检查完成',repr(value(b'task_status'))
report=json.loads((job/'工程检查报告.json').read_text(encoding='utf-8'));assert report['project']==draft.name;assert report['duration_seconds']==2;assert report['handles_seconds']==0;assert report['start_timecode'].startswith('未知')
# All missing sources are collected instead of silently dropping clips.
import sys
sys.path.insert(0,str(root/'src/jy-mix-ofx'))
import aaf_worker as worker,aaf_inspection
missing_job=work/'missing-check';missing_job.mkdir()
data={'duration':2000000,'materials':{'audios':[{'id':'x','path':'missing-a.wav'},{'id':'y','path':'missing-b.wav'}]},'tracks':[{'type':'audio','segments':[{'material_id':'x'},{'material_id':'y'}]}]}
summary,path,*_=aaf_inspection.inspect(worker,data,draft,draft/'draft_content.json','test',missing_job)
assert not summary['can_export'];assert 'missing-a.wav' in path.read_text(encoding='utf-8') and 'missing-b.wav' in path.read_text(encoding='utf-8')
assert not list(output.rglob('*.cmd'))
result={'memory_after_selection':'pass','cancel_does_not_change_memory':'pass','fresh_instance_restores_both_paths':'pass','existing_project_paths_take_priority':'pass','explicit_restore':'pass','failed_write_does_not_save_memory':'pass','missing_chooser_path_uses_existing_parent':'pass','native_inspection_button_and_status':'pass','report_collects_all_missing_materials':'pass','no_audio_render_during_inspection':'pass','real_jianying_memory_reopen':False}
(work/'memory-inspection-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
