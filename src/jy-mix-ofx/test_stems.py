import sys,pathlib,tempfile,json,wave,array,hashlib,types
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import aaf_worker as w
import stems_export as s
base=w.ROOT/'build/ofx-mix-aaf-v0.7';root=base/'tests';root.mkdir(exist_ok=True)
work=pathlib.Path(tempfile.mkdtemp(prefix='stems-',dir=root));draft=work/'单集';draft.mkdir()
def pcm(path,channels,values):
    data=array.array('h')
    for _ in range(48000):data.extend(values)
    with wave.open(str(path),'wb') as f:f.setparams((channels,2,48000,0,'NONE',''));f.writeframes(data.tobytes())
pcm(draft/'mono.wav',1,[1000]);pcm(draft/'stereo.wav',2,[1200,-1600])
def seg(mat,start,duration=500000,gain=1):return dict(material_id=mat,volume=gain,target_timerange=dict(start=start,duration=duration),source_timerange=dict(start=0,duration=duration))
data=dict(duration=2000000,materials=dict(audios=[dict(id='a',path='mono.wav'),dict(id='b',path='stereo.wav')]),tracks=[dict(type='audio',name='对白',is_muted=True,segments=[seg('a',500000,gain=.5),seg('a',750000,gain=.5)]),dict(type='audio',name='音乐',segments=[seg('b',0)])])
(draft/'draft_content.json').write_text(json.dumps(data),encoding='utf-8');before=hashlib.sha256((draft/'draft_content.json').read_bytes()).hexdigest()
job=work/'job';job.mkdir();result=s.export(w,draft,work/'output',job)
assert len(result['tracks'])==2 and result['duration_samples']==96000
assert result['risks'] and result['source_unchanged']
def read(track):
    with wave.open(str(pathlib.Path(result['output'])/track['file'])) as f:
        assert f.getnframes()==96000 and f.getframerate()==48000 and f.getsampwidth()==3
        raw=f.readframes(96000);ch=f.getnchannels()
        return ch,[int.from_bytes(raw[i:i+3],'little',signed=True) for i in range(0,len(raw),3)]
ch,mono=read(result['tracks'][0]);assert ch==1
assert mono[1000]==0 and abs(mono[30000]-128000)<10 and abs(mono[40000]-256000)<10 and mono[-1]==0
ch,stereo=read(result['tracks'][1]);assert ch==2 and stereo[2000]>0 and stereo[2001]<0 and stereo[-1]==0
assert hashlib.sha256((draft/'draft_content.json').read_bytes()).hexdigest()==before
# More than 16 clips exercises chunk mixing and recursive reduction.
tmp=work/'mix';tmp.mkdir();path=draft/'mono.wav'
dense=s.mix_channel(w,[(path,0)]*17,48000,tmp,'dense')
assert dense.is_file()
# Mixed channel counts promote the original track to stereo.
data['tracks']=[dict(type='audio',name='混合',segments=[seg('a',0),seg('b',500000)])]
(draft/'draft_content.json').write_text(json.dumps(data),encoding='utf-8');j=work/'mixed';j.mkdir();mixed=s.export(w,draft,work/'output',j)
assert mixed['tracks'][0]['channels']==2
# Parent discovery only, one failure does not suppress successful siblings.
library=work/'library';library.mkdir()
import shutil
for name in ('2','10'):shutil.copytree(draft,library/name)
bad=library/'3';bad.mkdir();(bad/'draft_content.json').write_text('{broken',encoding='utf-8')
(library/'not-project').mkdir();bj=work/'batch';bj.mkdir();batch=s.batch(w,library,work/'batch-output',bj)
assert (batch['success'],batch['failed'],batch['total'])==(2,1,3),batch
assert [x['project'] for x in batch['episodes']]==['2','3','10']
assert batch['skipped']==['not-project']
assert (pathlib.Path(batch['output'])/'批量汇总.json').is_file()
report=dict(time_alignment='pass',silence_tail='pass',stereo_polarity='pass',overlap_and_gain='pass',mixed_channels='pass',bounded_dense_mixing='pass',risks_preserved='pass',source_unchanged='pass',batch_failure_continues='pass',natural_episode_order='pass',root=str(work),real_editor_ui=False)
(work/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True,indent=2))
