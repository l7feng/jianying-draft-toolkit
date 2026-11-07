"""Regression tests for source origin, mixed channel counts, silent tail and sample rounding."""
import array,json,os,pathlib,subprocess,sys,time,uuid,wave
from unittest.mock import patch
import aaf2
import aaf_worker as w
base=w.ROOT/'build/ofx-mix-aaf-v0.1';work=base/('edge-test-'+uuid.uuid4().hex[:8]);work.mkdir();src=work/'单集';src.mkdir()
for ch,name in [(1,'mono'),(2,'stereo')]:
    buf=array.array('h',[1000] if ch==1 else [1000,-2000])*48000
    with wave.open(str(src/(name+'.wav')),'wb') as f:f.setparams((ch,2,48000,0,'NONE',''));f.writeframes(buf.tobytes())
w.run_command(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=size=16x16:rate=1:color=black','-t','5','-an','-c:v','mpeg4',src/'silent.mp4'])
base_data=dict(materials=dict(audios=[dict(id='mono',path='mono.wav'),dict(id='stereo',path='stereo.wav')],videos=[dict(id='video',path='silent.mp4')]),tracks=[dict(type='audio',name='混合',segments=[dict(material_id='stereo',target_timerange=dict(start=0,duration=1000000),source_timerange=dict(start=0,duration=1000000)),dict(material_id='mono',target_timerange=dict(start=2000000,duration=1000000))]),dict(type='video',segments=[dict(material_id='video',target_timerange=dict(start=0,duration=5000000),source_timerange=dict(start=0,duration=5000000))])])
content=src/'draft_content.json';content.write_text(json.dumps(base_data),encoding='utf-8');job=work/'mixed';job.mkdir();r=w.export(src,work/'out',job)
assert r['tracks']==3 and r['duration_samples']==240000,r
assert [m['start_samples'] for m in r['manifest']]==[0,0,96000]
assert any(m['track']=='混合·单声道' for m in r['manifest']),r
with aaf2.open(r['aaf'],'r') as f:
    comp=list(f.content.compositionmobs())[0]
    slot=next(s for s in comp.slots if s['SlotName'].value=='混合·单声道')
    clip=next(p for p in slot.segment.components if type(p).__name__=='SourceClip')
    file=work/'mono-readback.wav';f.content.mobs[clip['SourceID'].value].export_audio(str(file))
    with wave.open(str(file),'rb') as wf:assert int.from_bytes(wf.readframes(1),'little',signed=True)==256000
# Adjacent non-integral sample durations must not create an overlap track or drift.
data=dict(materials=base_data['materials'],tracks=[dict(type='audio',name='相邻',segments=[dict(material_id='mono',target_timerange=dict(start=i*1011,duration=1011),source_timerange=dict(start=0,duration=1011)) for i in range(3)])])
content.write_text(json.dumps(data),encoding='utf-8');job=work/'rounding';job.mkdir();r=w.export(src,work/'out',job)
assert r['tracks']==1 and [m['start_samples'] for m in r['manifest']]==[0,49,97],r
assert [m['length_samples'] for m in r['manifest']]==[49,48,49],r
assert r['duration_samples']==146
# Real Windows lock held by another process must produce a useful failure, not start an export.
fake=work/'profile';lockdir=fake/'JYMixBridge';lockdir.mkdir(parents=True);ready=work/'ready'
childcode="import pathlib,msvcrt,sys;f=open(sys.argv[1],'a+b');f.write(b'0');f.flush();f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);pathlib.Path(sys.argv[2]).write_text('ready');sys.stdin.readline()"
child=subprocess.Popen([sys.executable,'-c',childcode,str(lockdir/'worker.lock'),str(ready)],stdin=subprocess.PIPE,creationflags=0x08000000)
try:
    for _ in range(50):
        if ready.exists():break
        time.sleep(.05)
    assert ready.exists()
    with patch.dict(os.environ,{'LOCALAPPDATA':str(fake)}):code=w.run(['--source',str(src),'--output',str(work/'blocked')])
    assert code==1
    result=json.loads(next(lockdir.glob('*/result.json')).read_text(encoding='utf-8'));assert '已有AAF任务' in result['error'],result
finally:child.communicate(b'\n',timeout=10)
result=dict(missing_source_range_starts_at_zero='pass',mono_stereo_separated_correctly='pass',silent_video_tail='pass',sample_endpoint_rounding='pass',no_false_overlap_lane='pass',component_sum_validation='pass',real_process_lock_feedback='pass',real_jianying_audio_export=False,real_daw_import=False,test_root=str(work))
(base/'aaf-edge-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
