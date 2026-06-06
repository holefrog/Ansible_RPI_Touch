# 💻 宿主机开发、解耦管理与 Python 联调配置指南 (Ubuntu PC Simulator)

为了避免在树莓派真机上盲调 SPI 显存与触控总线导致开发效率极低，本项目推荐在 Ubuntu 宿主机上使用 VS Code 配合 LVGL 仿真器进行界面开发、排版微调与断点调试。在 PC 端通过鼠标左键（自适应映射电容手势坐标）调顺的纯 C UI 业务代码，可 **100% 零修改** 直接分发至树莓派真机上运行。

---

### 📂 第一步：自有项目目录演进树结构

为了不让第三方的仿真底座代码污染你的主项目仓库，我们将你手写的纯 C UI 源码放在独立的业务文件夹下，将官方仿真底座作为 **Git 子模块 (Submodule)** 完整克隆到项目独立工具目录下。

请在你的主项目 **`Ansible_RPI_MediaPlayer`** 根目录下运行以下命令建立目录拓扑：
```bash
# 1. 创建存放你自定义纯 C 图形界面的业务文件夹
mkdir -p src/ui_custom

# 2. 将官方带有 VS Code 配置文件的 CMake 仿真底座完全引入为子模块
git submodule add https://github.com/lvgl/lv_port_pc_vscode.git tools/lv_port_pc_vscode
```

#### 📌 本地 Git 仓库演进后的理想拓扑：
```text
Ansible_RPI_MediaPlayer/ (你的自有项目根目录)
├── ansible/               # 你的 Ansible 自动化部署剧本
├── src/
│   ├── main_core.py       # 你的 Python 多媒体核心控制主程序
│   └── ui_custom/         # 📁 这里存放你手写的所有 C 语言 UI 界面代码
│       ├── my_player_ui.c # 歌曲名接收、切歌热区划分等纯 C 布局逻辑
│       └── my_player_ui.h
└── tools/
    └── lv_port_pc_vscode/ # 📁 官方仿真底座子模块（充当模拟器外壳）
        ├── main.c         # 我们将在此文件中引用并拉起项目自定义的 UI
        └── CMakeLists.txt # 需要覆盖它以便自动扫描外部的 ui_custom 目录
```

---

### 🛠️ 第二步：建立软链接与覆盖 CMake 自动化扫描

为了让底座能跨目录编译你的代码，且不需要每次新增 C 文件都手动修改编译脚本，我们使用 **软链接投影** 与 **CMake 递归扫描** 的高阶打法。

在项目根目录下连续执行以下命令：

#### 1. 建立软链接（投影）
```bash
ln -s ../../src/ui_custom tools/lv_port_pc_vscode/ui_custom
```

#### 2. 完全覆盖底座的 `CMakeLists.txt`
使用以下配置**完全覆盖** `tools/lv_port_pc_vscode/CMakeLists.txt` 的内容：
```cmake
cmake_minimum_required(VERSION 3.12)
project(lvgl_pc_simulator C CXX)

set(CMAKE_C_STANDARD 99)
set(CMAKE_CXX_STANDARD 11)

# 1. 查找系统的 SDL2 依赖（用于宿主机弹窗渲染与鼠标捕捉）
find_package(SDL2 REQUIRED)

# 2. 包含官方模拟器底座自带的核心构建逻辑
include(${PROJECT_SOURCE_DIR}/lvgl/env_init.cmake)

# 3. 🔥 全自动扫描你在自有项目中手写的 C UI 源码
# 自动递归拉取刚才建立软链接的 ui_custom 文件夹下所有的 .c 文件
file(GLOB_RECURSE CUSTOM_UI_SOURCES 
     "${PROJECT_SOURCE_DIR}/ui_custom/*.c"
     "${PROJECT_SOURCE_DIR}/main.c"
)

# 4. 将底座的头文件路径、LVGL 核心路径和你自己的 ui_custom 路径暴露给编译器
include_directories(
    ${PROJECT_SOURCE_DIR}
    ${PROJECT_SOURCE_DIR}/ui_custom
    ${SDL2_INCLUDE_DIRS}
)

# 5. 生成 PC 端最终的二进制仿真可执行文件
add_executable(main ${CUSTOM_UI_SOURCES})

# 6. 链接 LVGL 核心静态库与 SDL2 图形驱动库
target_link_libraries(main lvgl::lvgl lvgl::drivers ${SDL2_LIBRARIES})
```

---

### 🚀 第三步：在 VS Code 中点亮图形化构建栏（最新版状态栏直调法）

1. **精确进入工作区**：在 Ubuntu 终端中必须切入底座外壳路径拉起 VS Code，以便最新的 CMake Tools 插件能够瞬间解析到顶层工程结构：
   ```bash
   cd tools/lv_port_pc_vscode
   code .
   ```
2. **确认插件就绪**：确保 VS Code 内已经激活安装了官方的 **`C/C++`** 和 **`CMake Tools`** 扩展插件。
3. **激活编译器选择**：
   * 正确进入目录后，VS Code 最下方的**蓝色状态栏（Status Bar）**右侧会最先直接亮起一个带有 **`右三角 ➡️ Run`** 的快捷配置按钮。
   * 用鼠标直接点击底部状态栏的那个 **`➡️ Run`** 按钮。
   * 此时，由于插件的延迟懒加载（Lazy Load）机制，VS Code 屏幕正上方中央会弹出一个本地编译器（Kit）扫描列表。直接在列表中鼠标点击选择你本地的 **`GCC`**（例如 `/usr/bin/gcc` 或 `GCC x86_64-linux-gnu`）。
4. **全自动编译与跑通**：
   * 编译器选定后，底部状态栏会瞬间多出 **`齿轮 ⚙️ Build`** 和 **`小飞虫 🪲 Debug`** 图标。
   * 插件会在后台全自动调通 GCC 完成项目的首次构建并直接弹窗点亮！

---

### 📝 第四步：适配 3.5 寸硬件物理画布与 1080p 屏幕等比放大

最新版仿真底座中去除了头文件中的 `SDL_HOR_RES` 分辨率宏，改为在 `main()` 中动态创建。为了让它 1:1 契合微雪 3.5 寸硬件（480x320），同时防止在 1080p 显示器上因物理分辨率太高导致画面像“豆腐块”一样小，我们直接对 **`tools/lv_port_pc_vscode/main.c`** 的初始化部分进行重写：

```c
#include "lvgl/lvgl.h"
#include "ui_custom/my_player_ui.h" // 🛠️ 跨目录安全引用你自有仓库的 UI 核心头文件
#include <unistd.h>

int main(int argc, char **argv) {
    /* 初始化 LVGL 图形库核心 */
    lv_init();

    /* 1. 画布物理对齐：直接硬编码数字 480 和 320 创建标准的 3.5 寸硬件像素视口 */
    /* 这能保证你在 C 代码里写的任何绝对像素坐标，移植到树莓派真机时排版 100% 零错位 */
    lv_display_t * display = lv_sdl_window_create(480, 320);
    if (display == NULL) {
        return -1;
    }

    /* 2. 🔥 视野拯救：仅在 PC 宿主机上等比例放大 2 倍显示 (可视窗口变为 960x640) */
    /* 这一步属于 SDL 窗口拉伸，完全不会对你的 LVGL 坐标逻辑数字造成任何变动污染 */
    lv_sdl_window_set_zoom(display, 2);

    /* 初始化本地鼠标驱动：LVGL 会自动将放大 2 倍后的鼠标坐标等比例除以 2 映射回去 */
    /* 你的 PC 鼠标点击和拖拽手势，完全 1:1 等价于树莓派真机的电容触摸事件 */
    lv_sdl_mouse_create();

    /* 注释掉原有的官方示例 Demo */
    // lv_demo_widgets();

    /* 3. 调用放在你自己 src/ui_custom/ 目录下的多媒体播放器界面入口 */
    my_player_ui_init();

    /* 进入 LVGL 任务处理器主循环 */
    while(1) {
        lv_timer_handler();
        usleep(5000); /* 5毫秒标准时间心跳控制 */
    }
    return 0;
}
```

---

## 🔄 第四步：与 Python 媒体主程序进行异步管道 (FIFO) 联调

为了让 C 语言的高速图形渲染能力能与你的 Python 媒体主框架共存，联调推荐采用**多进程管道解耦法**：

### 1. 纯 C 业务层异步读取：编写 `src/ui_custom/my_player_ui.c`
```c
#include "my_player_ui.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>

static lv_obj_t * song_label;
static int pipe_fd = -1;

void my_player_ui_init(void) {
    /* 用 LVGL 构建好你的 480x320 播放器歌曲名显示标签 */
    song_label = lv_label_create(lv_scr_act());
    lv_label_set_text(song_label, "Waiting For Python...");
    lv_obj_align(song_label, LV_ALIGN_CENTER, 0, 0);

    /* 在本地文件系统创建命名管道 */
    const char * pipe_path = "/tmp/player_ui_pipe";
    mkfifo(pipe_path, 0666);
    
    /* 以非阻塞 O_RDONLY 模式打开管道，防止 C 进程因没有新歌名而卡死 UI 渲染 */
    pipe_fd = open(pipe_path, O_RDONLY | O_NONBLOCK);

    /* 向 LVGL 注册一个后台定时器，每 100ms 异步读取一次管道 */
    lv_timer_create(check_pipe_task, 100, NULL);
}

void check_pipe_task(lv_timer_t * timer) {
    if (pipe_fd < 0) return;

    char buffer[128];
    memset(buffer, 0, sizeof(buffer));
    
    if (read(pipe_fd, buffer, sizeof(buffer) - 1) > 0) {
        if (strncmp(buffer, "TITLE:", 6) == 0) {
            lv_label_set_text(song_label, buffer + 6); // 刷新动态歌名
        }
    }
}
```

### 2. Python 业务端状态推流：编写 `src/main_core.py`
你的 Python 进程可以自由运行在自有目录下，负责通过 D-Bus 监听 AirPlay 2 或蓝牙流，一旦发现歌曲变动，立刻通过流向管道推流：
```python
import os
import time

PIPE_PATH = "/tmp/player_ui_pipe"

def send_to_c_ui(song_title):
    """将 Python 监听到多媒体数据高速推给 C 进程"""
    if not os.path.exists(PIPE_PATH):
        return
    try:
        with open(PIPE_PATH, 'w') as pipe:
            pipe.write(f"TITLE:{song_title}")
            pipe.flush()
    except Exception as e:
        print(f"Pipe write error: {e}")

if __name__ == "__main__":
    print("Python Core State Machine Started...")
    time.sleep(2)
    send_to_c_ui("Pink Floyd - Time")
```

### 🏁 终极同步联调
在 Ubuntu 宿主机上分别打开两个终端：
* **终端 1**：在 `tools/lv_port_pc_vscode` 下直接点击 VS Code 状态栏的 **`Run`** 按钮，等比例拉伸的彩屏模拟器亮起，等待流数据。
* **终端 2**：在项目根目录下执行 `python3 src/main_core.py`。

终端 2 回车敲下的瞬间，终端 1 的 LVGL 仿真器画布组件会直接完成流数据的异步刷新！
```