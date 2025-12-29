# vtbrainhair Protocol Specification v1.0

A serial-transparent desktop graphics protocol designed for low-bandwidth connections.

## Design Goals

1. **Serial Transparent** - Works over any serial link (RS-232, UART, USB-serial)
2. **Bandwidth Efficient** - Designed for 9600-115200 baud typical
3. **Full Desktop** - Windows, widgets, mouse cursor, not just text
4. **Progressive** - Images stream incrementally, UI remains responsive
5. **Retained Mode** - Server maintains scene graph, client sends updates
6. **Resumable** - Can recover from connection drops

## Architecture

```
┌─────────────────┐                      ┌─────────────────┐
│   vtbrainhair   │    Serial Link       │   vtbrainhair   │
│     Client      │◄────────────────────►│     Server      │
│  (runs on OS)   │   escape sequences   │   (renderer)    │
└─────────────────┘                      └─────────────────┘
        │                                        │
        ▼                                        ▼
   Application                              Display
    Processes                              Hardware
```

- **Client**: Runs in OS kernel/userspace, sends draw commands
- **Server**: Renders to display, sends input events back

---

## Packet Format

### Framing

All packets use ASCII-safe framing to avoid serial control character conflicts:

```
STX <type> <length_b64> <payload_b64> <crc8_b64> ETX
```

| Field | Bytes | Description |
|-------|-------|-------------|
| STX | 1 | Start of packet: `\x02` |
| type | 1 | Packet type: A-Z (commands), a-z (responses) |
| length_b64 | 2 | Payload length, base64-encoded (0-4095 bytes) |
| payload_b64 | variable | Base64-encoded payload |
| crc8_b64 | 2 | CRC-8 of raw payload, base64-encoded |
| ETX | 1 | End of packet: `\x03` |

### Why Base64?

- Avoids XON/XOFF (0x11, 0x13) flow control conflicts
- Avoids NULL bytes that terminate strings
- Survives 7-bit serial links
- ~33% overhead but predictable and safe

### Alternative: Binary Mode

After handshake, can negotiate binary mode for higher throughput:

```
\x1B[?2026h    Enable binary mode
\x1B[?2026l    Disable binary mode (return to safe mode)
```

In binary mode:
- Length is 2-byte little-endian
- Payload is raw bytes
- XON/XOFF must be disabled on link

---

## Coordinate System

- Origin (0,0) at top-left
- X increases right, Y increases down
- All coordinates are 16-bit signed integers (-32768 to 32767)
- Allows for off-screen rendering, scrolling regions
- 1 unit = 1 pixel at native resolution

## Color Format

Colors use 16-bit RGB565 for efficiency, or 32-bit RGBA8888 when alpha needed:

| Format | Bits | Description |
|--------|------|-------------|
| RGB565 | 16 | 5-bit R, 6-bit G, 5-bit B |
| RGBA4444 | 16 | 4 bits per channel |
| RGBA8888 | 32 | 8 bits per channel |
| Indexed | 8 | Palette index (256 colors) |

Default palette: Standard 256-color terminal palette (16 ANSI + 216 cube + 24 gray)

---

## Object Model (Retained Mode)

vtbrainhair uses a retained scene graph. Objects persist until explicitly destroyed.

### Object Types

| Type ID | Name | Description |
|---------|------|-------------|
| 0x01 | Window | Top-level container |
| 0x02 | Panel | Child container |
| 0x03 | Text | Text string |
| 0x04 | Rect | Rectangle |
| 0x05 | Line | Line segment |
| 0x06 | Circle | Circle/ellipse |
| 0x07 | Arc | Arc segment |
| 0x08 | Polygon | Arbitrary polygon |
| 0x09 | Path | Vector path |
| 0x0A | Image | Bitmap image |
| 0x0B | Cursor | Mouse cursor |
| 0x0C | Sprite | Animated sprite |

### Object IDs

- 32-bit unique identifier
- Client assigns IDs (server validates uniqueness)
- ID 0 reserved for root/desktop

---

## Commands (Client → Server)

### Packet Type Codes

| Code | Command | Description |
|------|---------|-------------|
| A | HELLO | Handshake initiation |
| B | AUTH | Authentication |
| C | CREATE | Create object |
| D | DESTROY | Destroy object |
| E | UPDATE | Modify object properties |
| F | MOVE | Change position |
| G | RESIZE | Change size |
| H | ZORDER | Change stacking |
| I | SHOW | Set visibility |
| J | STYLE | Set style properties |
| K | TEXT | Set text content |
| L | IMAGE | Image data chunk |
| M | CURSOR | Set cursor shape |
| N | CLIP | Set clipping region |
| O | SCROLL | Scroll region |
| P | INVALIDATE | Request redraw |
| Q | QUERY | Query state |
| R | BATCH | Batch multiple commands |
| S | SYNC | Synchronization barrier |
| T | PALETTE | Set color palette |
| U | FONT | Define/select font |
| V | CAPTURE | Screen capture request |

---

### Command Details

#### A: HELLO - Handshake

```
Payload: <version:u8> <flags:u16> <max_width:u16> <max_height:u16> <name:str>
```

Flags:
- 0x0001: Supports binary mode
- 0x0002: Supports compression
- 0x0004: Supports alpha channel
- 0x0008: Supports animations
- 0x0010: Supports audio (future)

#### C: CREATE - Create Object

```
Payload: <object_id:u32> <parent_id:u32> <type:u8> <x:i16> <y:i16> <w:u16> <h:u16> <flags:u16> [type-specific data]
```

Type-specific data for TEXT (0x03):
```
<font_id:u8> <size:u8> <color:u16> <align:u8> <text:str>
```

Type-specific data for RECT (0x04):
```
<fill_color:u16> <border_color:u16> <border_width:u8> <radius:u8>
```

Type-specific data for IMAGE (0x0A):
```
<format:u8> <compression:u8> <total_size:u32>
```

Image formats:
- 0x00: Raw RGB565
- 0x01: Raw RGBA8888
- 0x02: RLE-compressed
- 0x03: PNG
- 0x04: JPEG (lossy OK for photos)
- 0x05: QOI (fast encode/decode)

#### E: UPDATE - Modify Properties

```
Payload: <object_id:u32> <property_count:u8> [<prop_id:u8> <value:varies>]...
```

Property IDs:
| ID | Property | Value Type |
|----|----------|------------|
| 0x01 | x | i16 |
| 0x02 | y | i16 |
| 0x03 | width | u16 |
| 0x04 | height | u16 |
| 0x05 | visible | u8 (bool) |
| 0x06 | opacity | u8 (0-255) |
| 0x07 | rotation | i16 (degrees * 10) |
| 0x08 | scale_x | u16 (fixed 8.8) |
| 0x09 | scale_y | u16 (fixed 8.8) |
| 0x0A | z_index | i16 |
| 0x10 | fill_color | u16/u32 |
| 0x11 | border_color | u16/u32 |
| 0x12 | border_width | u8 |
| 0x13 | corner_radius | u8 |
| 0x20 | text | string |
| 0x21 | font_id | u8 |
| 0x22 | font_size | u8 |
| 0x23 | text_color | u16/u32 |
| 0x24 | text_align | u8 |

#### L: IMAGE - Image Data Chunk

For streaming large images over slow serial:

```
Payload: <object_id:u32> <offset:u32> <chunk_size:u16> <data:bytes>
```

- Server assembles chunks into complete image
- Can send out-of-order for progressive display
- Recommend 256-512 byte chunks for serial

#### R: BATCH - Batch Commands

Reduces per-packet overhead:

```
Payload: <count:u16> [<cmd_type:u8> <cmd_len:u16> <cmd_payload:bytes>]...
```

#### S: SYNC - Synchronization

```
Payload: <sync_id:u32>
```

Server responds with sync acknowledgment when all prior commands processed.
Essential for knowing when a frame is complete.

---

## Responses (Server → Client)

| Code | Response | Description |
|------|----------|-------------|
| a | WELCOME | Handshake response |
| b | OK | Command succeeded |
| c | ERROR | Command failed |
| d | EVENT | Input event |
| e | SYNC_ACK | Sync acknowledgment |
| f | QUERY_RESULT | Query response |

### d: EVENT - Input Events

```
Payload: <event_type:u8> <timestamp:u32> <data:varies>
```

Event Types:

| Type | Name | Data |
|------|------|------|
| 0x01 | KEY_DOWN | keycode:u16, modifiers:u8, char:u32 |
| 0x02 | KEY_UP | keycode:u16, modifiers:u8 |
| 0x03 | KEY_REPEAT | keycode:u16, modifiers:u8, char:u32 |
| 0x10 | MOUSE_MOVE | x:i16, y:i16, buttons:u8 |
| 0x11 | MOUSE_DOWN | x:i16, y:i16, button:u8, modifiers:u8 |
| 0x12 | MOUSE_UP | x:i16, y:i16, button:u8, modifiers:u8 |
| 0x13 | MOUSE_SCROLL | x:i16, y:i16, dx:i8, dy:i8 |
| 0x20 | FOCUS_IN | object_id:u32 |
| 0x21 | FOCUS_OUT | object_id:u32 |
| 0x30 | RESIZE | width:u16, height:u16 |
| 0x31 | CLOSE | (none) |

Modifier bits:
- 0x01: Shift
- 0x02: Ctrl
- 0x04: Alt
- 0x08: Meta/Super
- 0x10: Caps Lock (state)
- 0x20: Num Lock (state)

---

## Compression

For bandwidth-constrained links, optional compression:

### Delta Encoding

For small updates, send only changed bytes:

```
Command D_UPDATE:
Payload: <object_id:u32> <base_hash:u16> <delta_ops:bytes>
```

Delta ops:
- `0x00 <skip:u8>` - Skip N bytes unchanged
- `0x01 <count:u8> <bytes>` - Replace N bytes
- `0x02 <count:u8> <byte>` - Repeat byte N times

### RLE for Images

Simple RLE for images:
- `0x00-0x7F` - Literal run (1-128 bytes follow)
- `0x80-0xFF` - Repeat run (next byte repeated 2-129 times)

### LZ4/Zstd

For batch commands, can use streaming LZ4:

```
\x1B[?2027h    Enable LZ4 compression
\x1B[?2027l    Disable compression
```

---

## Flow Control

### Software Flow Control (Safe Mode)

- XON/XOFF handled by serial driver
- Protocol uses only 0x02-0x03 (STX/ETX), 0x20-0x7E (printable), plus base64
- If receiver buffer full, sends XOFF, sender pauses
- Recovery: can always send SYNC to re-establish state

### Hardware Flow Control (Preferred)

- RTS/CTS for byte-level flow control
- Allows binary mode without XON/XOFF conflicts
- Much higher effective throughput

### Rate Limiting

Client should implement:
```
Commands per second: min(1000, baud_rate / 100)
```

Server sends BUSY response if overwhelmed:
```
Response c: ERROR
Payload: <error_code:u8> 0x10 = BUSY, retry after <delay_ms:u16>
```

---

## Session Management

### Connection Sequence

```
Client                          Server
   │                               │
   │──── HELLO ───────────────────►│
   │                               │
   │◄─── WELCOME ─────────────────│
   │     (capabilities, screen)    │
   │                               │
   │──── CREATE (root window) ────►│
   │                               │
   │──── CREATE (UI objects) ─────►│
   │                               │
   │──── SYNC ────────────────────►│
   │                               │
   │◄─── SYNC_ACK ─────────────────│
   │     (display ready)           │
   │                               │
   │◄─── EVENT (inputs) ──────────│
   │                               │
```

### Reconnection

After connection loss:

1. Client sends HELLO with reconnect flag
2. Server clears all objects
3. Client re-sends scene graph
4. Use SYNC to confirm ready

Or, for session persistence:

1. Server can optionally persist scene
2. HELLO includes session_id
3. Server sends current object list
4. Client sends only deltas

---

## Built-in Widgets (Optional Extension)

For common UI elements, high-level commands:

| Widget | Description |
|--------|-------------|
| BUTTON | Clickable button with label |
| CHECKBOX | Toggle checkbox |
| RADIO | Radio button group |
| TEXTFIELD | Single-line text input |
| TEXTAREA | Multi-line text input |
| SLIDER | Value slider |
| PROGRESS | Progress bar |
| LISTBOX | Scrollable list |
| DROPDOWN | Dropdown menu |
| SCROLLBAR | Scroll control |
| MENUBAR | Application menu |
| TOOLTIP | Hover tooltip |

Widget command:
```
Type W: WIDGET
Payload: <widget_type:u8> <object_id:u32> <parent_id:u32> <x:i16> <y:i16> <w:u16> <h:u16> <style_id:u8> <widget_data:varies>
```

Reduces bandwidth vs. drawing widgets from primitives.

---

## Fonts

### Built-in Fonts

| ID | Name | Description |
|----|------|-------------|
| 0 | System | Default proportional |
| 1 | Mono | Default monospace |
| 2 | Serif | Serif proportional |
| 3 | Sans | Sans-serif proportional |

### Custom Fonts

Upload bitmap or vector font:

```
Type U: FONT
Payload: <font_id:u8> <format:u8> <data:bytes>
```

Formats:
- 0x00: BDF (bitmap)
- 0x01: PSF (console font)
- 0x02: Compressed glyph atlas

---

## Example Session (Bandwidth Estimate)

Drawing a simple window with title and button at 115200 baud (~11KB/s):

| Command | Payload Size | Wire Size (base64) | Time @ 115200 |
|---------|--------------|-------------------|---------------|
| HELLO | 20 | 35 | 3ms |
| CREATE window | 24 | 40 | 3ms |
| CREATE title_bar | 20 | 35 | 3ms |
| CREATE title_text | 40 | 60 | 5ms |
| CREATE button | 28 | 45 | 4ms |
| CREATE button_text | 35 | 55 | 5ms |
| SYNC | 4 | 14 | 1ms |
| **Total** | **171** | **284** | **~25ms** |

A basic window appears in under 30ms even at 115200 baud.

For a 640x480 RGB565 image (614KB raw):
- With RLE (typical 2:1): ~300KB
- With JPEG (10:1): ~60KB
- At 115200: 5-50 seconds depending on compression

---

## Kernel Integration Notes

### Minimal Kernel Driver

```c
struct vtbh_device {
    int fd;                    // Serial port fd
    uint32_t next_object_id;
    struct vtbh_object *root;
    // ... buffers, state
};

// Core API
int vtbh_init(struct vtbh_device *dev, const char *serial_port);
int vtbh_create(struct vtbh_device *dev, uint32_t parent, uint8_t type, ...);
int vtbh_update(struct vtbh_device *dev, uint32_t id, ...);
int vtbh_destroy(struct vtbh_device *dev, uint32_t id);
int vtbh_sync(struct vtbh_device *dev);
int vtbh_poll_events(struct vtbh_device *dev, struct vtbh_event *events, int max);
```

### Interrupt-Driven I/O

- TX: Fill UART FIFO from command queue
- RX: Parse incoming events into event queue
- Use ring buffers to avoid blocking kernel

### Memory Mapping (Advanced)

For local displays, can memory-map framebuffer:
- Client writes directly to shared memory
- Only need serial for input events
- Hybrid mode for best performance

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01 | Initial specification |

---

## Reference Implementation

See: `vtbrainhair-client/` (kernel module)
See: `vtbrainhair-server/` (renderer)
See: `vtbrainhair-tools/` (testing utilities)
