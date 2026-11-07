# 剪映音频工具 OFX 使用说明

这是音频业务初版，插件标识local.jytools.AudioToolkit，版本0.1；原Interface Probe为独立诊断插件，两者不互相替换。

## 导入

在剪映“插件”页选择导入文件夹，选完整的JYAudioToolkit.ofx.bundle。应用后使用右侧面板的路径和按钮。此版本已通过独立宿主与合成音频测试，剪映中的业务按钮与外部进程启动仍待真实使用验证。

## 路径与操作

- 草稿或素材目录：导出时可以填单个草稿、草稿库或音视频素材目录；导入时必须填单个目标草稿。
- 音频输出目录：导出结果位置。
- PT JSON或CSV清单：沿用原EXE的pt-clips.json或含source/track_no等列的CSV。
- 新草稿副本目录：导入输出位置，必须是尚不存在的独立目录。
- 导出方式：整轨、片段或两者。
- 批量导出音频：启动后台任务。
- 导入到新草稿副本：复制草稿并导入音频；不改剪映当前打开的工程。副本不自动注册到草稿库，需后续通过剪映支持的工程导入/打开方式使用；新版剪映可打开性尚待验证。
- 打开原工具包：打开现有EXE，保留完整旧工作流入口。
- 查看任务记录：打开实际执行账户的%LOCALAPPDATA%/JyOfxAudio，每个任务有结果说明.txt、task.log及result.json。

## 与EXE的关系

复用原仓库jianying-draft-toolkit的导入、导出、命名和轨道逻辑。默认路径先参考EXE的jy.h-preferences.local.json；发现其C盘旧路径不存在后，只在新OFX默认值中更正到已存在的D:/My-Temporary/Backup-Jianying/Project/JianyingPro Drafts及D:/My-Temporary/Backup-Jianying/Tools/out。旧EXE配置未改。

仅继承已接入选项，不是整个EXE界面的逐项复制。当前不包含人声分离、AAF、字幕和按视频分包；它们仍可通过原EXE使用。音频格式与命名等后台设置参考旧配置，冲突采用重命名。原核心对片段WAV输出44.1kHz立体声；本次整轨样本输出48kHz立体声，按最后音频片段末尾对齐，不额外保留工程尾部静音。

## 本地依赖

这是当前设备的本地桥接版，.ofx负责剪映内参数与操作，Python核心在原仓库运行，未嵌入.ofx。需要保留D:/Ai-Files/Repos/GitHub/pt-audio-toolkit、D:/Ai-Files/Tools/BuildEnv/py312及FFmpeg；只复制.ofx到其他机器不能独立使用。没有绕过剪映运行时令牌或内部CLI权限。

批量导出使用磁盘草稿内容，请先在剪映保存；它不通过剪映实际音效引擎渲染，不能保证降噪、变声等专有效果与剪映导出一致。

## 构建与验证

运行build_audio.ps1生成独立build/ofx-audio-v0.1目录内的完整bundle。便携TinyCC沿用build/ofx-probe/toolchain/tcc。test_audio_worker.py验证导出、导入副本、源文件保护及失败计数；test_audio_plugin.py验证ABI及图像透传；test_audio_dispatch.py对测试专用dispatch-test.dll验证原生按钮回调到后台导出（测试构建屏蔽通知弹窗）。

唯一项目进度在知识库项目71的Documentation.md。

