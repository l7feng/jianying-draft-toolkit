# JY Tools

版本：4.3.1（见 `VERSION`）。

把剪映草稿与音频交付互相打通：从剪映草稿导出音频、把多轨音频导入剪映草稿、生成交付包。本版移除人声分离，保留草稿解密器；FFmpeg 可通过随包入口安装。

## 目录

```text
jy-tools/
├── src/
│   ├── jy-tools/   主工具：GUI 三个标签页（导出音频／导入多轨／生成交付包）
│   ├── jy-mix-ofx/         OFX 混音相关实现与工人进程
│   ├── jy-ofx-probe/       OFX 音频探针（含 C 源）
│   ├── pt-tools/                 与 PT 工具箱共用的扫描／导出代码
│   └── v4/                       H 版外壳：只留 API 与 shell，界面在库外 Web 真源
├── tools/                        打包入口：build.py、v4_pack/build_v4.py、verify_exe.py
├── web/                          内嵌界面（index／jy／re 三个入口页）
├── packaging/                    依赖安装脚本、锁定版本清单、使用说明
└── README.md · CHANGELOG.md · VERSION · LICENSE
```

## 跑起来

主工具 GUI：

```bash
python src/jy-tools/code/gui.py
```

首次运行先按 `packaging/build-requirements.txt` 装依赖；缺组件时用 `packaging/Install-Dependencies.cmd`。界面依赖 Microsoft Edge WebView2 Runtime（大部分 Windows 已安装）。

## 构建与发布

```bash
python tools/build.py                 # 默认构建三个工具
python tools/build.py pt-tools jy     # 只构建指定目标
python tools/v4_pack/build_v4.py jy   # H 版包
python tools/verify_exe.py            # 构建后校验
```

依赖精确版本见 `packaging/build-requirements.txt`（声明与锁合一，构建前按它装环境）。出口布局与重建前归档规则写在 `tools/build.py` 顶部注释；发行包在 [GitHub Releases](https://github.com/l7feng/jy-tools/releases)，下载 ZIP 完整解压后运行 JY Tools 的 EXE（保留 `_internal`）。

## 已知边界

- 面向 Windows 10/11 x64；未在全新 Windows、真实 Pro Tools 工程或真实剪映草稿上做业务验收。
- 草稿解密依赖剪映自带的 `videoeditor.dll`；剪映版本变化可能导致失效。
- `src/v4` 的 Web 界面真源仍在本仓之外（`D:/Ai-Files/Tools/Html/pt-audio-toolkit/source`，2026-10-14 人类裁决迁出）。clone 后只能跑 API 与 shell，不能完整复现 H 版界面，属按 07 判据未收口项，待裁决收回或登记例外。
- 本仓是多工具合仓（PT 工具箱、JY Tools、Rename Project 共用一套 `web/` 与 `tools/`）；单工具能否独立 clone 运行尚未验证。

## 验证

- 构建：`python tools/build.py` 后跑 `verify_exe.py` 逐包校验；失败会打印目标名、返回码与关键 stderr 行。
- 测试：本仓无自动化测试目录，回归依赖打包后的人工验收。
- 当前状态以本页与 `CHANGELOG.md` 为准，历史见 `git log`。
