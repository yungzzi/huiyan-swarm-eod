
# 目录
- [目录](#目录)
- [简介](#简介)
- [在 macOS 上安装](#在-macos-上安装)
- [在 Ubuntu 上安装（推荐）](#在-ubuntu-上安装推荐)
  - [**VirtualBox 用户的警告**](#virtualbox-用户的警告)
  - [Git 与 Arcade 库依赖](#git-与-arcade-库依赖)
  - [*Python* 安装](#python-安装)
  - [安装本 *swarm-rescue* 仓库](#安装本-swarm-rescue-仓库)
- [在 Windows 10/11 上使用 WSL2 安装](#在-windows-1011-上使用-wsl2-安装)
  - [WSL2：OpenGL 与 GPU 选择](#wsl2opengl-与-gpu-选择)
- [在 Windows 10/11 上使用 GitBash 安装](#在-windows-1011-上使用-gitbash-安装)
  - [**Windows 用户的警告**](#windows-用户的警告)
  - [*Python* 安装](#python-安装-1)
  - [*Git* 安装](#git-安装)
  - [配置 *Git Bash*](#配置-git-bash)
  - [安装本 *swarm-rescue* 仓库](#安装本-swarm-rescue-仓库-1)
- [故障排查](#故障排查)
  - [停用 OpenGL 着色器](#停用-opengl-着色器)
  - [检查软件版本](#检查软件版本)
  - [在 Ubuntu 和 WSL2 上查看 OpenGL 版本](#在-ubuntu-和-wsl2-上查看-opengl-版本)
  - [更新 Mesa 库](#更新-mesa-库)
- [Python IDE](#python-ide)
- [联系方式](#联系方式)

# 简介

这套安装流程已在 **Ubuntu** 和 **Windows 11 + Git Bash** 上成功测试。Ubuntu 是获得最佳性能和稳定性的推荐平台。

# 在 macOS 上安装

在 **macOS 系统**上安装具有挑战性，且**不受官方支持**。*Swarm-Rescue* 需要较新版本的 *OpenGL* 才能正常运行。然而，较新版本的 macOS 已不再使用 *OpenGL*，转而依赖苹果的 *Metal* 图形框架。

无论如何，过去代码不得不为 macOS 做过适配，结果是相比 Ubuntu 系统出现明显的性能下降。如果你必须使用 macOS，请参考[停用 OpenGL 着色器](#停用-opengl-着色器)

# 在 Ubuntu 上安装（推荐）

这套安装流程已在 Ubuntu 20.04、22.04 和 24.04 上测试。

## **VirtualBox 用户的警告**

**VirtualBox 用户报告过兼容性问题**。

*Swarm-Rescue* 使用 *OpenGL* 着色器来加速计算。Lidar 和语义传感器的计算直接通过这些着色器在 GPU 上完成，以获得最佳性能。

VirtualBox 在图形驱动和 OpenGL 处理方面存在已知问题，可能导致 *Swarm-Rescue* 出错。

你有几种解决方案：
- **推荐**：原生安装 Ubuntu（不使用 VirtualBox）
- **备选**：采用[停用 OpenGL 着色器](#停用-opengl-着色器)中描述的变通方案

## Git 与 Arcade 库依赖

首先，你显然需要安装 Git 工具。

*Arcade* 库（用于 2D 图形）需要 *libjpeg-dev* 和 *zlib1g-dev* 才能正常工作。

```bash
sudo apt update
sudo apt install git git-gui gitk libjpeg-dev zlib1g-dev
```

## *Python* 安装

*Swarm-Rescue* 需要 **Python 3.8 或更高版本**。Python 3.8 是 Ubuntu 20.04 的默认版本。

```bash
sudo apt update
sudo apt install python3 python3-venv python3-dev python3-pip
```

确认你的 Python 版本：
```bash
python3 --version
```

## 安装本 *swarm-rescue* 仓库

**第 1 步：准备你的工作区**
进入你想要的工作目录（例如 *~/code/*）：

```bash
cd
mkdir code
cd code
```

**第 2 步：克隆仓库**
从 [*Swarm-Rescue*](https://github.com/emmanuel-battesti/swarm-rescue) 下载代码：

```bash
git clone https://github.com/emmanuel-battesti/swarm-rescue.git
```

这会创建包含全部源代码的 *swarm-rescue* 目录。

**第 3 步：创建虚拟环境**
为项目搭建一个隔离的 Python 环境：

```bash
cd swarm-rescue
python3 -m venv .venv
```
它会创建一个 *.venv* 目录，所有依赖都会安装在那里。

**第 4 步：激活虚拟环境**
激活该环境（每次使用项目时都需要）：

```bash
source .venv/bin/activate
```

完成后要停用虚拟环境：`deactivate`

**第 5 步：安装依赖**
在虚拟环境已激活的情况下，安装所有必需的软件包：

```bash
python3 -m pip install --upgrade pip
python3 -m pip install --editable .
```

**第 6 步：测试安装**
通过运行启动器来验证一切正常：

```bash
python3 ./src/swarm_rescue/launcher.py
```

**仿真器元素：** 代码库使用 *Bomb* 和 *DisposalCenter*（而不是 `WoundedPerson` / `RescueCenter`）。如果你要移植旧版队伍代码，请参阅 `README.md` 中的 "API 命名"表。

# 在 Windows 10/11 上使用 WSL2 安装

它仍然**非常实验性且未经充分测试**，但看起来是可以在 Windows 的 WSL2 上安装 *Swarm-Rescue* 的。
为此需要确认几点：
- 使用 WSL 2 而不是 WSL 1，
- 拥有 Windows 11，或已安装最新更新的 Windows 10，
- 更新到最新的显卡驱动，然后重启，
- WSL 使用 Ubuntu 24.04（Ubuntu 22.04 或更早版本无法工作）。

然后只需按照 Ubuntu 的安装说明操作：[在 Ubuntu 上安装（推荐）](#在-ubuntu-上安装推荐)

> [!NOTE]
> 更准确地说，在 WSL 下无需为显卡安装驱动。WSL 通过虚拟接口使用 Windows 的图形驱动。OpenGL 支持由 Mesa 库提供。WSL 中 Ubuntu 22.04 的 Mesa 版本不支持所需的 OpenGL 4.4 特性，这就是为什么必须使用 Ubuntu 24.04。

## WSL2：OpenGL 与 GPU 选择

在 WSL2 上，GUI OpenGL 走的是 Mesa 的 **d3d12** Gallium 驱动和 Windows 显示栈——而不是单独的 Linux `nvidia-driver` 包。**`nvidia-smi` 只能确认 CUDA**；它不显示 OpenGL 是否使用了你的独立显卡。

射线传感器使用 GLSL `#version 440`（见 `src/swarm_rescue/simulation/ray_sensors/shaders/id_compute.glsl`），这要求 **GLSL 4.40+**，因而需要 **OpenGL 4.4+** 上下文。某些系统上的集成显卡路径只报告 OpenGL 4.1 / GLSL 4.10，尽管版本号看起来"很接近"，但**并不满足要求**。

### 启用硬件 OpenGL（避免 llvmpipe）

未经配置时，`glxinfo` 可能报告 `llvmpipe`（CPU 软件渲染）。强制使用 D3D12 后端：

```bash
sudo apt install mesa-utils   # 提供 glxinfo
export GALLIUM_DRIVER=d3d12
glxinfo | grep "OpenGL renderer"
```

你应该看到 `D3D12 (...)` 而不是 `llvmpipe`。

### 选择 NVIDIA（或其他独立显卡）

在有多块 GPU 的系统上，Mesa 常常选择第一个枚举到的适配器（通常是 Intel 集成显卡）。要使用 NVIDIA 显卡，请在 `~/.bashrc` 或 `~/.zshrc` 中设置：

```bash
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=nvidia
```

`MESA_D3D12_DEFAULT_ADAPTER_NAME` 是 Windows 设备管理器中 GPU 名称的**子串**（不区分大小写），例如 `nvidia`、`NVIDIA`、`4090`。参见 [WSLg 中的 GPU 选择](https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg)。

重新加载 shell，然后验证：

```bash
glxinfo | grep -E "OpenGL renderer|OpenGL version|shading language"
```

一个可用的独立显卡配置示例：

```text
OpenGL renderer string: D3D12 (NVIDIA GeForce RTX 4090)
OpenGL version string: 4.6 (Compatibility Profile) Mesa ...
OpenGL shading language version string: 4.60
```

然后从项目虚拟环境中验证：

```bash
python src/swarm_rescue/tools/opengl_info.py
```

### Windows 侧设置（如果 OpenGL 仍在使用 Intel）

如果环境变量还不够，请在 Windows 的**设置 → 系统 → 显示 → 图形**（或 NVIDIA 控制面板）中，为以下程序指定**高性能** / NVIDIA：

- `C:\Windows\System32\wsl.exe`
- `C:\Windows\System32\wslhost.exe`

然后在 PowerShell 中执行：`wsl --shutdown`，并重新打开 Ubuntu。

### 在 WSL2 上不要做的事

- **不要**在 WSL 内为 GUI OpenGL 安装 `nvidia-driver-*`（Windows 驱动已暴露在 `/usr/lib/wsl/lib` 下）。
- **不要**在 WSL 中使用 `__GLX_VENDOR_LIBRARY_NAME=nvidia`；它常常会回退到 `llvmpipe`。

当 Ubuntu 24.04 已经自带较新的 Mesa 时，通过 [kisak PPA](#更新-mesa-库)升级 Mesa 在 WSL2 上是可选的；真正要紧的通常是修好 **GPU 选择**（`GALLIUM_DRIVER` + `MESA_D3D12_DEFAULT_ADAPTER_NAME`）。

# 在 Windows 10/11 上使用 GitBash 安装

这套安装流程已在 Windows 11 上测试（2025 年 10 月）

## **Windows 用户的警告**

**Windows 用户报告过各种问题**，从意外行为到程序完全崩溃。

**常见问题：**
- Lidar 传感器穿透墙体进行探测
- 语义传感器在炸弹被抓起后仍然探测到它（被抓起的炸弹应当对携带者的语义射线隐藏；如果没有，请检查驱动/OpenGL）
- 仿真整体不稳定

**根本原因：**

*Swarm-Rescue* 使用 OpenGL 着色器进行 GPU 加速计算（lidar 和语义传感器计算）。这些问题似乎源于图形驱动兼容性或 Windows 的 OpenGL 实现。
该问题在 Ubuntu 上似乎不会出现。在某些"更强"的 Windows 机器（台式机）上，它也能正常工作。

**环境要求：**
- Windows 11，或已安装最新更新的 Windows 10
- 最新的显卡驱动（安装后重启）
- 配置最佳性能设置

如果问题持续存在，你有几种解决方案：
- 换用 Ubuntu 操作系统，
- 换一台机器，更强的台式机往往问题更少
- 使用[停用 OpenGL 着色器](#停用-opengl-着色器)中的变通方案

## *Python* 安装

- 在浏览器中打开以下链接：https://www.python.org/downloads/windows/
- 该程序**无法**在高于或等于 3.12 的 Python 版本上运行。（3.13.7 2025 年 8 月 14 日）
- 不要选择最新版本的 Python，而要选择 3.11.9 版本。目前（2023 年 10 月）它是 "*Python 3.11.9 - April 2, 2024*"。
- 对于现代机器，必须选择 *Windows installer (64-bit)*。
- 下载安装程序后，运行 Python 安装程序。
- **重要**：你需要勾选"**Add python.exe to path**"复选框，把解释器加入执行路径。

## *Git* 安装

Git 对于源代码管理和跟踪 *swarm-rescue* 项目的改动至关重要。

**安装步骤：**
1. 下载[最新版本的 Git](https://git-scm.com/download/win)
2. 在 "Standalone Installer" 中选择 "Git for Windows/x64 Setup"
3. 使用默认配置安装
4. 选择 "Launch Git Bash" 并点击 "Finish"

*Git Bash* 终端将成为你进行项目工作的主要界面。

## 配置 *Git Bash*

- 运行 *Git Bash* 终端。
- **警告**，默认情况下你可能**不在**自己的主目录中。要进入主目录，只需输入 `cd`。
- 如果一切正常，命令 `python --version` 应显示已安装的 Python 版本，例如：`Python 3.11.9`。

## 安装本 *swarm-rescue* 仓库

- 要安装这个 git 仓库，请进入你想工作的目录（例如：*~/code/*）。
- 使用 *Git Bash* 时，你必须使用这些 Linux 命令，例如：
```bash
cd
mkdir code
cd code
```

从 [*Swarm-Rescue*](https://github.com/emmanuel-battesti/swarm-rescue) 克隆代码：

```bash
git clone https://github.com/emmanuel-battesti/swarm-rescue.git
```

这会创建包含全部源代码的 *swarm-rescue* 目录。

- 创建你的虚拟环境。这个命令会创建一个 *.venv* 目录，所有依赖都会安装在其中：

```bash
cd swarm-rescue
python -m venv .venv
```

- 要使用这个新建的虚拟环境（每次需要时都要执行），请使用命令：

```bash
source .venv/Scripts/activate
```

完成后要停用这个虚拟环境，只需输入：`deactivate`

- 在虚拟环境已激活的情况下，我们可以用以下命令安装所有依赖：

```bash
python -m pip install --upgrade pip
python -m pip install --editable .
```

测试安装：

```bash
python ./src/swarm_rescue/launcher.py
```
# 故障排查

## 停用 OpenGL 着色器

着色器是用 GLSL 编写的 GPU 加速程序，能显著提升性能。但兼容性问题可能要求禁用它们。

禁用着色器：
1. 打开文件 *src/swarm_rescue/simulation/gui_map/closed_playground.py*
2. 在 `ClosedPlayground.__init__` 中，把 `use_shaders` 从 *True* 改为 *False*

**注意**：这会降低性能，尤其是在多架无人机的情况下。

## 检查软件版本

*Swarm-Rescue* 需要 **GLSL 4.40+**（着色器 `#version 440`），实际意味着 **OpenGL 4.4+**。并不存在单独的 "4.40" 这个 OpenGL API 版本；那个数字指的是着色语言版本。

用这个脚本验证你的系统：
```bash
python src/swarm_rescue/tools/opengl_info.py
```

在 WSL2 上，设置完 [WSL2：OpenGL 与 GPU 选择](#wsl2opengl-与-gpu-选择)后，还要用 `glxinfo` 检查渲染器和 GLSL 版本——在 `llvmpipe` 上或在使用 GLSL 4.10 的集成显卡上，OpenGL 版本号再高也不够。

## 在 Ubuntu 和 WSL2 上查看 OpenGL 版本

使用 *glxinfo* 检查你的 OpenGL 版本：

安装 *glxinfo*：
```bash
sudo apt update
sudo apt install mesa-utils
```

使用 *glxinfo*：
```bash
glxinfo | grep -E "OpenGL renderer|OpenGL version|shading language"
```

在 WSL2 上，请在导出 `GALLIUM_DRIVER=d3d12` 之后（如果你有独立显卡，还要导出 `MESA_D3D12_DEFAULT_ADAPTER_NAME=nvidia`）再运行同样的命令（见上文）。

## 更新 Mesa 库

在 Linux 或 WSL2 下，要把 Mesa 库更新到最新（但非官方）版本：
```bash
sudo add-apt-repository ppa:kisak/kisak-mesa
sudo apt update
sudo apt upgrade
```

# Python IDE

虽然是可选的，但使用 IDE 能提升 Python 开发体验。

**推荐**：[*PyCharm Community*](https://www.jetbrains.com/pycharm/)（免费）
- 把解释器路径配置到你的虚拟环境（.venv）以获得正确的集成

# 联系方式

有关安装或代码的问题：

**邮箱**：emmanuel . battesti at ensta . fr

**Discord**：项目的 Discord 服务器上可获取
