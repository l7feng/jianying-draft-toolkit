# 剪映 OFX 接口探针

项目71的最小诊断插件，版本0.1。只透传画面、记录宿主接口和参数事件，不导入、导出或修改音频工程，不联网、不启动外部程序。

## 当前验证范围

已在 Windows x64 TinyCC 0.9.27 构建，并通过独立 Python/ctypes 合成 OFX 宿主测试。剪映11.7.0.14596中的导入、参数界面、实际渲染和保存重开尚未验证。不能把合成测试当作剪映兼容性通过。

## 文件

- probe.c：原生 C 插件。
- test_probe.py：独立合成宿主测试；检查位深、行方向、边界、句柄释放和必要接口缺失。
- build.ps1：本地构建，不自动下载、安装或注册插件。
- vendor/openfx：官方头文件与原许可证；完整来源及文件哈希见构建目录sdk-manifest.json。
- 产物：仓库 build/ofx-probe/JYInterfaceProbe.ofx；同时生成标准 .ofx.bundle 布局作为备用，不代表剪映必须使用该布局。

## 构建与测试

从本目录执行，需已有x64 TinyCC以及Python3。便携TinyCC放在仓库build/ofx-probe/toolchain/tcc时无需指定Compiler。

~~~powershell
.\build.ps1
& 'D:/Ai-Files/Tools/BuildEnv/py312/python.exe' .\test_probe.py ../../build/ofx-probe/JYInterfaceProbe.ofx ../../build/ofx-probe/synthetic-test-results.json
~~~

官方编译器来源：https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip 。已下载到隔离构建目录，未安装全局软件。OpenFX头文件：https://github.com/AcademySoftwareFoundation/openfx ，BSD-3-Clause；本模块没有重分发剪映内置插件。

## 剪映手动验证

1. 新建一个独立测试草稿，加入一张无业务内容的图片到时间线。
2. 在“插件”页导入build/ofx-probe/JYInterfaceProbe.ofx。
3. 如果识别成功，将JY Interface Probe应用到测试素材；若剪映采用其他应用方式，按实际界面记录。
4. 如显示参数，调整Probe value并点击Record capabilities。Draft path probe保留空值，用于观察宿主是否主动注入草稿路径；手工输入不会证明注入成功。
5. 播放测试素材、保存关闭再重开，核查画面透传和稳定性。导入拒绝、参数缺失、按钮不显示均应记录原提示。
6. 日志位于实际加载进程账户的%LOCALAPPDATA%/JyOfxProbe/probe-进程号.log。只记录接口、动作及草稿路径是否存在和长度，不记录路径正文。仅有日志文件不证明所有阶段通过；未出现日志也可能是插件尚未加载或目录不可写。

## 接口探测边界

只查询标准suite，以及内置插件中观察到的标准OpenGL suite。草稿参数名param_draft_path来自剪映内置smart_cut.ofx字符串，只是调查线索，未有公开注入契约。未实现未知的OfxImageContextAlgorithm、OfxAlgoJson或OfxMessageParamUpdate协议。

不绕过lyra-cli宿主授权，不读取用户运行token，不调用apply-patch。音频业务能否实现，以后续正式接口或隔离验证为准。

## 项目状态入口

D:/1-个人知识库_Vault/4-项目-P/71-剪映音频批处理插件接入验证/Documentation.md 为唯一项目进度入口；本README仅说明构建和使用。

