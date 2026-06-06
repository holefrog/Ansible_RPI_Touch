cmake_minimum_required(VERSION 3.12)
project(touch_gui C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(SDL2 REQUIRED sdl2)

find_path(LVGL_INCLUDE_DIR lvgl/lvgl.h)
find_library(LVGL_LIBRARY NAMES lvgl)

if(NOT LVGL_INCLUDE_DIR OR NOT LVGL_LIBRARY)
  message(FATAL_ERROR "LVGL not found. Install liblvgl-dev or provide LVGL headers and library in CMAKE_PREFIX_PATH.")
endif()

add_executable(touch_gui main.c touch_ui.c)

target_include_directories(touch_gui PRIVATE ${SDL2_INCLUDE_DIRS} ${LVGL_INCLUDE_DIR})
target_link_libraries(touch_gui PRIVATE ${SDL2_LIBRARIES} ${LVGL_LIBRARY})

set_target_properties(touch_gui PROPERTIES
  C_STANDARD 99
)
