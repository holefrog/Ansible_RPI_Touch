## 💻 宿主机仿真开发环境配置 (Ubuntu PC Simulator)

为了避免在树莓派真机上盲调 SPI 显存与触控总线导致开发效率极低，本项目推荐在 Ubuntu 宿主机上使用 VS Code 配合 LVGL 仿真器进行 1:1 分辨率的界面开发、排版微调与断点调试。在 PC 端通过鼠标捕捉模拟的 UI 业务代码，可 **100% 零修改** 移植到树莓派真机上。

---

### 🛠️ 第一步：安装 Ubuntu 系统依赖

在 Ubuntu 终端（Terminal）中运行以下一键命令，安装 GCC 编译器、CMake 构建工具以及 LVGL 仿真器必须的 **SDL2** 图形渲染驱动库：

```bash
# 更新 apt 软件源
sudo apt update

# 核心工具补装：安装基础编译工具链、C/C++ 构建环境及 Git
sudo apt install -y build-essential cmake git

# 安装 SDL2 依赖开发库（模拟器利用它在 Ubuntu 桌面弹窗渲染像素）
sudo apt install -y libsdl2-dev
```

---

### 📂 第二步：克隆官方 Linux 仿真项目

官方为 Linux/VS Code 环境维护了一个基于 CMake 的独立仿真仓库。请务必使用带 `--recursive` 参数的 Git 命令克隆，切勿直接下载 GitHub 的 ZIP 压缩包（否则嵌套的核心核心子模块文件夹会为空）：

```bash
# 一键克隆主仓库及嵌套的 lvgl 核心子模块
git clone --recursive https://github.com/lvgl/lv_port_pc_vscode.git
```

---

### 🚀 第三步：在 VS Code 中配置与首次运行（新版插件适配）

1. **进入工作区并打开项目**：在终端中必须通过以下命令进入克隆下来的项目目录，再拉起 VS Code，以便插件能正确识别根目录下的配置文件：
   ```bash
   cd lv_port_pc_vscode
   code .
   ```
2. **安装 VS Code 必备扩展插件**（在左侧 Extensions 市场搜索安装）：
   * **`C/C++`** (Microsoft 官方插件，提供代码高亮与断点调试)
   * **`CMake Tools`** (Microsoft 官方插件，提供一键构建管理)
3. **选择配置预设（最新版 VS Code 关键操作）**：
   * 打开项目后，新版 CMake 插件会自动扫描项目根目录下的 `CMakePresets.json`。
   * 按下键盘快捷键 **`Ctrl + Shift + P`**，键入并选择 **`CMake: Select Configure Preset`**（代替了老版本的 Select a Kit）。
   * 在弹出的列表中选择本地的 Linux 预设或 **`default`** 构建链。
   * 接着再次按 **`Ctrl + Shift + P`**，键入并选择 **`CMake: Select Build Preset`**，同样选择 **`default`**。
4. **一键编译与仿真**：
   * 点击 VS Code 最下方状态栏的 **`Build`** 按钮（或按键盘 `F7`），CMake 会自动拉起本地 GCC 开始编译。
   * 编译完成后，点击最下方状态栏的 **小飞虫图标/Debug** 或者 **右三角/Run** 按钮（或直接按 `F5`），Ubuntu 桌面上就会立刻弹出一个丝滑的 LVGL 官方演示窗口！

---

### 📝 第四步：适配微雪 3.5 寸播放器屏幕分辨率

由于你的物理目标屏幕是 480x320，为了在 Ubuntu 电脑上获得 1:1 的真实排版像素，必须修改配置文件。

#### 1. 修改分辨率宏
在左侧文件树中找到并打开 **`lv_conf.h`**（或仿真驱动配置对应的头文件，通常在根目录或 `main.c` 附近）。找到用于控制模拟器物理像素的宏定义，修改为：

```c
/* 调整模拟器横屏物理分辨率为 480 x 320 */
#define SDL_HOR_RES     480
#define SDL_VER_RES     320

/* 💡 小提示：如果觉得 Ubuntu 电脑屏幕分辨率太高，导致 480x320 窗口极小
   可以寻找 SDL_ZOOM 宏，将其设为 2，即可在 PC 端等比例放大窗口显示，不影响代码底层坐标！ */
```

#### 2. 注入你的多媒体播放器业务 UI 代码
打开项目根目录下的 **`main.c`**，找到 `main` 函数，将其中的官方 Demo 注释掉，换上你纯 C 语言构建的 LMS 播放器 UI入口：

```c
#include "lvgl/lvgl.h"

/* 1. 声明并编写你的多媒体播放器简易 UI 骨架 */
void my_player_ui_init(void) {
    /* 将主屏幕背景初始化为高级深色调 */
    lv_obj_t * scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, lv_color_make(20, 20, 20), 0);

    /* 创建文字标签，指示多音源播放器初始化状态 */
    lv_obj_t * label = lv_label_create(scr);
    lv_label_set_text(label, "My LMS Player \nInitializing Stream...");
    lv_obj_set_style_text_color(label, lv_color_make(0, 255, 0), 0); /* 经典荧光绿 */
    lv_obj_align(label, LV_ALIGN_CENTER, 0, 0);
}

int main(int argc, char **argv) {
    /* ... 保持原有的包含 lv_init() 和 SDL 驱动初始化的前置代码不变 ... */

    /* 注释掉原有的官方示例 */
    // lv_demo_widgets();

    /* 2. 调用你自己的播放器首屏代码 */
    my_player_ui_init();

    /* ... 保持原有的 while(1) 任务处理器及时间心跳主循环不变 ... */
    while(1) {
        lv_timer_handler();
        usleep(5000);
    }
    return 0;
}
```

再次点击底部的 **`Build`** 并按 **`F5`** 启动，你便能在电脑上以极高的效率打断点、肉眼排查刷新或指针越界错误。UI 在 Ubuntu 上彻底调顺后，这些 C 文件即可信心满满地直接分发至树莓派真机编译运行！
```