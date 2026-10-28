# 剪映工程工具包

版本：4.3.1。

导入交付包、处理剪映草稿并导出音频。本版移除人声分离；包含草稿解密器，FFmpeg 可通过随包入口安装。

## 下载与使用

在 [GitHub Releases](https://github.com/l7feng/jianying-draft-toolkit/releases) 下载对应 Windows x64 ZIP，完整解压后打开中文名称的 EXE。详细依赖和验证边界见 [使用说明](packaging/使用说明.md)。

## 源码构建

安装 Python 3.12、PyInstaller、pywebview、pyaaf2；PT 构建另需 py-ptsl 602.0.0。运行 `python tools/v4_pack/build_v4.py jy --out-root build/output`。具体构建版本见 `packaging/build-requirements.txt`。
