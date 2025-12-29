# vtbrainhair Quick Reference

## Packet Format

```
STX <type:1> <len_b64:2> <payload_b64:*> <crc8_b64:2> ETX
```

- STX = 0x02, ETX = 0x03
- Type: A-Z = commands, a-z = responses
- All data base64 encoded (serial safe)

---

## Commands (Client → Server)

| Type | Name | Payload |
|------|------|---------|
| `A` | HELLO | ver:u8, flags:u16, max_w:u16, max_h:u16, name:str |
| `C` | CREATE | oid:u32, parent:u32, type:u8, x:i16, y:i16, w:u16, h:u16, flags:u16, [data] |
| `D` | DESTROY | oid:u32 |
| `E` | UPDATE | oid:u32, prop_count:u8, [prop_id:u8, value]... |
| `L` | IMAGE | oid:u32, offset:u32, chunk_len:u16, data:bytes |
| `R` | BATCH | count:u16, [type:u8, len:u16, payload]... |
| `S` | SYNC | sync_id:u32 |

---

## Object Types

| ID | Type | Extra Data |
|----|------|------------|
| 0x01 | Window | title:str |
| 0x02 | Panel | - |
| 0x03 | Text | font:u8, size:u8, color:u16, align:u8, text:str |
| 0x04 | Rect | fill:u16, border:u16, border_w:u8, radius:u8 |
| 0x05 | Line | x2:i16, y2:i16, color:u16, width:u8 |
| 0x06 | Circle | color:u16, border:u16, border_w:u8, filled:u8 |
| 0x07 | Arc | start:i16, end:i16, color:u16, width:u8 |
| 0x08 | Polygon | point_count:u8, [x:i16, y:i16]..., color:u16, filled:u8 |
| 0x0A | Image | format:u8, compress:u8, total_size:u32 |

---

## Properties (for UPDATE)

| ID | Property | Type |
|----|----------|------|
| 0x01 | x | i16 |
| 0x02 | y | i16 |
| 0x03 | width | u16 |
| 0x04 | height | u16 |
| 0x05 | visible | u8 |
| 0x06 | opacity | u8 |
| 0x07 | rotation | i16 (deg×10) |
| 0x10 | fill_color | u16 |
| 0x11 | border_color | u16 |
| 0x20 | text | string |
| 0x22 | font_size | u8 |
| 0x23 | text_color | u16 |

---

## Responses (Server → Client)

| Type | Name | Payload |
|------|------|---------|
| `a` | WELCOME | ver:u8, flags:u16, width:u16, height:u16 |
| `b` | OK | - |
| `c` | ERROR | code:u8, msg:str |
| `d` | EVENT | type:u8, timestamp:u32, [data] |
| `e` | SYNC_ACK | sync_id:u32 |

---

## Events

| Type | Name | Data |
|------|------|------|
| 0x01 | KEY_DOWN | key:u16, mod:u8, char:u32 |
| 0x02 | KEY_UP | key:u16, mod:u8 |
| 0x10 | MOUSE_MOVE | x:i16, y:i16, buttons:u8 |
| 0x11 | MOUSE_DOWN | x:i16, y:i16, btn:u8, mod:u8 |
| 0x12 | MOUSE_UP | x:i16, y:i16, btn:u8, mod:u8 |
| 0x13 | SCROLL | x:i16, y:i16, dx:i8, dy:i8 |
| 0x30 | RESIZE | w:u16, h:u16 |

Modifiers: Shift=0x01, Ctrl=0x02, Alt=0x04, Meta=0x08

---

## Color: RGB565

```
RRRRRGGGGGGBBBBB
  5     6    5
```

Common colors:
- White: 0xFFFF
- Black: 0x0000
- Red: 0xF800
- Green: 0x07E0
- Blue: 0x001F

---

## CRC-8 (Polynomial 0x07)

```c
uint8_t crc8(const uint8_t *data, size_t len) {
    uint8_t crc = 0;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++)
            crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : crc << 1;
    }
    return crc;
}
```

---

## Base64 Table

```
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/
```

---

## Typical Session

```
→ A (HELLO)
← a (WELCOME: 1024×768)
→ C (CREATE window id=1 parent=0 at 100,100 size 400×300)
→ C (CREATE text id=2 parent=1 "Hello World")
→ C (CREATE rect id=3 parent=1 button)
→ S (SYNC id=1)
← e (SYNC_ACK id=1)
← d (EVENT: MOUSE_MOVE)
← d (EVENT: KEY_DOWN)
...
```

---

## Bandwidth Planning

| Baud | KB/s | Simple UI | Small Image | Full Screen |
|------|------|-----------|-------------|-------------|
| 9600 | ~1 | 200ms | 30s | 10min |
| 115200 | ~11 | 20ms | 3s | 1min |
| 921600 | ~90 | 3ms | 400ms | 7s |
