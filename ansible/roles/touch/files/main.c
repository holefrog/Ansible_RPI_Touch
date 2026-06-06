#include <stdlib.h>
#include <unistd.h>
#include <lvgl/lvgl.h>
#include "touch_ui.h"

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    lv_init();

    if (!touch_driver_init()) {
        return EXIT_FAILURE;
    }

    touch_ui_init();

    while (1) {
        lv_timer_handler();
        usleep(5000);
    }

    return EXIT_SUCCESS;
}
