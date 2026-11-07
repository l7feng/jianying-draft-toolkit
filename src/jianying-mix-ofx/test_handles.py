import pathlib,sys,json,wave,array,uuid
ROOT=pathlib.Path(r'D:\Ai-Files\Repos\GitHub\jianying-draft-toolkit');sys.path.insert(0,str(ROOT/'src/jianying-mix-ofx'))
import aaf_worker as w,aaf2
work=ROOT/'build/ofx-layout-v0.5'/('handles-'+uuid.uuid4().hex[:8]);work.mkdir();draft=work/'合成草稿';draft.mkdir()
with wave.open(str(draft/'声音.wav'),'wb') as f:f.setparams((1,2,48000,0,'NONE',''));f.writeframes(array.array('h',[2000]*480000).tobytes())
data={'duration':5000000,'materials':{'audios':[{'id':'a','path':'声音.wav'}],'audio_fades':[{'id':'fade','fade_in_duration':500000,'fade_out_duration':500000}]},'tracks':[{'type':'audio','name':'对白','segments':[{'material_id':'a','source_timerange':{'start':3000000,'duration':2000000},'target_timerange':{'start':1000000,'duration':2000000},'volume':.5,'extra_material_refs':['fade']}]}]}
(draft/'draft_content.json').write_text(json.dumps(data),encoding='utf-8')
job=work/'job';job.mkdir();result=w.export(draft,work/'输出',job,2)
assert result['handles_seconds']==2
with aaf2.open(result['aaf'],'r') as f:
 slot=list(list(f.content.compositionmobs())[0].slots)[0];assert slot.segment.length==240000
 parts=list(slot.segment.components);assert parts[0].length==48000
 clip=parts[1];assert clip['StartTime'].value==96000;assert clip.length==96000
 mob=f.content.mobs[clip['SourceID'].value];wav=work/'回读.wav';mob.export_audio(str(wav))
with wave.open(str(wav),'rb') as f:
 assert f.getnframes()==288000
 def value(n):f.setpos(n);return int.from_bytes(f.readframes(1),'little',signed=True)
 assert abs(value(48000)-256000)<5,'pre-handle must retain audio'
 assert abs(value(96000))<500,'original clip fade-in must start at edit point'
 assert abs(value(144000)-256000)<5
 assert abs(value(191990))<500,'fade-out must still reach original end'
 assert abs(value(240000)-256000)<5,'post-handle must retain audio'
# Bounds clamp without moving the edit or changing its timeline duration.
data['tracks'][0]['segments'][0]['source_timerange']['start']=0
(draft/'draft_content.json').write_text(json.dumps(data),encoding='utf-8');job2=work/'job2';job2.mkdir();r=w.export(draft,work/'输出2',job2,5)
assert r['manifest'][0]['handle_before_samples']==0 and r['manifest'][0]['handle_after_samples']==240000
report={'embedded_handles':'pass','edit_point_and_duration_preserved':'pass','gain_and_original_fades':'pass','handles_outside_fades_audible':'pass','source_boundary_clamping':'pass','real_daw_handles_import':False}
(work/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));print(work)
