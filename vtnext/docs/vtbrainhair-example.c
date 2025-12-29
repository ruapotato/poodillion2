/*
 * vtbrainhair - Example Kernel Client Implementation
 *
 * This shows how to integrate vtbrainhair into an OS kernel
 * for serial-based desktop graphics.
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ============================================================
 * PROTOCOL CONSTANTS
 * ============================================================ */

#define VTBH_STX        0x02
#define VTBH_ETX        0x03

/* Command types (client -> server) */
#define VTBH_CMD_HELLO      'A'
#define VTBH_CMD_CREATE     'C'
#define VTBH_CMD_DESTROY    'D'
#define VTBH_CMD_UPDATE     'E'
#define VTBH_CMD_IMAGE      'L'
#define VTBH_CMD_BATCH      'R'
#define VTBH_CMD_SYNC       'S'

/* Response types (server -> client) */
#define VTBH_RSP_WELCOME    'a'
#define VTBH_RSP_OK         'b'
#define VTBH_RSP_ERROR      'c'
#define VTBH_RSP_EVENT      'd'
#define VTBH_RSP_SYNC_ACK   'e'

/* Object types */
#define VTBH_OBJ_WINDOW     0x01
#define VTBH_OBJ_PANEL      0x02
#define VTBH_OBJ_TEXT       0x03
#define VTBH_OBJ_RECT       0x04
#define VTBH_OBJ_LINE       0x05
#define VTBH_OBJ_CIRCLE     0x06
#define VTBH_OBJ_ARC        0x07
#define VTBH_OBJ_POLYGON    0x08
#define VTBH_OBJ_IMAGE      0x0A

/* Property IDs */
#define VTBH_PROP_X             0x01
#define VTBH_PROP_Y             0x02
#define VTBH_PROP_WIDTH         0x03
#define VTBH_PROP_HEIGHT        0x04
#define VTBH_PROP_VISIBLE       0x05
#define VTBH_PROP_OPACITY       0x06
#define VTBH_PROP_FILL_COLOR    0x10
#define VTBH_PROP_BORDER_COLOR  0x11
#define VTBH_PROP_TEXT          0x20
#define VTBH_PROP_FONT_SIZE     0x22
#define VTBH_PROP_TEXT_COLOR    0x23

/* Event types */
#define VTBH_EVT_KEY_DOWN       0x01
#define VTBH_EVT_KEY_UP         0x02
#define VTBH_EVT_MOUSE_MOVE     0x10
#define VTBH_EVT_MOUSE_DOWN     0x11
#define VTBH_EVT_MOUSE_UP       0x12
#define VTBH_EVT_SCROLL         0x13
#define VTBH_EVT_RESIZE         0x30

/* Modifier keys */
#define VTBH_MOD_SHIFT  0x01
#define VTBH_MOD_CTRL   0x02
#define VTBH_MOD_ALT    0x04
#define VTBH_MOD_META   0x08

/* Colors (RGB565) */
#define VTBH_COLOR_WHITE    0xFFFF
#define VTBH_COLOR_BLACK    0x0000
#define VTBH_COLOR_RED      0xF800
#define VTBH_COLOR_GREEN    0x07E0
#define VTBH_COLOR_BLUE     0x001F
#define VTBH_COLOR_GRAY     0x8410

#define VTBH_RGB565(r, g, b) \
    ((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | (((b) & 0xF8) >> 3))

/* ============================================================
 * DATA STRUCTURES
 * ============================================================ */

struct vtbh_event {
    uint8_t type;
    uint32_t timestamp;
    union {
        struct {
            uint16_t keycode;
            uint8_t modifiers;
            uint32_t character;
        } key;
        struct {
            int16_t x, y;
            uint8_t buttons;
            uint8_t button;
            uint8_t modifiers;
        } mouse;
        struct {
            int16_t x, y;
            int8_t dx, dy;
        } scroll;
        struct {
            uint16_t width, height;
        } resize;
    };
};

struct vtbh_device {
    /* Serial port (platform-specific) */
    void *serial_handle;

    /* Protocol state */
    uint32_t next_object_id;
    uint32_t next_sync_id;
    uint16_t screen_width;
    uint16_t screen_height;
    bool connected;

    /* Buffers */
    uint8_t tx_buffer[4096];
    size_t tx_len;
    uint8_t rx_buffer[4096];
    size_t rx_len;

    /* Event queue */
    struct vtbh_event event_queue[64];
    size_t event_head;
    size_t event_tail;

    /* Callbacks (optional) */
    void (*on_event)(struct vtbh_device *dev, struct vtbh_event *evt);
};

/* ============================================================
 * BASE64 ENCODING
 * ============================================================ */

static const char b64_table[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static size_t b64_encode(const uint8_t *src, size_t len, char *dst) {
    size_t i, j;
    for (i = 0, j = 0; i < len; i += 3) {
        uint32_t v = src[i] << 16;
        if (i + 1 < len) v |= src[i + 1] << 8;
        if (i + 2 < len) v |= src[i + 2];

        dst[j++] = b64_table[(v >> 18) & 0x3F];
        dst[j++] = b64_table[(v >> 12) & 0x3F];
        dst[j++] = (i + 1 < len) ? b64_table[(v >> 6) & 0x3F] : '=';
        dst[j++] = (i + 2 < len) ? b64_table[v & 0x3F] : '=';
    }
    return j;
}

static int b64_decode_char(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

static size_t b64_decode(const char *src, size_t len, uint8_t *dst) {
    size_t i, j;
    for (i = 0, j = 0; i < len; i += 4) {
        int a = b64_decode_char(src[i]);
        int b = b64_decode_char(src[i + 1]);
        int c = (src[i + 2] != '=') ? b64_decode_char(src[i + 2]) : 0;
        int d = (src[i + 3] != '=') ? b64_decode_char(src[i + 3]) : 0;

        if (a < 0 || b < 0) break;

        dst[j++] = (a << 2) | (b >> 4);
        if (src[i + 2] != '=') dst[j++] = ((b & 0x0F) << 4) | (c >> 2);
        if (src[i + 3] != '=') dst[j++] = ((c & 0x03) << 6) | d;
    }
    return j;
}

/* ============================================================
 * CRC-8
 * ============================================================ */

static uint8_t crc8(const uint8_t *data, size_t len) {
    uint8_t crc = 0;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1;
        }
    }
    return crc;
}

/* ============================================================
 * PACKET BUILDING
 * ============================================================ */

/* Platform-specific: implement these for your OS */
extern int serial_write(void *handle, const void *data, size_t len);
extern int serial_read(void *handle, void *data, size_t len);

static int vtbh_send_packet(struct vtbh_device *dev, char type,
                            const uint8_t *payload, size_t payload_len) {
    /* Calculate sizes */
    size_t b64_payload_len = ((payload_len + 2) / 3) * 4;
    size_t packet_len = 1 + 1 + 2 + b64_payload_len + 2 + 1;

    if (packet_len > sizeof(dev->tx_buffer)) {
        return -1; /* Payload too large */
    }

    uint8_t *p = dev->tx_buffer;

    /* STX */
    *p++ = VTBH_STX;

    /* Type */
    *p++ = type;

    /* Length (base64 encoded, 2 chars for 0-4095) */
    uint8_t len_bytes[2] = { payload_len >> 8, payload_len & 0xFF };
    char len_b64[4];
    b64_encode(len_bytes, 2, len_b64);
    *p++ = len_b64[0];
    *p++ = len_b64[1];
    /* Note: simplified - full impl needs proper 2-char base64 for 12 bits */

    /* Payload (base64) */
    if (payload_len > 0) {
        p += b64_encode(payload, payload_len, (char *)p);
    }

    /* CRC (base64) */
    uint8_t crc = crc8(payload, payload_len);
    char crc_b64[4];
    b64_encode(&crc, 1, crc_b64);
    *p++ = crc_b64[0];
    *p++ = crc_b64[1];

    /* ETX */
    *p++ = VTBH_ETX;

    dev->tx_len = p - dev->tx_buffer;
    return serial_write(dev->serial_handle, dev->tx_buffer, dev->tx_len);
}

/* ============================================================
 * PAYLOAD BUILDING HELPERS
 * ============================================================ */

struct vtbh_builder {
    uint8_t buffer[2048];
    size_t len;
};

static void vtbh_builder_init(struct vtbh_builder *b) {
    b->len = 0;
}

static void vtbh_builder_u8(struct vtbh_builder *b, uint8_t v) {
    b->buffer[b->len++] = v;
}

static void vtbh_builder_u16(struct vtbh_builder *b, uint16_t v) {
    b->buffer[b->len++] = v & 0xFF;
    b->buffer[b->len++] = (v >> 8) & 0xFF;
}

static void vtbh_builder_i16(struct vtbh_builder *b, int16_t v) {
    vtbh_builder_u16(b, (uint16_t)v);
}

static void vtbh_builder_u32(struct vtbh_builder *b, uint32_t v) {
    b->buffer[b->len++] = v & 0xFF;
    b->buffer[b->len++] = (v >> 8) & 0xFF;
    b->buffer[b->len++] = (v >> 16) & 0xFF;
    b->buffer[b->len++] = (v >> 24) & 0xFF;
}

static void vtbh_builder_str(struct vtbh_builder *b, const char *s) {
    size_t len = 0;
    while (s[len]) len++;
    vtbh_builder_u8(b, len);
    for (size_t i = 0; i < len; i++) {
        vtbh_builder_u8(b, s[i]);
    }
}

/* ============================================================
 * HIGH-LEVEL API
 * ============================================================ */

int vtbh_init(struct vtbh_device *dev, void *serial_handle) {
    dev->serial_handle = serial_handle;
    dev->next_object_id = 1;
    dev->next_sync_id = 1;
    dev->connected = false;
    dev->tx_len = 0;
    dev->rx_len = 0;
    dev->event_head = 0;
    dev->event_tail = 0;
    dev->on_event = NULL;
    return 0;
}

int vtbh_connect(struct vtbh_device *dev, const char *name) {
    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u8(&b, 1);              /* version */
    vtbh_builder_u16(&b, 0x0003);        /* flags: binary + compress */
    vtbh_builder_u16(&b, 1920);          /* max width */
    vtbh_builder_u16(&b, 1080);          /* max height */
    vtbh_builder_str(&b, name);          /* client name */

    return vtbh_send_packet(dev, VTBH_CMD_HELLO, b.buffer, b.len);
}

uint32_t vtbh_create_window(struct vtbh_device *dev, int16_t x, int16_t y,
                            uint16_t w, uint16_t h, const char *title) {
    uint32_t oid = dev->next_object_id++;

    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);           /* object id */
    vtbh_builder_u32(&b, 0);             /* parent (root) */
    vtbh_builder_u8(&b, VTBH_OBJ_WINDOW);
    vtbh_builder_i16(&b, x);
    vtbh_builder_i16(&b, y);
    vtbh_builder_u16(&b, w);
    vtbh_builder_u16(&b, h);
    vtbh_builder_u16(&b, 0);             /* flags */
    vtbh_builder_str(&b, title);         /* window title */

    vtbh_send_packet(dev, VTBH_CMD_CREATE, b.buffer, b.len);
    return oid;
}

uint32_t vtbh_create_rect(struct vtbh_device *dev, uint32_t parent,
                          int16_t x, int16_t y, uint16_t w, uint16_t h,
                          uint16_t fill_color, uint16_t border_color,
                          uint8_t border_width, uint8_t radius) {
    uint32_t oid = dev->next_object_id++;

    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u32(&b, parent);
    vtbh_builder_u8(&b, VTBH_OBJ_RECT);
    vtbh_builder_i16(&b, x);
    vtbh_builder_i16(&b, y);
    vtbh_builder_u16(&b, w);
    vtbh_builder_u16(&b, h);
    vtbh_builder_u16(&b, 0);             /* flags */
    vtbh_builder_u16(&b, fill_color);
    vtbh_builder_u16(&b, border_color);
    vtbh_builder_u8(&b, border_width);
    vtbh_builder_u8(&b, radius);

    vtbh_send_packet(dev, VTBH_CMD_CREATE, b.buffer, b.len);
    return oid;
}

uint32_t vtbh_create_text(struct vtbh_device *dev, uint32_t parent,
                          int16_t x, int16_t y, const char *text,
                          uint8_t font_size, uint16_t color) {
    uint32_t oid = dev->next_object_id++;

    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u32(&b, parent);
    vtbh_builder_u8(&b, VTBH_OBJ_TEXT);
    vtbh_builder_i16(&b, x);
    vtbh_builder_i16(&b, y);
    vtbh_builder_u16(&b, 0);             /* w (auto) */
    vtbh_builder_u16(&b, 0);             /* h (auto) */
    vtbh_builder_u16(&b, 0);             /* flags */
    vtbh_builder_u8(&b, 0);              /* font id */
    vtbh_builder_u8(&b, font_size);
    vtbh_builder_u16(&b, color);
    vtbh_builder_u8(&b, 0);              /* align */
    vtbh_builder_str(&b, text);

    vtbh_send_packet(dev, VTBH_CMD_CREATE, b.buffer, b.len);
    return oid;
}

uint32_t vtbh_create_circle(struct vtbh_device *dev, uint32_t parent,
                            int16_t cx, int16_t cy, uint16_t radius,
                            uint16_t color, bool filled) {
    uint32_t oid = dev->next_object_id++;

    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u32(&b, parent);
    vtbh_builder_u8(&b, VTBH_OBJ_CIRCLE);
    vtbh_builder_i16(&b, cx - radius);   /* x (bounding box) */
    vtbh_builder_i16(&b, cy - radius);   /* y */
    vtbh_builder_u16(&b, radius * 2);    /* w */
    vtbh_builder_u16(&b, radius * 2);    /* h */
    vtbh_builder_u16(&b, 0);
    vtbh_builder_u16(&b, color);
    vtbh_builder_u16(&b, color);         /* border (same as fill if filled) */
    vtbh_builder_u8(&b, filled ? 0 : 2); /* border width */
    vtbh_builder_u8(&b, filled ? 1 : 0);

    vtbh_send_packet(dev, VTBH_CMD_CREATE, b.buffer, b.len);
    return oid;
}

int vtbh_destroy(struct vtbh_device *dev, uint32_t oid) {
    struct vtbh_builder b;
    vtbh_builder_init(&b);
    vtbh_builder_u32(&b, oid);
    return vtbh_send_packet(dev, VTBH_CMD_DESTROY, b.buffer, b.len);
}

int vtbh_update_position(struct vtbh_device *dev, uint32_t oid,
                         int16_t x, int16_t y) {
    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u8(&b, 2);              /* property count */
    vtbh_builder_u8(&b, VTBH_PROP_X);
    vtbh_builder_i16(&b, x);
    vtbh_builder_u8(&b, VTBH_PROP_Y);
    vtbh_builder_i16(&b, y);

    return vtbh_send_packet(dev, VTBH_CMD_UPDATE, b.buffer, b.len);
}

int vtbh_update_text(struct vtbh_device *dev, uint32_t oid, const char *text) {
    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u8(&b, 1);
    vtbh_builder_u8(&b, VTBH_PROP_TEXT);
    vtbh_builder_str(&b, text);

    return vtbh_send_packet(dev, VTBH_CMD_UPDATE, b.buffer, b.len);
}

int vtbh_update_color(struct vtbh_device *dev, uint32_t oid, uint16_t color) {
    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u8(&b, 1);
    vtbh_builder_u8(&b, VTBH_PROP_FILL_COLOR);
    vtbh_builder_u16(&b, color);

    return vtbh_send_packet(dev, VTBH_CMD_UPDATE, b.buffer, b.len);
}

int vtbh_update_visible(struct vtbh_device *dev, uint32_t oid, bool visible) {
    struct vtbh_builder b;
    vtbh_builder_init(&b);

    vtbh_builder_u32(&b, oid);
    vtbh_builder_u8(&b, 1);
    vtbh_builder_u8(&b, VTBH_PROP_VISIBLE);
    vtbh_builder_u8(&b, visible ? 1 : 0);

    return vtbh_send_packet(dev, VTBH_CMD_UPDATE, b.buffer, b.len);
}

uint32_t vtbh_sync(struct vtbh_device *dev) {
    uint32_t sync_id = dev->next_sync_id++;

    struct vtbh_builder b;
    vtbh_builder_init(&b);
    vtbh_builder_u32(&b, sync_id);

    vtbh_send_packet(dev, VTBH_CMD_SYNC, b.buffer, b.len);
    return sync_id;
}

/* ============================================================
 * EVENT PROCESSING
 * ============================================================ */

/* Call this periodically to process incoming data */
int vtbh_poll(struct vtbh_device *dev) {
    uint8_t buf[256];
    int n = serial_read(dev->serial_handle, buf, sizeof(buf));

    if (n <= 0) return 0;

    /* Append to rx buffer */
    for (int i = 0; i < n && dev->rx_len < sizeof(dev->rx_buffer); i++) {
        dev->rx_buffer[dev->rx_len++] = buf[i];
    }

    /* Process complete packets */
    int events_processed = 0;
    size_t start = 0;

    for (size_t i = 0; i < dev->rx_len; i++) {
        if (dev->rx_buffer[i] == VTBH_STX) {
            start = i;
        } else if (dev->rx_buffer[i] == VTBH_ETX && i > start + 5) {
            /* Found complete packet */
            char type = dev->rx_buffer[start + 1];

            /* Decode and process based on type */
            if (type == VTBH_RSP_WELCOME) {
                /* Parse welcome response */
                dev->connected = true;
                /* TODO: parse screen size, etc */
            } else if (type == VTBH_RSP_EVENT) {
                /* Parse event */
                /* TODO: decode base64, parse event, add to queue */
                events_processed++;
            } else if (type == VTBH_RSP_SYNC_ACK) {
                /* Sync acknowledged */
            }

            start = i + 1;
        }
    }

    /* Compact rx buffer */
    if (start > 0) {
        for (size_t i = start; i < dev->rx_len; i++) {
            dev->rx_buffer[i - start] = dev->rx_buffer[i];
        }
        dev->rx_len -= start;
    }

    return events_processed;
}

bool vtbh_get_event(struct vtbh_device *dev, struct vtbh_event *evt) {
    if (dev->event_head == dev->event_tail) {
        return false; /* Queue empty */
    }

    *evt = dev->event_queue[dev->event_tail];
    dev->event_tail = (dev->event_tail + 1) % 64;
    return true;
}

/* ============================================================
 * EXAMPLE USAGE
 * ============================================================ */

#if 0  /* Example main() for your OS */

void example_main(void) {
    struct vtbh_device dev;
    void *serial = open_serial("/dev/ttyS0", 115200);

    vtbh_init(&dev, serial);
    vtbh_connect(&dev, "MyOS Desktop");

    /* Wait for connection */
    while (!dev.connected) {
        vtbh_poll(&dev);
    }

    /* Create a simple window with a button */
    uint32_t win = vtbh_create_window(&dev, 100, 100, 300, 200, "Hello");
    uint32_t btn_bg = vtbh_create_rect(&dev, win, 100, 80, 100, 30,
                                       VTBH_COLOR_BLUE, VTBH_COLOR_WHITE, 2, 5);
    uint32_t btn_text = vtbh_create_text(&dev, win, 125, 88, "Click Me", 14,
                                         VTBH_COLOR_WHITE);

    /* Sync to ensure everything is drawn */
    vtbh_sync(&dev);

    /* Event loop */
    while (1) {
        vtbh_poll(&dev);

        struct vtbh_event evt;
        while (vtbh_get_event(&dev, &evt)) {
            if (evt.type == VTBH_EVT_MOUSE_DOWN) {
                /* Check if click is inside button */
                if (evt.mouse.x >= 200 && evt.mouse.x <= 300 &&
                    evt.mouse.y >= 180 && evt.mouse.y <= 210) {
                    /* Button clicked! */
                    vtbh_update_color(&dev, btn_bg, VTBH_COLOR_GREEN);
                    vtbh_update_text(&dev, btn_text, "Clicked!");
                }
            }
            if (evt.type == VTBH_EVT_KEY_DOWN && evt.key.keycode == 0x29) {
                /* ESC pressed, exit */
                vtbh_destroy(&dev, win);
                return;
            }
        }

        /* Small delay */
        sleep_ms(10);
    }
}

#endif
