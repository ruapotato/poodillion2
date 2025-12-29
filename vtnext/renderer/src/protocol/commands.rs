//! VTNext output commands (terminal -> renderer)

use super::types::*;

/// All possible VTNext output commands
#[derive(Debug, Clone)]
pub enum Command {
    /// Draw text at position
    Text {
        transform: Transform,
        color: Color,
        content: String,
    },

    /// Draw single character
    Char {
        transform: Transform,
        color: Color,
        codepoint: u32,
    },

    /// Draw image
    Image {
        x: f32,
        y: f32,
        z: f32,
        width: f32,
        height: f32,
        rotation: f32,
        format: ImageFormat,
        data: Vec<u8>,
    },

    /// Draw rectangle
    Rect {
        x: f32,
        y: f32,
        z: f32,
        width: f32,
        height: f32,
        rotation: f32,
        color: Color,
        filled: bool,
    },

    /// Draw line
    Line {
        x1: f32,
        y1: f32,
        x2: f32,
        y2: f32,
        z: f32,
        thickness: f32,
        color: Color,
    },

    /// Draw circle
    Circle {
        cx: f32,
        cy: f32,
        z: f32,
        radius: f32,
        color: Color,
        filled: bool,
    },

    /// Draw ellipse
    Ellipse {
        cx: f32,
        cy: f32,
        z: f32,
        rx: f32,
        ry: f32,
        rotation: f32,
        color: Color,
        filled: bool,
    },

    /// Draw arc
    Arc {
        cx: f32,
        cy: f32,
        z: f32,
        radius: f32,
        start_angle: f32,
        end_angle: f32,
        thickness: f32,
        color: Color,
    },

    /// Draw polygon
    Polygon {
        points: Vec<(f32, f32)>,
        z: f32,
        color: Color,
        filled: bool,
    },

    /// Draw rounded rectangle
    RoundedRect {
        x: f32,
        y: f32,
        z: f32,
        width: f32,
        height: f32,
        radius: f32,
        color: Color,
        filled: bool,
    },

    /// Clear viewport
    Clear {
        color: Color,
        region: Option<(f32, f32, f32, f32)>, // x, y, w, h
    },

    /// Set viewport size
    Viewport {
        width: f32,
        height: f32,
    },

    /// Layer operations
    LayerPush {
        id: String,
        x: f32,
        y: f32,
        width: f32,
        height: f32,
        opacity: f32,
    },
    LayerPop {
        id: String,
    },

    /// Legacy VT100 subwindow
    LegacyCreate {
        id: String,
        x: f32,
        y: f32,
        cols: u32,
        rows: u32,
        font_size: f32,
    },
    LegacyDestroy {
        id: String,
    },
    LegacyWrite {
        id: String,
        data: Vec<u8>,
    },
    LegacyFocus {
        id: String,
    },

    /// Query commands
    QueryVersion,
    QuerySize,
    QueryFeatures,

    /// Input mode
    InputMode {
        raw: bool,
    },

    /// Cursor control
    CursorHide,
    CursorShow,
    CursorSet {
        image_data: Vec<u8>,
        hotspot_x: f32,
        hotspot_y: f32,
    },
}

/// Input events (renderer -> application)
#[derive(Debug, Clone)]
pub enum InputEvent {
    /// Key pressed
    KeyDown {
        keycode: u32,
        scancode: u32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Key released
    KeyUp {
        keycode: u32,
        scancode: u32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Key repeat
    KeyRepeat {
        keycode: u32,
        scancode: u32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Character input (for text)
    KeyChar {
        codepoint: u32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Mouse button pressed
    MouseDown {
        button: MouseButton,
        x: f32,
        y: f32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Mouse button released
    MouseUp {
        button: MouseButton,
        x: f32,
        y: f32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Mouse moved
    MouseMove {
        x: f32,
        y: f32,
        dx: f32,
        dy: f32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Mouse wheel/scroll
    Scroll {
        dx: f32,
        dy: f32,
        x: f32,
        y: f32,
        modifiers: Modifiers,
        timestamp: u64,
    },

    /// Window focus
    Focus {
        focused: bool,
    },

    /// Window resize
    Resize {
        width: f32,
        height: f32,
    },
}

impl InputEvent {
    /// Encode event as escape sequence to send to application
    pub fn encode(&self) -> String {
        match self {
            InputEvent::KeyDown { keycode, scancode, modifiers, timestamp } => {
                format!("\x1b]vtni;kd;{};{};{};{}\x07", keycode, scancode, modifiers.0, timestamp)
            }
            InputEvent::KeyUp { keycode, scancode, modifiers, timestamp } => {
                format!("\x1b]vtni;ku;{};{};{};{}\x07", keycode, scancode, modifiers.0, timestamp)
            }
            InputEvent::KeyRepeat { keycode, scancode, modifiers, timestamp } => {
                format!("\x1b]vtni;kr;{};{};{};{}\x07", keycode, scancode, modifiers.0, timestamp)
            }
            InputEvent::KeyChar { codepoint, modifiers, timestamp } => {
                format!("\x1b]vtni;kc;{};{};{}\x07", codepoint, modifiers.0, timestamp)
            }
            InputEvent::MouseDown { button, x, y, modifiers, timestamp } => {
                let btn = match button {
                    MouseButton::Left => 0,
                    MouseButton::Right => 1,
                    MouseButton::Middle => 2,
                    MouseButton::Extra(n) => *n,
                };
                format!("\x1b]vtni;md;{};{};{};{};{}\x07", btn, x, y, modifiers.0, timestamp)
            }
            InputEvent::MouseUp { button, x, y, modifiers, timestamp } => {
                let btn = match button {
                    MouseButton::Left => 0,
                    MouseButton::Right => 1,
                    MouseButton::Middle => 2,
                    MouseButton::Extra(n) => *n,
                };
                format!("\x1b]vtni;mu;{};{};{};{};{}\x07", btn, x, y, modifiers.0, timestamp)
            }
            InputEvent::MouseMove { x, y, dx, dy, modifiers, timestamp } => {
                format!("\x1b]vtni;mm;{};{};{};{};{};{}\x07", x, y, dx, dy, modifiers.0, timestamp)
            }
            InputEvent::Scroll { dx, dy, x, y, modifiers, timestamp } => {
                format!("\x1b]vtni;mw;{};{};{};{};{};{}\x07", dx, dy, x, y, modifiers.0, timestamp)
            }
            InputEvent::Focus { focused } => {
                format!("\x1b]vtni;focus;{}\x07", if *focused { 1 } else { 0 })
            }
            InputEvent::Resize { width, height } => {
                format!("\x1b]vtni;resize;{};{}\x07", width, height)
            }
        }
    }
}
