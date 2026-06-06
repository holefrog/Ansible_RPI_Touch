# LVGL 仿真调试指南（Ubuntu）

本文件说明如何在 Ubuntu 宿主机上安装 LVGL 开发环境，并使用 SDL2 仿真调试 480x320 电容触摸屏界面。

> 本指南适用于当前项目的 `touch` 角色开发阶段。我们当前只做方案设计与基础界面规划，不做编码实现。

## 1. 环境准备

### 1.1 系统要求

- Ubuntu 20.04 / 22.04 / 24.04
- 已安装常规开发工具：`gcc`、`g++`、`cmake`、`make`
- 推荐使用 WSL2 以外的本机 Ubuntu，避免鼠标/SDL 输入映射兼容性问题

### 1.2 安装依赖

打开终端，依次执行：

```bash
sudo apt update
sudo apt install -y build-essential cmake pkg-config git 
    libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev libfreetype6-dev libglib2.0-dev libudev-dev libx11-dev libxkbcommon-dev
```

说明：
- `libsdl2-dev` 用于 SDL2 窗口与鼠标仿真
- `libsdl2-image-dev` 用于加载图片资源（可选，后续如果需要 PNG/图标支持）
- `libfreetype6-dev` 用于 LVGL 字体渲染

## 2. LVGL 仿真开发准备

### 2.1 获取 LVGL 仿真底座

如果项目还没有 `tools/lv_port_pc_vscode` 子模块，可按下面流程准备：

```bash
cd /home/david/Coding/Ansible_RPI_Touch
git submodule add https://github.com/lvgl/lv_port_pc_vscode.git tools/lv_port_pc_vscode
```

如果已经有该目录，则只需更新子模块：

```bash
git submodule update --init --recursive
```

### 2.2 准备自定义 UI 源码目录

建议把 C UI 业务代码放在项目中的独立目录，例如：

```text
src/ui_custom/
```

仿真底座与业务代码的关系可以通过软连接或 CMake 包含方式建立：

```bash
cd /home/david/Coding/Ansible_RPI_Touch/tools/lv_port_pc_vscode
ln -s ../../src/ui_custom ui_custom
```

> 如果你使用本仓库提供的构建脚本 `tools/build_lv_port_pc_vscode.sh`，它会自动在子模块中创建临时 `ui_custom` 链接，所以不必手动建立。

### 2.3 修改仿真底座 CMake 配置

建议在 `tools/lv_port_pc_vscode/CMakeLists.txt` 中增加对自定义目录的扫描：

```cmake
file(GLOB_RECURSE CUSTOM_UI_SOURCES "${PROJECT_SOURCE_DIR}/ui_custom/*.c")
add_executable(main ${CUSTOM_UI_SOURCES})
```

这样后续只需把 UI 源文件放到 `src/ui_custom/`，不必每次修改底座工程。

## 3. 运行仿真

### 3.1 编译仿真程序

在仿真底座目录执行：

在第一次构建前，务必初始化并更新 Git 子模块（这会检出 `lvgl` 源代码）：

```bash
cd /home/david/Coding/Ansible_RPI_Touch
git submodule update --init --recursive
```

如果你之前已经添加了子模块但目录为空，运行上面命令会填充 `tools/lv_port_pc_vscode/lvgl`。

然后在仿真底座目录进行构建：

```bash
cd /home/david/Coding/Ansible_RPI_Touch/tools/lv_port_pc_vscode
rm -rf build
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

提示：

- 如果遇到类似 “`add_subdirectory(lvgl)` 找不到 CMakeLists.txt” 或 “target lvgl 未构建” 的错误，通常是子模块未初始化导致，请先运行 `git submodule update --init --recursive`。
- 如果遇到 “add_executable cannot create target \"main\" because another target with the same name already exists” 的错误，说明 `CMakeLists.txt` 中同时为底座和自定义 UI 创建了 `main` 目标。项目已修正为将 `ui_custom` 源追加到 `MAIN_SOURCES`（避免重复 `add_executable(main ...)`）。如果你修改过底座 `CMakeLists.txt`，请恢复或合并为单一 `add_executable(main ...)`。

在构建失败时的快速诊断：

```bash
# 查看 lvgl 目录是否存在且包含 CMakeLists.txt
ls -la tools/lv_port_pc_vscode/lvgl | head

# 清理并重新运行 cmake，观察配置输出中的错误信息
rm -rf tools/lv_port_pc_vscode/build
mkdir -p tools/lv_port_pc_vscode/build && cd tools/lv_port_pc_vscode/build
cmake .. 2>&1 | tee cmake_config.log
grep -i error cmake_config.log || true
```

如需，我可以在你确认后远程帮你执行上述构建命令并排查具体错误（注意构建可能会耗时）。

#### 在父仓库使用提供的构建脚本（推荐）

项目包含一个便捷脚本和 override，用于在不修改子模块远端的情况下应用修正并构建：

- 覆盖文件：`tools/overrides/lv_port_pc_vscode/CMakeLists.override`
- 构建脚本：`tools/build_lv_port_pc_vscode.sh`

用法（在项目根执行）：

```bash
# 临时应用 override、构建、然后恢复子模块原始 CMakeLists.txt
./tools/build_lv_port_pc_vscode.sh

# 若希望保留 override（子模块内会被替换，不会自动提交）
./tools/build_lv_port_pc_vscode.sh --keep
```

注意事项：

- 如果子模块 `tools/lv_port_pc_vscode` 中对 `CMakeLists.txt` 已有本地未提交修改，脚本可能无法正确恢复，请先检查并还原：

```bash
git -C tools/lv_port_pc_vscode status --porcelain
git -C tools/lv_port_pc_vscode restore CMakeLists.txt
```

- 若需把修正永久共享给其他人，应 fork 或在子模块上有写权限并向子模块仓库提交；另可通过更新父仓库的 `.gitmodules` 指向你的 fork。


### 3.2 启动仿真窗口

编译成功后，运行：

```bash
./tools/lv_port_pc_vscode/bin/main
```

这会打开 SDL2 窗口，渲染 LVGL 画布。

### 3.3 保持 480x320 逻辑坐标

为了保证 UI 逻辑与树莓派真机一致，仿真程序应当：

- 内部画布尺寸固定为 `480x320`
- 仅在 SDL 窗口层做缩放显示

如果 SDL 窗口太小，可在仿真层增加窗口放大倍率，例如 `2x`，但坐标逻辑仍然保持 `480x320`。

## 4. 触摸与输入仿真

### 4.1 鼠标代替触摸

在 PC 仿真过程中，鼠标左键直接映射为触摸按下，松开映射为触摸释放。

如果 SDL 仿真底座支持手势或多点，则可继续扩展，但当前阶段只需验证单点点击和拖拽即可。

### 4.2 坐标映射原则

- 物理屏幕坐标：`480x320`
- 仿真窗口可放大显示，但 UI 内部坐标保持不变
- 例如：显示窗口 `960x640` 时，鼠标位置应按 `2x` 缩放映射回 LVGL 画布

## 5. 常见问题与调试

### 5.1 SDL2 无法创建窗口

检查是否正确安装 `libsdl2-dev`，并确认当前用户具备 X11/Wayland 显示权限。

### 5.2 字体显示不正常

确认已安装 `libfreetype6-dev`，并在 LVGL 仿真程序中使用正确的字体文件路径。

### 5.3 画面显示不对齐

请确认仿真程序内部画布尺寸为 `480x320`，不要把宿主机窗口的像素尺寸直接当成 LVGL 逻辑尺寸。

## 6. 与当前项目的关系

当前我们只做方案设计与基础界面规划，目标是：

- 在 Ubuntu 上验证 UI 布局和状态机设计
- 让 PC 仿真和真机真屏共享同一套业务设计思路
- 保持 `oled` 代码作为现有业务逻辑参考，暂不迁移

## 7. 后续工作建议

- 当仿真设计验证通过后，再逐步将 `touch` 角色中的 `files/` 目录补齐为实际的 C/LVGL 模块骨架
- 真机阶段再由 `system` 角色负责底层 SPI/I2C 启用与 boot config
- `touch` 角色继续负责 GUI 应用层和 systemd 服务部署

---

本文件仅作为 Ubuntu 上 LVGL 仿真调试的说明，不包含具体编码实现。