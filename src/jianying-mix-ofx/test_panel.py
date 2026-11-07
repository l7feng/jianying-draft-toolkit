"""Own-window integration tests; no control of Jianying or other user apps."""
from pathlib import Path
import sys,os,json,time,wave,uuid,subprocess,tkinter as tk
from unittest.mock import patch
ROOT=Path(r'D:\Ai-Files\Repos\GitHub\jianying-draft-toolkit');SRC=ROOT/'src/jianying-mix-ofx'
work=ROOT/'build/ofx-path-fix-v0.2'/('panel-test-'+uuid.uuid4().hex[:8]);work.mkdir()
os.environ['LOCALAPPDATA']=str(work/'appdata');sys.path.insert(0,str(SRC))
import aaf_panel as panel
draft=work/'单集 空格';draft.mkdir();output=work/'输出 空格'
with wave.open(str(draft/'对白.wav'),'wb') as f:f.setparams((1,2,48000,0,'NONE',''));f.writeframes(b'\0\0'*48000)
(draft/'draft_content.json').write_text(json.dumps({'duration':2000000,'materials':{'audios':[{'id':'a','path':'对白.wav'}]},'tracks':[{'type':'audio','name':'对白','segments':[{'material_id':'a','source_timerange':{'start':0,'duration':1000000},'target_timerange':{'start':500000,'duration':1000000}}]}]},ensure_ascii=False),encoding='utf-8')
root=tk.Tk();root.withdraw();w=panel.ExportWindow(root)
assert w.output.get()=='D:/Out'
with patch.object(panel.filedialog,'askdirectory',return_value=str(draft)):w.browse(w.source,True)
assert w.source.get()==str(draft)
with patch.object(panel.filedialog,'askdirectory',return_value=''):w.browse(w.source,True)
assert w.source.get()==str(draft)
w.source.set('"'+str(draft)+'"');w.output.set(str(output))
errors=[]
with patch.object(panel.messagebox,'showerror',side_effect=lambda *a,**k:errors.append(a)):
 w.start();process=w.process;assert process is not None
 w.start();assert w.process is process
 assert str(w.start_button['state'])=='disabled'
 deadline=time.time()+35
 while not w.result_path and time.time()<deadline and not errors:root.update();time.sleep(.05)
 assert not errors,errors
 assert w.result_path and w.result_path.is_file(),w.status.get()
 assert '导出完成' in w.status.get();assert str(w.start_button['state'])=='normal'
 result=json.loads((w.job/'result.json').read_text(encoding='utf-8'));assert result['ok']
 assert result['result']['duration_samples']==96000
 with patch.object(panel.os,'startfile') as opened:
  w.open_output();opened.assert_called_once_with(str(w.result_path.parent))
root.destroy()
for source,dest in [('',str(output)),(str(work),str(output)),(str(draft),str(draft/'inside')),('relative',str(output))]:
 try:panel.validate_paths(source,dest)
 except ValueError:pass
 else:raise AssertionError((source,dest))
invalid=subprocess.run([sys.executable,str(SRC/'aaf_worker.py'),'--source',str(draft),'--output',str(output),'--job-id','../escape'],capture_output=True)
assert invalid.returncode!=0
report={'path_edit_and_folder_selection':'pass','cancel_preserves_path':'pass','quoted_chinese_paths':'pass','duplicate_click_guard':'pass','panel_to_worker_to_embedded_aaf':'pass','success_status_and_open_exact_result':'pass','invalid_paths_and_job_id':'pass','real_jianying_ui':False,'sample_aaf':str(w.result_path)}
(work/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
