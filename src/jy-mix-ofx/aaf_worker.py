"""Single saved Jianying draft -> embedded, editable audio AAF. Project 72."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, math, os, pathlib, re, shutil, subprocess, sys, time, uuid, wave
ROOT=pathlib.Path(__file__).resolve().parents[2]
CODE=ROOT/'src/jy-tools/code'
SR=48000
FLAGS={'creationflags':0x08000000} if os.name=='nt' else {}

def media_tool(name):
    config=pathlib.Path(__file__).with_name('media-tools.local.json')
    configured=json.loads(config.read_text(encoding='utf-8-sig')).get(name) if config.is_file() else None
    if configured and pathlib.Path(configured).is_absolute() and pathlib.Path(configured).is_file():return configured
    found=shutil.which(name)
    if found:return found
    raise ValueError('缺少音频工具 '+name+'，请修复media-tools.local.json中的绝对路径。')

def run_command(args, timeout=600):
    args=list(args)
    if str(args[0]) in ('ffmpeg','ffprobe'):args[0]=media_tool(str(args[0]))
    p=subprocess.run([str(a) for a in args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,**FLAGS)
    if p.returncode: raise RuntimeError('音频转换或草稿读取失败：'+p.stderr[-1500:]+p.stdout[-300:])
    return p.stdout

def samples(us): return int(round(int(us)*SR/1000000))
def safe(name): return re.sub(r'[\\/:*?"<>|]', '_', name).strip(' .')[:100] or '未命名草稿'

def configured_runtime(config=None):
    config=pathlib.Path(config) if config is not None else pathlib.Path(__file__).with_name('runtime.local.json')
    if not config.is_file():return None
    data=json.loads(config.read_text(encoding='utf-8-sig'))
    runtime=pathlib.Path(data['runtime_dir'])
    if not runtime.is_absolute():raise ValueError('草稿读取运行时路径必须为绝对路径。')
    for name,key in [('videoeditor.dll','engine_sha256'),('jy-draftc.exe','converter_sha256')]:
        p=runtime/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=data[key]:
            raise ValueError('已验证的草稿读取运行环境缺失或发生变化，请先重新核对：'+name)
    return runtime

class DraftReadError(RuntimeError):
    def __init__(self,message,diagnostic):
        super().__init__(message)
        self.diagnostic=diagnostic
        self.code='DRAFT_READ_FAILED'

def load_draft(source, job):
    if str(CODE) not in sys.path: sys.path.insert(0,str(CODE))
    import import_audio as imp
    if not source.is_dir(): raise ValueError('草稿目录不存在，请填写单集草稿文件夹。')
    authority,_,_=imp.resolve_content_files(source)
    if authority is None: raise ValueError('此处不是单集草稿：请进入具体工程文件夹，不要选择整个草稿库。')
    raw=authority.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    snapshot_dir=job/'草稿副本';snapshot_dir.mkdir(exist_ok=True)
    snapshot=snapshot_dir/authority.name;snapshot.write_bytes(raw)
    try: data=json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError,json.JSONDecodeError):
        if raw.lstrip().startswith((b'{',b'[')):
            raise ValueError('草稿JSON结构损坏，请先在剪映中确认工程可正常打开。')
        # Work only on a snapshot and a private converter copy; leave source and EXE settings untouched.
        install=configured_runtime() or imp._jianying_install_dir()
        if not install or not (install/'videoeditor.dll').is_file(): raise ValueError('找不到可用的剪映安装目录。')
        tools=job/'converter';tools.mkdir()
        converter_source=install/'jy-draftc.exe' if (install/'jy-draftc.exe').is_file() else imp.DEFAULT_DRAFTC
        if not converter_source.is_file():raise ValueError('草稿已加密，缺少已验证的草稿转换器。')
        converter=tools/'jy-draftc.exe';shutil.copy2(converter_source,converter)
        (tools/'.env').write_text('JY_INSTALL_DIR='+str(install),encoding='utf-8')
        env=os.environ.copy();env['JY_INSTALL_DIR']=str(install)
        p=subprocess.run([str(converter),'-d',str(snapshot)],cwd=tools,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,**FLAGS)
        decoded=snapshot.with_suffix(snapshot.suffix+'.dec.json')
        valid=False;data=None
        if decoded.is_file() and decoded.stat().st_size:
            try:
                data=json.loads(decoded.read_text(encoding='utf-8-sig'));valid=isinstance(data,dict)
            except (UnicodeError,json.JSONDecodeError):pass
        diagnostic=dict(phase='读取加密草稿',runtime_version=install.name,source_bytes=len(raw),
                        return_code=p.returncode,decoded_bytes=decoded.stat().st_size if decoded.exists() else 0,
                        decoded_json_valid=valid,source_matches_snapshot=hashlib.sha256(authority.read_bytes()).hexdigest()==digest,
                        converter_output=(p.stdout+p.stderr)[-2000:])
        diagnostic_path=job/'读取诊断.json'
        diagnostic_path.write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2),encoding='utf-8')
        if p.returncode or not valid:
            raise DraftReadError(f'草稿读取未通过：转换器无法还原此草稿（剪映{install.name}）。本任务未写回原工程，未生成AAF。详情见任务目录中的读取诊断.json。',str(diagnostic_path))
    if not isinstance(data,dict): raise ValueError('草稿结构不是可识别的工程对象。')
    return data,authority,digest

def source_file(text, source):
    p=pathlib.Path(text)
    if p.is_absolute() and p.is_file(): return p
    if not p.is_absolute() and (source/p).is_file(): return (source/p).resolve()
    hits=[x for x in source.rglob(p.name) if x.is_file()] if p.name else []
    # Archiving inside the original media folder must not make an otherwise unchanged draft unusable.
    if p.is_absolute() and p.parent.is_dir() and p.parent!=p.anchor and len(p.parent.parts)>2:
        hits += [x for x in p.parent.rglob(p.name) if x.is_file()]
    hits=list({x.resolve() for x in hits})
    if len(hits)==1: return hits[0].resolve()
    if len(hits)>1: raise ValueError('素材路径有多个同名候选，无法确定：'+text)
    raise ValueError('素材缺失：'+text)

def probe(path):
    d=json.loads(run_command(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=channels,duration:format=duration','-of','json',path],60))
    streams=d.get('streams',[])
    if not streams: return 0,0
    ch=int(streams[0]['channels'])
    duration=streams[0].get('duration') or d.get('format',{}).get('duration')
    return ch,float(duration) if duration and duration!='N/A' else None

def plan(data,source):
    materials={m['id']:m for cat in ('audios','videos') for m in data.get('materials',{}).get(cat,[]) if 'id' in m}
    fades={m['id']:m for m in data.get('materials',{}).get('audio_fades',[]) if 'id' in m}
    tracks=[];warnings=['本文件是素材剪辑交接AAF，仅烘焙固定片段音量和线性淡入淡出；不包含剪映降噪、变声、插件音效、非线性淡化曲线、关键帧自动化、轨道静音及独奏状态。']
    info={};total=int(data.get('duration',0) or 0)
    # Silent video and text can extend the project past the last audible clip.
    for t in data.get('tracks',[]):
        for segment in t.get('segments',[]):
            timerange=segment.get('target_timerange') or {}
            total=max(total,int(timerange.get('start',0))+int(timerange.get('duration',0)))
    for ti,t in enumerate(data.get('tracks',[]),1):
        if t.get('type') not in ('audio','video'): continue
        clips=[]
        for si,s in enumerate(t.get('segments',[]),1):
            m=materials.get(s.get('material_id'))
            if not m or not m.get('path'): raise ValueError(f'第{ti}轨第{si}段缺少素材路径。')
            path=source_file(m['path'],source)
            if pathlib.Path(m['path']).is_absolute() and path.resolve()!=pathlib.Path(m['path']).resolve():
                warnings.append('素材位置已变化，使用原媒体目录内唯一同名文件：'+str(path))
            if path not in info: info[path]=probe(path)
            ch,media_duration=info[path]
            if not ch:
                if t['type']=='video': warnings.append(f'视频无音轨，已略过：{path.name}');continue
                raise ValueError('音频素材没有可读取的音轨：'+str(path))
            if ch>8: raise ValueError('暂不支持超过八声道的素材：'+str(path))
            target=s.get('target_timerange') or {}
            start=int(target.get('start',0));dur=int(target.get('duration',0))
            if not s.get('source_timerange'):warnings.append(f'第{ti}轨第{si}段缺少取材范围，按素材起点导出，请核对。')
            origin=s.get('source_timerange') or {'start':0,'duration':dur}
            offset=int(origin.get('start',0));srcdur=int(origin.get('duration',dur))
            length=samples(start+dur)-samples(start)
            if length<=0:raise ValueError(f'第{ti}轨第{si}段不足一个采样点，无法导出。')
            if start<0 or offset<0 or dur<=0: raise ValueError(f'第{ti}轨第{si}段时间范围无效。')
            if abs(srcdur-dur)>22 or s.get('reverse') or s.get('is_reverse'): raise ValueError(f'第{ti}轨第{si}段包含变速或倒放，请先在剪映烘焙为普通音频后替换。')
            if media_duration is not None and (offset+srcdur)/1e6>media_duration+0.002: raise ValueError('片段取材超出源文件时长：'+str(path))
            gain=float(s.get('volume',1));
            if not math.isfinite(gain) or gain<0: raise ValueError('片段音量无效。')
            fade_in=fade_out=0
            for ref in s.get('extra_material_refs',[]):
                f=fades.get(ref)
                if f:
                    fade_in=max(fade_in,int(f.get('fade_in_duration',0)));fade_out=max(fade_out,int(f.get('fade_out_duration',0)))
            clips.append(dict(path=path,name=m.get('material_name') or path.stem,start=samples(start),length=length,offset=offset,channels=ch,gain=gain,media_duration=media_duration,fade_in=min(fade_in,dur),fade_out=min(fade_out,dur)))
            total=max(total,start+dur)
        if clips: tracks.append(dict(name=t.get('name') or f'轨道{ti}',clips=sorted(clips,key=lambda x:x['start'])))
    if not tracks: raise ValueError('草稿中没有可导出的音频片段。')
    return tracks,samples(total),warnings

def audio_filter(clip,channel,before,after):
    length=before+clip['length']+after
    base=f"pan=mono|c0=c{channel},volume={clip['gain']:.12g},aresample={SR},atrim=end_sample={length},asetpts=PTS-STARTPTS"
    fades=[]
    if clip['fade_in']:fades.append(f"afade=t=in:st=0:d={clip['fade_in']/1e6:.9f}")
    if clip['fade_out']:fades.append(f"afade=t=out:st={clip['length']/SR-clip['fade_out']/1e6:.9f}:d={clip['fade_out']/1e6:.9f}")
    if not fades:return base
    if not before and not after:return base+','+','.join(fades)
    # Split on exact PCM sample boundaries. Timeline enable is frame-granular
    # and can otherwise leave the first samples of a fade at full gain.
    ranges=[]
    if before:ranges.append((0,before,False))
    ranges.append((before,before+clip['length'],True))
    if after:ranges.append((before+clip['length'],length,False))
    count=len(ranges);graph=base+f',asplit={count}'+''.join(f'[in{i}]' for i in range(count))
    for i,(start,end,center) in enumerate(ranges):
        graph+=f';[in{i}]atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS'
        if center:graph+=','+','.join(fades)
        graph+=f'[out{i}]'
    graph+=';'+''.join(f'[out{i}]' for i in range(count))+f'concat=n={count}:v=0:a=1,atrim=end_sample={length},asetpts=PTS-STARTPTS'
    return graph

def normalize_pcm_tail(wav,expected):
    with wave.open(str(wav),'rb') as src:
        if (src.getnchannels(),src.getframerate(),src.getsampwidth())!=(1,SR,3):raise RuntimeError('转换音频规格不匹配：'+str(wav))
        missing=expected-src.getnframes()
        if missing==0:return 0
        if missing<0 or missing>int(SR*.020):raise RuntimeError(f'转换音频长度不匹配：期望{expected}，实际{src.getnframes()}采样；缺口超过20毫秒或音频过长。')
        temp=wav.with_suffix('.pad.wav')
        with wave.open(str(temp),'wb') as dst:
            dst.setparams(src.getparams())
            while True:
                block=src.readframes(65536)
                if not block:break
                dst.writeframesraw(block)
            dst.writeframesraw(bytes(missing*3))
    temp.replace(wav)
    return missing

def write_aaf(tracks,total,title,output,work,handles_seconds=0):
    import aaf2
    manifest=[]
    with aaf2.open(str(output),'w') as f:
        comp=f.create.CompositionMob();comp.name=title;f.content.mobs.append(comp)
        sound=f.dictionary.lookup_datadef('Sound');slot_id=0
        for track in tracks:
            # Preserve simultaneous clips with extra lanes, rather than serializing overlaps.
            lanes=[]
            for clip in track['clips']:
                lane=next((x for x in lanes if x[0]['channels']==clip['channels'] and x[-1]['start']+x[-1]['length']<=clip['start']),None)
                if lane is None: lane=[];lanes.append(lane)
                lane.append(clip)
            mixed=len({c['channels'] for c in track['clips']})>1
            for li,lane in enumerate(lanes):
                channels=lane[0]['channels']
                overlap_index=sum(1 for previous in lanes[:li] if previous[0]['channels']==channels)
                for channel in range(channels):
                    slot_id+=1;name=track['name']
                    if mixed:name+=('·单声道' if channels==1 else '·立体声' if channels==2 else f'·{channels}声道')
                    if overlap_index:name+=f'·重叠{overlap_index+1}'
                    if channels>1: name+=('·左','·右')[channel] if channel<2 else f'·声道{channel+1}'
                    slot=comp.create_timeline_slot(SR,slot_id=slot_id);slot['SlotName'].value=name
                    seq=f.create.Sequence();seq['DataDefinition'].value=sound;parts=[];cursor=0
                    def filler(n):
                        if n>0:
                            p=f.create.Filler();p['DataDefinition'].value=sound;p['Length'].value=n;parts.append(p)
                    for clip in lane:
                        if channel>=clip['channels']: continue
                        wav=work/f'{slot_id}-{len(manifest)}.wav'
                        requested=int(handles_seconds*SR)
                        before=min(requested,int(clip['offset']*SR//1000000))
                        available=clip.get('media_duration')
                        after=min(requested,max(0,int((available-clip['offset']/1e6)*SR)-clip['length'])) if available is not None else 0
                        essence_length=before+clip['length']+after
                        decode_start=clip['offset']/1e6-before/SR
                        filters=audio_filter(clip,channel,before,after)
                        print(f'正在转换：{name}，片段{len(manifest)+1}，声道{channel+1}',flush=True)
                        run_command(['ffmpeg','-y','-v','error','-ss',f'{decode_start:.9f}','-i',clip['path'],'-map','0:a:0','-t',f'{essence_length/SR:.9f}','-af',filters,'-ar',SR,'-ac',1,'-c:a','pcm_s24le',wav])
                        padded=normalize_pcm_tail(wav,essence_length)
                        sm=f.create.SourceMob();sm.name=clip['name'];f.content.mobs.append(sm);sm.import_audio_essence(str(wav),edit_rate=SR)
                        filler(clip['start']-cursor)
                        part=f.create.SourceClip();part['DataDefinition'].value=sound;part['StartTime'].value=before;part['Length'].value=clip['length'];part['SourceID'].value=sm.mob_id;part['SourceMobSlotID'].value=1;parts.append(part)
                        cursor=clip['start']+clip['length'];manifest.append(dict(track=name,start_samples=clip['start'],length_samples=clip['length'],source=str(clip['path']),source_channel=channel+1,handle_before_samples=before,handle_after_samples=after,essence_samples=essence_length,tail_padding_samples=padded))
                    filler(total-cursor);seq['Components'].value=parts;seq['Length'].value=total;slot['Segment'].value=seq
    # Read back embedded media and timeline lengths before publishing success.
    with aaf2.open(str(output),'r') as f:
        compositions=list(f.content.compositionmobs())
        if len(compositions)!=1 or len(list(compositions[0].slots))!=slot_id: raise RuntimeError('AAF回读轨道核验失败。')
        if any(s.segment.length!=total or sum(p.length for p in s.segment.components)!=total for s in compositions[0].slots): raise RuntimeError('AAF回读总长度或片段累计长度核验失败。')
        if len(list(f.content.essencedata))!=len(manifest): raise RuntimeError('AAF内嵌音频数量核验失败。')
    return manifest,slot_id

def export(source,output,job,handles_seconds=0):
    if handles_seconds not in (0,2,5):raise ValueError('片段余量只支持0、2或5秒。')
    source=source.resolve();output=output.resolve()
    if source==output or source in output.parents: raise ValueError('输出目录必须位于源草稿目录之外。')
    media_tool('ffmpeg');media_tool('ffprobe')
    print('正在只读解析草稿…',flush=True)
    data,authority,digest=load_draft(source,job)
    from aaf_inspection import inspect
    report,report_path,tracks,total,warnings=inspect(sys.modules[__name__],data,source,authority,digest,job,handles_seconds)
    if report['issues']:raise ValueError('工程检查未通过，请查看工程检查报告：'+report['issues'][0])
    print(f'识别到{len(tracks)}条原始音频轨，开始生成AAF内嵌媒体。',flush=True)
    output.mkdir(parents=True,exist_ok=True)
    dest=output/(safe(source.name)+'-'+job.name);dest.mkdir()
    work=job/'音频中间文件';work.mkdir();pending=dest/(safe(source.name)+'.未完成.aaf')
    manifest,count=write_aaf(tracks,total,source.name,pending,work,handles_seconds)
    if hashlib.sha256(authority.read_bytes()).hexdigest()!=digest: raise RuntimeError('导出期间源草稿发生变化，请保存后重新导出。本次文件保留为未完成。')
    final=dest/(safe(source.name)+'.aaf');pending.rename(final)
    padded=[x for x in manifest if x.get('tail_padding_samples')]
    if padded:warnings=warnings+[f'有{len(padded)}份单声道片段的源音频短尾补静音（每份不超过20毫秒），具体采样数见交接清单。']
    result=dict(aaf=str(final),handles_seconds=handles_seconds,tracks=count,clips=len(manifest),sample_rate=SR,bit_depth=24,duration_samples=total,warnings=warnings,risks=report['risks'],project=source.name,source=str(source),source_unchanged=True,manifest=manifest)
    (dest/'交接清单.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'交接说明.txt').write_text('AAF导出完成\n'+str(final)+'\n'+f'轨道：{count}；音频片段声道：{len(manifest)}；48千赫兹，24位。\n片段前后余量：各{handles_seconds}秒（受源素材边界限制）。\n'+'\n'.join(report['risks']+warnings),encoding='utf-8')
    shutil.copy2(report_path,dest/'工程检查报告.md')
    (job/'结果目录.txt').write_text(str(dest),encoding='utf-8')
    return result

def inspect_only(source,output,job,handles_seconds=0):
    if handles_seconds not in (0,2,5):raise ValueError('片段余量只支持0、2或5秒。')
    source=source.resolve();output=output.resolve()
    if source==output or source in output.parents:raise ValueError('输出目录必须位于源草稿目录之外。')
    data,authority,digest=load_draft(source,job)
    from aaf_inspection import inspect
    report,path,_,_,_=inspect(sys.modules[__name__],data,source,authority,digest,job,handles_seconds)
    if hashlib.sha256(authority.read_bytes()).hexdigest()!=digest:raise RuntimeError('检查期间草稿发生变化，请保存后重新检查。')
    return dict(report=str(path),can_export=report['can_export'],issues=report['issues'],project=source.name)

def run(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);ap.add_argument('--job-id');ap.add_argument('--inspect',action='store_true');ap.add_argument('--handles',type=int,choices=[0,2,5],default=0);ap.add_argument('--stems',action='store_true');ap.add_argument('--batch-stems',action='store_true');args=ap.parse_args(argv)
    if sum((args.inspect,args.stems,args.batch_stems))>1:ap.error('检查、单集分轨、多集分轨只能选择一种')
    if args.job_id and not re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]{8}',args.job_id):ap.error('invalid job id')
    base=pathlib.Path(os.environ.get('LOCALAPPDATA',str(pathlib.Path.home())))/'JYMixBridge';base.mkdir(parents=True,exist_ok=True)
    job=base/(args.job_id or (time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]));job.mkdir();result={'ok':False,'job':str(job)}
    with (job/'任务日志.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        try:
            import msvcrt
            with (base/'worker.lock').open('a+b') as lock:
                lock.seek(0)
                try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                except OSError as exc:raise RuntimeError('已有AAF任务正在运行，请等待结束。') from exc
                try:
                    if lock.seek(0,2)==0:lock.write(b'0');lock.flush()
                    if not args.source.strip() or not args.output.strip(): raise ValueError('请填写单集草稿目录和AAF输出目录。')
                    if args.stems or args.batch_stems:
                        import stems_export
                        result['result']=(stems_export.batch if args.batch_stems else stems_export.export)(sys.modules[__name__],pathlib.Path(args.source),pathlib.Path(args.output),job)
                        result['ok']=not args.batch_stems or result['result']['failed']==0
                        if not result['ok']:result['error']='批量导出存在失败工程，请查看批量汇总。'
                    else:
                        result['result']=(inspect_only if args.inspect else export)(pathlib.Path(args.source),pathlib.Path(args.output),job,args.handles);result['ok']=True
                finally: lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
        except Exception as exc:
            import traceback
            result['error']=str(exc)
            if isinstance(exc,DraftReadError):result.update(error_code=exc.code,diagnostic=exc.diagnostic)
            traceback.print_exc()
    (job/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    value=result.get('result',{})
    if args.batch_stems and value:
        summary=f"批量完成：成功{value['success']}集，失败{value['failed']}集\n"+value['output']
    elif not result['ok']:summary='任务失败\n'+result['error']
    elif args.stems:summary='分轨完成：'+str(len(value['tracks']))+'轨；请核对交接差异\n'+value['output']
    elif args.inspect:summary='检查完成'+('：有阻止导出的问题' if not value['can_export'] else '')+'\n'+value['report']
    else:summary=('导出完成：有'+str(len(value.get('risks',[])))+'项交接差异，请查看报告' if value.get('risks') else '导出完成：素材交接AAF，请核对声音差异')+'\n'+value['aaf']
    (job/'任务结果.txt').write_text(summary,encoding='utf-8')
    return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(run())
