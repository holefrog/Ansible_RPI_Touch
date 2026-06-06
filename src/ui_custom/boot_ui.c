#include "boot_ui.h"
#include "lvgl/lvgl.h"

/* A simple boot screen that mimics the provided image: progress bar at top,
   a boxed list of status lines with colored tags on the left.
   This function overrides lv_demo_widgets() from the demos so no main.c change
   is required. */

void lv_demo_widgets(void)
{
    /* Use the active screen */
    lv_obj_t * scr = lv_scr_act();
    lv_obj_clean(scr);

    /* Ensure background is dark */
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x0B0B0B), 0);

    /* Progress bar at top */
    lv_obj_t * cont = lv_obj_create(scr);
    lv_obj_set_size(cont, lv_pct(100), 40);
    lv_obj_align(cont, LV_ALIGN_TOP_MID, 0, 8);
    lv_obj_set_style_radius(cont, 4, 0);
    lv_obj_set_style_bg_color(cont, lv_color_hex(0x111111), 0);
    lv_obj_set_style_border_width(cont, 1, 0);
    lv_obj_set_style_border_color(cont, lv_color_hex(0x2E7D32), 0);

    lv_obj_t * bar_bg = lv_obj_create(cont);
    lv_obj_set_size(bar_bg, lv_pct(95), 8);
    lv_obj_align(bar_bg, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(bar_bg, lv_color_hex(0x222222), 0);
    lv_obj_set_style_radius(bar_bg, 3, 0);

    lv_obj_t * bar = lv_bar_create(bar_bg);
    lv_obj_set_size(bar, lv_pct(100), lv_pct(100));
    lv_bar_set_range(bar, 0, 100);
    lv_bar_set_value(bar, 62, LV_ANIM_OFF);
    lv_obj_set_style_bg_opa(bar, LV_OPA_TRANSP, 0);
    lv_obj_set_style_bg_color(bar, lv_color_hex(0x2E7D32), LV_PART_INDICATOR);
    lv_obj_set_style_radius(bar, 3, LV_PART_INDICATOR);

    /* Main boxed area for status messages */
    lv_obj_t * box = lv_obj_create(scr);
    lv_obj_set_size(box, lv_pct(92), lv_pct(70));
    lv_obj_align(box, LV_ALIGN_CENTER, 0, 20);
    lv_obj_set_style_radius(box, 6, 0);
    lv_obj_set_style_bg_color(box, lv_color_hex(0x071618), 0);
    lv_obj_set_style_border_width(box, 1, 0);
    lv_obj_set_style_border_color(box, lv_color_hex(0x1F8A70), 0);

    /* Create a column layout inside box */
    lv_obj_t * col = lv_obj_create(box);
    lv_obj_remove_style_all(col);
    lv_obj_set_size(col, lv_pct(100), lv_pct(100));
    lv_obj_set_layout(col, LV_LAYOUT_COLUMN_MID);
    lv_obj_set_scrollbar_mode(col, LV_SCROLLBAR_MODE_OFF);

    const char * lines[] = {
        "Mounted /boot/efi",
        "SPI LCD driver [waveshare35c] attached.",
        "Start systemd-modules-load.service",
        "Memory: 3.8GB RAM (ARMv8)",
        "Local Network: rpi-core.local",
        "SSH server: Active on port 22.",
        "DHCP lease: 192.168.1.100",
        "Bluetooth service started.",
        "Shairport-Sync service: Active.",
        "GPIO pins initialized [BCM21,BCM22]",
        "Reached target Multi-User System."
    };
    const int n = sizeof(lines)/sizeof(lines[0]);

    for(int i=0;i<n;i++) {
        lv_obj_t * row = lv_obj_create(col);
        lv_obj_set_width(row, lv_pct(100));
        lv_obj_set_height(row, 26);
        lv_obj_set_flex_flow(row, LV_FLEX_FLOW_ROW);
        lv_obj_set_style_pad_all(row, 6, 0);
        lv_obj_set_style_bg_opa(row, LV_OPA_TRANSP, 0);

        /* tag box */
        lv_obj_t * tag = lv_obj_create(row);
        lv_obj_set_size(tag, 34, 20);
        lv_obj_set_style_radius(tag, 3, 0);
        if(i==0 || i==2 || i==4 || i==6 || i==8 || i==9 || i==10) {
            lv_obj_set_style_bg_color(tag, lv_color_hex(0x2E7D32), 0); // OK green
        } else {
            lv_obj_set_style_bg_color(tag, lv_color_hex(0x1976D2), 0); // INFO blue
        }
        lv_obj_t * tag_label = lv_label_create(tag);
        lv_label_set_text(tag_label, (i%2==0)?"OK":"INFO");
        lv_obj_center(tag_label);
        lv_obj_set_style_text_color(tag_label, lv_color_hex(0x000000), 0);

        /* message label */
        lv_obj_t * lbl = lv_label_create(row);
        lv_label_set_text(lbl, lines[i]);
        lv_obj_set_style_text_color(lbl, lv_color_hex(0xE0F7FA), 0);
        lv_obj_set_style_text_font(lbl, &lv_font_montserrat_12, 0);
        lv_obj_align(lbl, LV_ALIGN_LEFT_MID, 10, 0);
    }
}
