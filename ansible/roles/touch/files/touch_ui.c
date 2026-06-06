#include <lvgl/lvgl.h>
#include "touch_ui.h"

static lv_obj_t * title_label;

bool touch_driver_init(void) {
    /* TODO: replace with real driver initialization for SPI + touch controller */
    return true;
}

void touch_ui_init(void) {
    lv_obj_t * screen = lv_scr_act();
    lv_obj_clean(screen);

    title_label = lv_label_create(screen);
    lv_label_set_text(title_label, "Waveshare 480x320 Touch GUI");
    lv_obj_align(title_label, LV_ALIGN_TOP_MID, 0, 20);

    lv_obj_t * info = lv_label_create(screen);
    lv_label_set_text(info, "LVGL C application running on Raspberry Pi");
    lv_obj_align(info, LV_ALIGN_CENTER, 0, 0);

    lv_obj_t * hint = lv_label_create(screen);
    lv_label_set_text(hint, "Touch the screen to interact.");
    lv_obj_align(hint, LV_ALIGN_BOTTOM_MID, 0, -20);
}
