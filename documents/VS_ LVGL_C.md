# 📂 进阶操作：启动 VS Code 补充说明

当你在 Ubuntu 终端中完成了主仓库及子模块的克隆后，必须进入该目录，才能让 VS Code 识别到项目根目录下的 `CMakeLists.txt` 和 `CMakePresets.json` 配置文件。

### 终端连续命令：
```bash
# 1. 进入克隆下来的仿真仓库目录
cd lv_port_pc_vscode

# 2. 在当前目录下直接拉起 VS Code
code .
```

### 💡 为什么必须在 `lv_port_pc_vscode` 目录下执行？
* **让 CMake 插件正常工作**：最新版 VS Code 的 `CMake Tools` 插件极其依赖“工作区根目录”。只有在这个目录下打开，插件才能在底层一眼看到 `CMakePresets.json`（配置预设文件），并自动在编辑器最下方为你准备好 **`Build`**、**`Run`** 按钮以及扫描出 `default` 配置预设。
* **避免路径错乱**：如果在其他父级目录下打开，VS Code 的 C/C++ 智能感知（IntelliSense）可能会找不到 `lvgl/lvgl.h` 等核心头文件，导致满屏报红色的波浪线。
```
