# Touch Role 说明文档

这个角色负责新接入的 Waveshare 480x320 电容触摸屏 UI 栈。
当前阶段以方案设计和最基础界面规划为主，暂时不做编码实现。
Python 业务逻辑仍然保留在现有 OLED 方案中，后续再进行迁移。

## 我们要解决的问题

- 逐步将旧的 OLED 显示层转向原生的 480x320 电容触摸屏界面。
- 使用 C/LVGL 设计高性能、低延迟的触控渲染架构。
- 保持 Python 负责 LMS/AirPlay/Bluetooth 等业务逻辑，不立即迁移所有内容。
- 让 PC 仿真与树莓派真机共享同一套基础业务设计思路。
- 通过轻量 IPC 协议传递状态和图片元数据。

## 角色结构

`ansible/roles/touch` 主要包含：

- `tasks/setup.yml`：安装编译依赖、准备应用目录。
- `tasks/app.yml`：拷贝源代码、生成 CMake 配置、构建二进制。
- `tasks/service.yml`：创建用户级 systemd 服务并启动 GUI。
- `templates/touch_gui.service.j2`：运行触控 GUI 的 systemd 单元模板。
- `files/`：放置 C 语言 UI 引擎、驱动接口、模块骨架等源码文件。

## 准备工作

### 1. 硬件准备

- 确认树莓派已接好 Waveshare 480x320 屏幕和 WM8960 声卡的引脚。
- 保证背光从 BCM13 输出，避免 BCM18 与 I2S 时钟冲突。
- 启用 SPI 和软件 I2C，确保触摸控制器与显示驱动同时可用。

### 2. 开发准备

- 在 PC 宿主机中构建 SDL2 仿真环境，验证 LVGL 布局和触控逻辑设计。
- 将 UI 业务代码与底层驱动分离，避免仿真和真机复用时发生改动。
- 先定义好 Python 与 C 之间的 IPC 协议，再进行界面设计。

### 3. 协议准备

我们将采用轻量 `KEY:VALUE` 文本协议，管道只传状态和元数据，不传大对象。

推荐字段：

- `STATE:IDLE` / `STATE:PLAYING` / `STATE:PAUSED`
- `TITLE:...`
- `ARTIST:...`
- `ALBUM:...`
- `PROGRESS:0-100`
- `VOLUME:0-100`
- `IMAGE_PATH:/tmp/player_cover.rgb565`
- `IMAGE_WIDTH:240`
- `IMAGE_HEIGHT:240`
- `IMAGE_FORMAT:RGB565`
- `IMAGE_VERSION:42`

这样可以保持管道轻量，并把图片传递交给文件/共享缓冲区方式。

## 我们要做的设计步骤

### 步骤 1：定义 IPC 协议

- 统一 Python 发给 C 的消息格式。
- 约定状态、文本和图片元数据字段。
- 约定 C 端如何解析、如何触发界面刷新。

### 步骤 2：设计 C 语言模块骨架

将触控 UI 设计为以下 5 个模块：

1. `drv_display`：显示抽象层，支持 SDL2 仿真和 framebuffer 真机。
2. `drv_input`：输入事件层，负责触摸事件读取与坐标映射。
3. `ui_player`：纯业务 UI 渲染层，负责布局和状态显示。
4. `ipc_manager`：IPC 管理层，负责管道创建、消息解析和缓存。
5. `main`：主循环与状态机层，负责初始化、调度和状态切换。

### 步骤 3：先在 PC 仿真上验证设计

- 使用 SDL2 模拟 480x320 屏幕。
- 验证 UI 设计、状态机和管道协议是否合理。
- 确保设计思路可移植到真机。

### 步骤 4：准备真机部署方案

- 用 Ansible 规划源码与构建脚本下发到树莓派。
- 规划 `touch` role 启用 SPI/I2C、构建触控 GUI、配置 systemd 启动。
- 规划验证 `touch_gui.service` 正常运行的检查点。

### 步骤 5：保留开机即显扩展方向

- 后续可以在 `touch` 角色外补一个早期 boot renderer。
- 该程序直接写 `/dev/fb1` 或使用 fbcon 映射来快速显示开机画面。
- 这部分不依赖 LVGL，只负责“开机第一屏”；之后再启动 LVGL GUI 进程接管。

## 为什么这样做

- **业务层与显示层解耦**：Python 负责业务，C 负责显示。
- **真机与仿真复用**：同一套 UI 代码可以在 PC 和 Raspberry Pi 上共享。
- **管道轻量且可扩展**：文本协议易调试，图片传递通过文件路径或共享缓存。
- **模块化清晰**：5 个模块分工明确，后续维护和扩展更简单。

## 目前我们的目标

- 先把 `touch` role 的目录结构和 C 模块设计搭好。
- 再明确 IPC 协议，设计 Python 发给 C 的状态数据流。
- 然后完成最基本的 LVGL 界面设计和 480x320 布局规划。
- 当前阶段不做编码，保持 OLED 业务逻辑原样不动。
- 后续再把设计方案迁移到真机部署和开机显示逻辑。

## 目录对应关系

- `ansible/roles/touch/tasks/`：触控角色的部署逻辑。
- `ansible/roles/touch/templates/`：service 模板。
- `ansible/roles/touch/files/`：未来放 C 代码、驱动接口、CMakeLists 等。
- `ansible/roles/touch/README.md`：本模块说明。

---

本 README 作为 `touch` 角色的实施指南，后续开发时应以此为准。
如果你同意，我可以继续把这个 README 再补成“真正的 5 个模块文件清单”并写出每个模块的具体接口。