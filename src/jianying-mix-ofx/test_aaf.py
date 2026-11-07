"""Real AAF generation/readback with synthetic sources, never a user's draft."""
import array,hashlib,json,math,pathlib,sys,uuid,wave
import aaf2
import aaf_worker as w
base=w.ROOT/'build/ofx-mix-aaf-v0.1';work=base/('aaf-test-'+uuid.uuid4().hex[:8]);work.mkdir()
source=work/'合成单集';source.mkdir();job=work/'job';job.mkdir()
for channels,name in [(1,'对白'),(2,'音乐')]:
    vals=array.array('h')
    for n in range(144000):
        a=1000 if n<24000 else 2000
        vals.extend([a] if channels==1 else [1000,-2000])
    with wave.open(str(source/(name+'.wav')),'wb') as f:
        f.setparams((channels,2,48000,0,'NONE',''));f.writeframes(vals.tobytes())
def seg(mat,start,offset=0,gain=1):
    return dict(material_id=mat,target_timerange=dict(start=start,duration=1000000),source_timerange=dict(start=offset,duration=1000000),volume=gain)
data=dict(duration=4000000,materials=dict(audios=[dict(id='d',path='对白.wav',material_name='对白'),dict(id='m',path='音乐.wav',material_name='音乐')]),tracks=[dict(type='audio',name='对白',segments=[seg('d',1000000,500000,.5)]),dict(type='audio',name='音乐',segments=[seg('m',0),seg('m',500000)])])
content=source/'draft_content.json';content.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');before=hashlib.sha256(content.read_bytes()).hexdigest()
result=w.export(source,work/'输出',job)
assert result['tracks']==5 and result['clips']==5,result
assert result['duration_samples']==192000
assert content.read_bytes() and hashlib.sha256(content.read_bytes()).hexdigest()==before
with aaf2.open(result['aaf'],'r') as f:
    comp=list(f.content.compositionmobs())[0];slots=list(comp.slots)
    assert [x['SlotName'].value for x in slots]==['对白','音乐·左','音乐·右','音乐·重叠2·左','音乐·重叠2·右']
    assert all(x.segment.length==192000 for x in slots)
    starts=[];values=[]
    for slot in slots:
        cursor=0
        for p in slot.segment.components:
            if type(p).__name__=='SourceClip':
                starts.append(cursor)
                sm=f.content.mobs[p['SourceID'].value]
                out=work/f'回读-{len(values)}.wav';sm.export_audio(str(out))
                with wave.open(str(out),'rb') as wf:
                    assert (wf.getnchannels(),wf.getframerate(),wf.getsampwidth(),wf.getnframes())==(1,48000,3,48000)
                    first=wf.readframes(1);values.append(int.from_bytes(first,'little',signed=True))
            cursor+=p.length
    assert starts==[48000,0,0,24000,24000],starts
    # Gain+source-offset retained for dialog; stereo L/R remains distinct and correctly ordered.
    assert abs(values[0]-256000)<=2,values
    assert values[1:]==[256000,-512000,256000,-512000],values
# Failure checks must not publish a successful .aaf.
broken=json.loads(json.dumps(data));broken['materials']['audios'][0]['path']='缺失.wav'
try: w.plan(broken,source);raise AssertionError('missing source accepted')
except ValueError as e: assert '素材缺失' in str(e)
broken=json.loads(json.dumps(data));broken['tracks'][0]['segments'][0]['source_timerange']['duration']=2000000
try: w.plan(broken,source);raise AssertionError('speed accepted')
except ValueError as e: assert '变速' in str(e)
# Per-draft authority uses the main timeline, rather than stale root content.
t=source/'Timelines';t.mkdir();(t/'project.json').write_text('{"main_timeline_id":"main"}',encoding='utf-8');(t/'main').mkdir();(t/'main/draft_content.json').write_text(json.dumps(data),encoding='utf-8')
_,authority,_=w.load_draft(source,job);assert authority.parent.name=='main'
# Refuse a draft-library root and unsafe output placement.
try:w.load_draft(work,job);raise AssertionError('library root accepted')
except ValueError:pass
try:w.export(source,source/'输出',job);raise AssertionError('nested output accepted')
except ValueError:pass
out=dict(aaf_roundtrip='pass',embedded_audio='pass',stereo_channels='pass',overlap_positions='pass',source_trim_and_gain='pass',four_second_tail='pass',missing_source_rejected='pass',unsupported_speed_rejected='pass',main_timeline_authority='pass',original_unchanged='pass',real_jianying_ui=False,real_daw_import=False,test_root=str(work),aaf=result['aaf'])
(base/'aaf-test-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
