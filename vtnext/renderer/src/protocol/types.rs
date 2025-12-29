//! Core types for VTNext protocol

/// RGBA color
#[derive(Debug, Clone, Copy, Default)]
pub struct Color {
    pub r: u8,
    pub g: u8,
    pub b: u8,
    pub a: u8,
}

impl Color {
    pub fn new(r: u8, g: u8, b: u8, a: u8) -> Self {
        Self { r, g, b, a }
    }

    pub fn as_floats(&self) -> [f32; 4] {
        [
            self.r as f32 / 255.0,
            self.g as f32 / 255.0,
            self.b as f32 / 255.0,
            self.a as f32 / 255.0,
        ]
    }
}

/// 2D/3D position
#[derive(Debug, Clone, Copy, Default)]
pub struct Position {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

/// Transform for rendering
#[derive(Debug, Clone, Copy)]
pub struct Transform {
    pub position: Position,
    pub rotation: f32,    // degrees
    pub scale_x: f32,
    pub scale_y: f32,
}

impl Default for Transform {
    fn default() -> Self {
        Self {
            position: Position::default(),
            rotation: 0.0,
            scale_x: 1.0,
            scale_y: 1.0,
        }
    }
}

/// Modifier key bitmask
#[derive(Debug, Clone, Copy, Default)]
pub struct Modifiers(pub u32);

impl Modifiers {
    pub const SHIFT_L: u32   = 0x0001;
    pub const SHIFT_R: u32   = 0x0002;
    pub const CTRL_L: u32    = 0x0004;
    pub const CTRL_R: u32    = 0x0008;
    pub const ALT_L: u32     = 0x0010;
    pub const ALT_R: u32     = 0x0020;
    pub const META_L: u32    = 0x0040;
    pub const META_R: u32    = 0x0080;
    pub const CAPS_LOCK: u32 = 0x0100;
    pub const NUM_LOCK: u32  = 0x0200;

    pub fn shift(&self) -> bool {
        self.0 & (Self::SHIFT_L | Self::SHIFT_R) != 0
    }

    pub fn ctrl(&self) -> bool {
        self.0 & (Self::CTRL_L | Self::CTRL_R) != 0
    }

    pub fn alt(&self) -> bool {
        self.0 & (Self::ALT_L | Self::ALT_R) != 0
    }

    pub fn meta(&self) -> bool {
        self.0 & (Self::META_L | Self::META_R) != 0
    }
}

/// Mouse button
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MouseButton {
    Left,
    Right,
    Middle,
    Extra(u8),
}

impl From<u8> for MouseButton {
    fn from(v: u8) -> Self {
        match v {
            0 => Self::Left,
            1 => Self::Right,
            2 => Self::Middle,
            n => Self::Extra(n),
        }
    }
}

/// Image format
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ImageFormat {
    Png,
    Jpg,
    Rgba,
}

impl ImageFormat {
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "png" => Some(Self::Png),
            "jpg" | "jpeg" => Some(Self::Jpg),
            "rgba" => Some(Self::Rgba),
            _ => None,
        }
    }
}
