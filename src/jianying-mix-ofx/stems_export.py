"""Read-only Jianying drafts -> aligned track WAVs; never drives the editor."""
import hashlib,json,pathlib,re,shutil,wave


def check_wave(path,channels,length,rate):
    with wave.open(str(path),'rb') as f:
        if (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())!=(channels,3,rate,length):
            raise RuntimeError('分轨规格或时间线长度不匹配：'+str(path))


def mix_channel(w,items,total,work,label):
    # Bound Windows argument length and input count, including dense timelines.
    paths=[]
    for index in range(0,len(items),16):
        chunk=items[index:index+16];target=work/f'{label}-{index//16}.wav'
        args=['ffmpeg','-y','-v','error']
        for path,_ in chunk:args+=['-i',path]
        graph=[]
        for i,(_,start) in enumerate(chunk):graph.append(f'[{i}:a]adelay={start}S:all=1[x{i}]')
        graph.append(''.join(f'[x{i}]' for i in range(len(chunk)))+f'amix=inputs={len(chunk)}:normalize=0:dropout_transition=0,apad,atrim=end_sample={total}[out]')
        args+=['-filter_complex',';'.join(graph),'-map','[out]','-ar',str(w.SR),'-ac','1','-c:a','pcm_f32le',target]
        w.run_command(args);paths.append((target,0))
    if not paths:
        target=work/f'{label}-silence.wav'
        w.run_command(['ffmpeg','-y','-v','error','-f','lavfi','-i',f'anullsrc=r={w.SR}:cl=mono','-af',f'atrim=end_sample={total}','-c:a','pcm_f32le',target])
        return target
    if len(paths)>1:return mix_channel(w,paths,total,work,label+'-sum')
    return paths[0][0]


def export(w,source,output,job):
    source=source.resolve();output=output.resolve()
    if source==output or source in output.parents:raise ValueError('输出目录必须位于源草稿目录之外。')
    w.media_tool('ffmpeg');w.media_tool('ffprobe')
    data,authority,digest=w.load_draft(source,job)
    from aaf_inspection import inspect
    report,report_path,tracks,total,warnings=inspect(w,data,source,authority,digest,job)
    if report['issues']:raise ValueError('工程检查未通过：'+report['issues'][0])
    if any(c['channels']>2 for t in tracks for c in t['clips']):raise ValueError('当前分轨支持单声道/立体声素材；发现超过2声道素材，请先核对声道映射。')
    output.mkdir(parents=True,exist_ok=True)
    name=w.safe(source.name)+'-分轨-'+job.name
    pending=output/(name+'.未完成');final=output/name
    if pending.exists() or final.exists():raise ValueError('本次输出目录已存在，拒绝覆盖。')
    pending.mkdir();work=job/'分轨中间文件';work.mkdir()
    results=[];pads=[]
    for ti,track in enumerate(tracks,1):
        channels=max(c['channels'] for c in track['clips']);items=[[] for _ in range(channels)]
        for ci,clip in enumerate(track['clips']):
            for ch in range(channels):
                # FFmpeg mono -> stereo uses identical samples on both channels.
                source_ch=0 if clip['channels']==1 else ch
                wav=work/f't{ti}-c{ci}-ch{ch}.wav'
                w.run_command(['ffmpeg','-y','-v','error','-ss',f"{clip['offset']/1e6:.9f}",'-i',clip['path'],'-map','0:a:0','-t',f"{clip['length']/w.SR:.9f}",'-af',w.audio_filter(clip,source_ch,0,0),'-ar',str(w.SR),'-ac','1','-c:a','pcm_s24le',wav])
                padding=w.normalize_pcm_tail(wav,clip['length'])
                if padding:pads.append(dict(track=track['name'],clip=ci+1,channel=ch+1,samples=padding))
                items[ch].append((wav,clip['start']))
        mixes=[mix_channel(w,l,total,work,f't{ti}-mix{ch}') for ch,l in enumerate(items)]
        filename=f'{ti:02d}-{w.safe(track["name"])}.wav';wav=pending/filename
        args=['ffmpeg','-y','-v','error']
        for path in mixes:args+=['-i',path]
        if channels==2:args+=['-filter_complex','[0:a][1:a]amerge=inputs=2[out]','-map','[out]']
        else:args+=['-map','0:a:0']
        args+=['-ar',str(w.SR),'-ac',str(channels),'-c:a','pcm_s24le',wav]
        w.run_command(args);check_wave(wav,channels,total,w.SR)
        with wav.open('rb') as stream:digest_wav=hashlib.file_digest(stream,'sha256').hexdigest()
        results.append(dict(name=track['name'],file=filename,channels=channels,samples=total,sha256=digest_wav))
        print('已完成分轨：'+filename,flush=True)
    if hashlib.sha256(authority.read_bytes()).hexdigest()!=digest:raise RuntimeError('导出期间源草稿发生变化，结果保留为未完成，请保存后重试。')
    notes=warnings+['各轨从时间线零点开始，包含首尾静音；同轨重叠片段直接叠加，不自动归一化，超过满幅可能削波。','原轨内混合单/双声道时输出立体声，单声道片段复制到左右声道。']
    if pads:notes+=['部分源音频短尾补静音（每份不超过20毫秒），采样数见清单。']
    result=dict(project=source.name,source=str(source),output=str(final),mode='stems',sample_rate=w.SR,bit_depth=24,duration_samples=total,tracks=results,risks=report['risks'],warnings=notes,padding=pads,source_unchanged=True)
    (pending/'分轨清单.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (pending/'分轨说明.txt').write_text('分轨导出完成；这是素材剪辑交接，非剪映最终效果渲染。\n'+'\n'.join(report['risks']+notes),encoding='utf-8')
    shutil.copy2(report_path,pending/'工程检查报告.md');pending.rename(final)
    (job/'结果目录.txt').write_text(str(final),encoding='utf-8')
    return result


def batch(w,source,output,job):
    source=source.resolve();output=output.resolve()
    if not source.is_dir():raise ValueError('多集目录不存在。')
    if source==output or source in output.parents:raise ValueError('批量输出必须位于草稿父目录之外。')
    if str(w.CODE) not in w.sys.path:w.sys.path.insert(0,str(w.CODE))
    import import_audio as imp
    if imp.resolve_content_files(source)[0]:raise ValueError('当前选的是单集草稿，请选择包含多集草稿的父目录。')
    def natural(p):return [int(x) if x.isdigit() else x.casefold() for x in re.split(r'(\d+)',p.name)]
    episodes=[];skipped=[]
    for child in sorted(source.iterdir(),key=natural):
        if not child.is_dir() or child.is_symlink() or child.is_junction():continue
        if imp.resolve_content_files(child)[0]:episodes.append(child)
        else:skipped.append(child.name)
    if not episodes:raise ValueError('此目录的直接子目录中没有可识别的剪映工程。')
    dest=output/('批量分轨-'+job.name)
    if dest.exists():raise ValueError('批量输出目录已存在，拒绝覆盖。')
    dest.mkdir(parents=True);entries=[]
    for i,episode in enumerate(episodes,1):
        childjob=job/f'{i:03d}';childjob.mkdir()
        try:
            value=export(w,episode,dest,childjob);entries.append(dict(project=episode.name,ok=True,result=value))
        except Exception as exc:
            import traceback
            (childjob/'失败详情.txt').write_text(traceback.format_exc(),encoding='utf-8')
            entries.append(dict(project=episode.name,ok=False,error=str(exc)))
        (dest/'批量汇总.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'批次进度：{i}/{len(episodes)}，{episode.name}',flush=True)
    success=sum(e['ok'] for e in entries)
    result=dict(mode='batch_stems',output=str(dest),total=len(entries),success=success,failed=len(entries)-success,skipped=skipped,episodes=entries)
    (dest/'批量说明.txt').write_text(f'共{len(entries)}集，成功{success}集，失败{len(entries)-success}集。\n只扫描父目录直接子工程；失败和声音处理差异见批量汇总及各集报告。',encoding='utf-8')
    (job/'结果目录.txt').write_text(str(dest),encoding='utf-8')
    return result
