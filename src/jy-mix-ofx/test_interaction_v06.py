from pathlib import Path
r=Path(r'D:\Ai-Files\Repos\jy-tools')
s=(r/'src/jy-mix-ofx/test_native_folder.py').read_text(encoding='utf-8')
s=s.replace('build/ofx-native-v0.3','build/ofx-mix-aaf-v0.6')
s=s.replace("os.environ['LOCALAPPDATA']=str(work/'appdata')","os.environ['LOCALAPPDATA']=str(work/'appdata');(work/'appdata').mkdir()")
s=s.replace("assert event(b'export_aaf')==0\nresult=None", """assert props[params[b'task_status']][b'OfxParamPropSecret'][0]==1
assert event(b'toggle_details')==0
assert props[params[b'task_status']][b'OfxParamPropSecret'][0]==0
assert event(b'toggle_details')==0
assert props[params[b'task_status']][b'OfxParamPropSecret'][0]==1
assert event(b'export_aaf')==0
assert props[params[b'task_status']][b'OfxParamPropSecret'][0]==0
job=value(b'last_job')
assert event(b'export_aaf')==0
assert value(b'last_job')==job,'duplicate click launched a second job'
result=None""")
s=s.replace("report=dict(","report=dict(details_toggle='pass',dispatch_expands_status='pass',duplicate_dispatch_guard='pass',")
exec(compile(s,'native-v06-regression','exec'))
assert event(b'refresh_status')==0
assert '导出完成' in value(b'task_status').decode()
last=value(b'last_job')
setvalue(params[b'last_job'],b'20000101-000000-00000000')
assert event(b'refresh_status')==0
assert '无法确认' in value(b'task_status').decode()
assert event(b'open_report')==0
assert '尚未生成' in value(b'task_status').decode()
setvalue(params[b'last_job'],last)
# Preserve the result as evidence while simulating a missing status file.
status=jobs/last.decode()/'任务结果.txt'
saved=status.with_name('任务结果测试保留.txt');status.rename(saved)
try:
    for _ in range(50):
        event(b'refresh_status')
        if '后台已结束' in value(b'task_status').decode():break
        time.sleep(.1)
    assert '后台已结束' in value(b'task_status').decode()
finally:saved.rename(status)
event(b'toggle_details');event(b'toggle_details')
assert '导出完成' in value(b'task_status').decode()
(work/'feedback-results.json').write_text(json.dumps(dict(missing_report='pass',unknown_job='pass',exited_without_result='pass',expand_refresh='pass'),indent=2),encoding='utf-8')
print('feedback regressions passed',work)
