//! Input handling module

use crate::protocol::{InputEvent, Modifiers, MouseButton};
use std::time::Instant;
use winit::event::{ElementState, MouseButton as WinitMouseButton};
use winit::keyboard::{KeyCode, PhysicalKey};

/// Tracks input state and generates events
pub struct InputHandler {
    start_time: Instant,
    modifiers: Modifiers,
    raw_mode: bool,
    last_mouse_pos: (f32, f32),
}

impl InputHandler {
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            modifiers: Modifiers::default(),
            raw_mode: true,
            last_mouse_pos: (0.0, 0.0),
        }
    }

    pub fn set_raw_mode(&mut self, raw: bool) {
        self.raw_mode = raw;
    }

    fn timestamp(&self) -> u64 {
        self.start_time.elapsed().as_micros() as u64
    }

    /// Update modifier state from winit modifiers
    pub fn update_modifiers(&mut self, mods: &winit::event::Modifiers) {
        let mut m = 0u32;
        let state = mods.state();

        if state.shift_key() {
            m |= Modifiers::SHIFT_L; // Can't distinguish L/R in winit easily
        }
        if state.control_key() {
            m |= Modifiers::CTRL_L;
        }
        if state.alt_key() {
            m |= Modifiers::ALT_L;
        }
        if state.super_key() {
            m |= Modifiers::META_L;
        }

        self.modifiers = Modifiers(m);
    }

    /// Handle keyboard event
    pub fn handle_keyboard(
        &self,
        physical_key: PhysicalKey,
        state: ElementState,
        repeat: bool,
    ) -> Option<InputEvent> {
        let keycode = match physical_key {
            PhysicalKey::Code(code) => keycode_to_u32(code),
            PhysicalKey::Unidentified(_) => return None,
        };

        let scancode = match physical_key {
            PhysicalKey::Code(code) => code as u32,
            PhysicalKey::Unidentified(_) => 0,
        };

        let timestamp = self.timestamp();

        Some(match state {
            ElementState::Pressed if repeat => InputEvent::KeyRepeat {
                keycode,
                scancode,
                modifiers: self.modifiers,
                timestamp,
            },
            ElementState::Pressed => InputEvent::KeyDown {
                keycode,
                scancode,
                modifiers: self.modifiers,
                timestamp,
            },
            ElementState::Released => InputEvent::KeyUp {
                keycode,
                scancode,
                modifiers: self.modifiers,
                timestamp,
            },
        })
    }

    /// Handle text input
    pub fn handle_text(&self, text: &str) -> Vec<InputEvent> {
        let timestamp = self.timestamp();
        text.chars()
            .map(|c| InputEvent::KeyChar {
                codepoint: c as u32,
                modifiers: self.modifiers,
                timestamp,
            })
            .collect()
    }

    /// Handle mouse button event
    pub fn handle_mouse_button(
        &self,
        button: WinitMouseButton,
        state: ElementState,
        position: (f32, f32),
    ) -> InputEvent {
        let btn = match button {
            WinitMouseButton::Left => MouseButton::Left,
            WinitMouseButton::Right => MouseButton::Right,
            WinitMouseButton::Middle => MouseButton::Middle,
            WinitMouseButton::Back => MouseButton::Extra(3),
            WinitMouseButton::Forward => MouseButton::Extra(4),
            WinitMouseButton::Other(n) => MouseButton::Extra(n as u8),
        };

        let timestamp = self.timestamp();

        match state {
            ElementState::Pressed => InputEvent::MouseDown {
                button: btn,
                x: position.0,
                y: position.1,
                modifiers: self.modifiers,
                timestamp,
            },
            ElementState::Released => InputEvent::MouseUp {
                button: btn,
                x: position.0,
                y: position.1,
                modifiers: self.modifiers,
                timestamp,
            },
        }
    }

    /// Handle mouse move event
    pub fn handle_mouse_move(&mut self, x: f32, y: f32) -> InputEvent {
        let dx = x - self.last_mouse_pos.0;
        let dy = y - self.last_mouse_pos.1;
        self.last_mouse_pos = (x, y);

        InputEvent::MouseMove {
            x,
            y,
            dx,
            dy,
            modifiers: self.modifiers,
            timestamp: self.timestamp(),
        }
    }

    /// Handle scroll event
    pub fn handle_scroll(&self, dx: f32, dy: f32, position: (f32, f32)) -> InputEvent {
        InputEvent::Scroll {
            dx,
            dy,
            x: position.0,
            y: position.1,
            modifiers: self.modifiers,
            timestamp: self.timestamp(),
        }
    }

    /// Handle focus event
    pub fn handle_focus(&self, focused: bool) -> InputEvent {
        InputEvent::Focus { focused }
    }

    /// Handle resize event
    pub fn handle_resize(&self, width: f32, height: f32) -> InputEvent {
        InputEvent::Resize { width, height }
    }
}

/// Convert winit KeyCode to our keycode
fn keycode_to_u32(code: KeyCode) -> u32 {
    // Using USB HID-ish codes
    match code {
        KeyCode::KeyA => 0x04,
        KeyCode::KeyB => 0x05,
        KeyCode::KeyC => 0x06,
        KeyCode::KeyD => 0x07,
        KeyCode::KeyE => 0x08,
        KeyCode::KeyF => 0x09,
        KeyCode::KeyG => 0x0A,
        KeyCode::KeyH => 0x0B,
        KeyCode::KeyI => 0x0C,
        KeyCode::KeyJ => 0x0D,
        KeyCode::KeyK => 0x0E,
        KeyCode::KeyL => 0x0F,
        KeyCode::KeyM => 0x10,
        KeyCode::KeyN => 0x11,
        KeyCode::KeyO => 0x12,
        KeyCode::KeyP => 0x13,
        KeyCode::KeyQ => 0x14,
        KeyCode::KeyR => 0x15,
        KeyCode::KeyS => 0x16,
        KeyCode::KeyT => 0x17,
        KeyCode::KeyU => 0x18,
        KeyCode::KeyV => 0x19,
        KeyCode::KeyW => 0x1A,
        KeyCode::KeyX => 0x1B,
        KeyCode::KeyY => 0x1C,
        KeyCode::KeyZ => 0x1D,
        KeyCode::Digit1 => 0x1E,
        KeyCode::Digit2 => 0x1F,
        KeyCode::Digit3 => 0x20,
        KeyCode::Digit4 => 0x21,
        KeyCode::Digit5 => 0x22,
        KeyCode::Digit6 => 0x23,
        KeyCode::Digit7 => 0x24,
        KeyCode::Digit8 => 0x25,
        KeyCode::Digit9 => 0x26,
        KeyCode::Digit0 => 0x27,
        KeyCode::Enter => 0x28,
        KeyCode::Escape => 0x29,
        KeyCode::Backspace => 0x2A,
        KeyCode::Tab => 0x2B,
        KeyCode::Space => 0x2C,
        KeyCode::ArrowUp => 0x52,
        KeyCode::ArrowDown => 0x51,
        KeyCode::ArrowLeft => 0x50,
        KeyCode::ArrowRight => 0x4F,
        KeyCode::F1 => 0x3A,
        KeyCode::F2 => 0x3B,
        KeyCode::F3 => 0x3C,
        KeyCode::F4 => 0x3D,
        KeyCode::F5 => 0x3E,
        KeyCode::F6 => 0x3F,
        KeyCode::F7 => 0x40,
        KeyCode::F8 => 0x41,
        KeyCode::F9 => 0x42,
        KeyCode::F10 => 0x43,
        KeyCode::F11 => 0x44,
        KeyCode::F12 => 0x45,
        KeyCode::ShiftLeft => 0xE1,
        KeyCode::ShiftRight => 0xE5,
        KeyCode::ControlLeft => 0xE0,
        KeyCode::ControlRight => 0xE4,
        KeyCode::AltLeft => 0xE2,
        KeyCode::AltRight => 0xE6,
        KeyCode::SuperLeft => 0xE3,
        KeyCode::SuperRight => 0xE7,
        _ => 0xFF,
    }
}
