//! VTNext escape sequence parser

use base64::Engine as _;
use super::{commands::Command, types::*};

/// Parser state machine for handling streaming input
pub struct Parser {
    buffer: Vec<u8>,
    in_escape: bool,
}

impl Parser {
    pub fn new() -> Self {
        Self {
            buffer: Vec::with_capacity(4096),
            in_escape: false,
        }
    }

    /// Feed bytes into parser, returns parsed commands and any plain text
    pub fn feed(&mut self, data: &[u8]) -> (Vec<Command>, Vec<u8>) {
        let mut commands = Vec::new();
        let mut plain_text = Vec::new();

        for &byte in data {
            if byte == 0x1B {
                // ESC - start of escape sequence
                self.in_escape = true;
                self.buffer.clear();
                self.buffer.push(byte);
            } else if self.in_escape {
                self.buffer.push(byte);

                // Check for sequence terminator (BEL or ST)
                if byte == 0x07 || (self.buffer.len() >= 2 && self.buffer.ends_with(&[0x1B, b'\\'])) {
                    // Try to parse the complete sequence
                    if let Ok(cmd) = self.parse_sequence(&self.buffer.clone()) {
                        commands.push(cmd);
                    }
                    self.in_escape = false;
                    self.buffer.clear();
                }

                // Safety limit on buffer size
                if self.buffer.len() > 1024 * 1024 {
                    self.in_escape = false;
                    self.buffer.clear();
                }
            } else {
                plain_text.push(byte);
            }
        }

        (commands, plain_text)
    }

    fn parse_sequence(&self, data: &[u8]) -> Result<Command, ParseError> {
        let s = std::str::from_utf8(data).map_err(|_| ParseError::InvalidUtf8)?;

        // Must start with ESC ] vtn ;
        if !s.starts_with("\x1b]vtn;") {
            return Err(ParseError::NotVtNext);
        }

        // Remove prefix and terminator
        let content = s
            .strip_prefix("\x1b]vtn;")
            .and_then(|s| s.strip_suffix('\x07').or_else(|| s.strip_suffix("\x1b\\")))
            .ok_or(ParseError::InvalidFormat)?;

        let parts: Vec<&str> = content.split(';').collect();
        if parts.is_empty() {
            return Err(ParseError::InvalidFormat);
        }

        match parts[0] {
            "text" => self.parse_text(&parts[1..]),
            "char" => self.parse_char(&parts[1..]),
            "rect" => self.parse_rect(&parts[1..]),
            "line" => self.parse_line(&parts[1..]),
            "circle" => self.parse_circle(&parts[1..]),
            "ellipse" => self.parse_ellipse(&parts[1..]),
            "arc" => self.parse_arc(&parts[1..]),
            "poly" => self.parse_polygon(&parts[1..]),
            "rrect" => self.parse_rounded_rect(&parts[1..]),
            "clear" => self.parse_clear(&parts[1..]),
            "viewport" => self.parse_viewport(&parts[1..]),
            "img" => self.parse_image(&parts[1..]),
            "query" => self.parse_query(&parts[1..]),
            "input" => self.parse_input_mode(&parts[1..]),
            "cursor" => self.parse_cursor(&parts[1..]),
            "layer" => self.parse_layer(&parts[1..]),
            "legacy" => self.parse_legacy(&parts[1..]),
            _ => Err(ParseError::UnknownCommand),
        }
    }

    fn parse_text(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // x ; y ; z ; rot ; scale ; r ; g ; b ; a ; "content"
        if parts.len() < 10 {
            return Err(ParseError::MissingParams);
        }

        let x: f32 = parts[0].parse().map_err(|_| ParseError::InvalidNumber)?;
        let y: f32 = parts[1].parse().map_err(|_| ParseError::InvalidNumber)?;
        let z: f32 = parts[2].parse().map_err(|_| ParseError::InvalidNumber)?;
        let rot: f32 = parts[3].parse().map_err(|_| ParseError::InvalidNumber)?;
        let scale: f32 = parts[4].parse().map_err(|_| ParseError::InvalidNumber)?;
        let r: u8 = parts[5].parse().map_err(|_| ParseError::InvalidNumber)?;
        let g: u8 = parts[6].parse().map_err(|_| ParseError::InvalidNumber)?;
        let b: u8 = parts[7].parse().map_err(|_| ParseError::InvalidNumber)?;
        let a: u8 = parts[8].parse().map_err(|_| ParseError::InvalidNumber)?;

        // Content might contain semicolons, so join remaining parts
        let content = parts[9..].join(";");
        let content = content.trim_matches('"').to_string();

        Ok(Command::Text {
            transform: Transform {
                position: Position { x, y, z },
                rotation: rot,
                scale_x: scale,
                scale_y: scale,
            },
            color: Color::new(r, g, b, a),
            content,
        })
    }

    fn parse_char(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // x ; y ; z ; rot ; sx ; sy ; r ; g ; b ; a ; codepoint
        if parts.len() < 11 {
            return Err(ParseError::MissingParams);
        }

        let x: f32 = parts[0].parse().map_err(|_| ParseError::InvalidNumber)?;
        let y: f32 = parts[1].parse().map_err(|_| ParseError::InvalidNumber)?;
        let z: f32 = parts[2].parse().map_err(|_| ParseError::InvalidNumber)?;
        let rot: f32 = parts[3].parse().map_err(|_| ParseError::InvalidNumber)?;
        let sx: f32 = parts[4].parse().map_err(|_| ParseError::InvalidNumber)?;
        let sy: f32 = parts[5].parse().map_err(|_| ParseError::InvalidNumber)?;
        let r: u8 = parts[6].parse().map_err(|_| ParseError::InvalidNumber)?;
        let g: u8 = parts[7].parse().map_err(|_| ParseError::InvalidNumber)?;
        let b: u8 = parts[8].parse().map_err(|_| ParseError::InvalidNumber)?;
        let a: u8 = parts[9].parse().map_err(|_| ParseError::InvalidNumber)?;
        let codepoint: u32 = parts[10].parse().map_err(|_| ParseError::InvalidNumber)?;

        Ok(Command::Char {
            transform: Transform {
                position: Position { x, y, z },
                rotation: rot,
                scale_x: sx,
                scale_y: sy,
            },
            color: Color::new(r, g, b, a),
            codepoint,
        })
    }

    fn parse_rect(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // x ; y ; z ; w ; h ; rot ; r ; g ; b ; a ; filled
        if parts.len() < 11 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::Rect {
            x: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            y: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            width: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            height: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
            rotation: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
            color: Color::new(
                parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[8].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[9].parse().map_err(|_| ParseError::InvalidNumber)?,
            ),
            filled: parts[10] == "1",
        })
    }

    fn parse_line(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // x1 ; y1 ; x2 ; y2 ; z ; thickness ; r ; g ; b ; a
        if parts.len() < 10 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::Line {
            x1: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            y1: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            x2: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            y2: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
            thickness: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
            color: Color::new(
                parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[8].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[9].parse().map_err(|_| ParseError::InvalidNumber)?,
            ),
        })
    }

    fn parse_circle(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // cx ; cy ; z ; radius ; r ; g ; b ; a ; filled
        if parts.len() < 9 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::Circle {
            cx: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            cy: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            radius: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            color: Color::new(
                parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
            ),
            filled: parts[8] == "1",
        })
    }

    fn parse_ellipse(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // cx ; cy ; z ; rx ; ry ; rot ; r ; g ; b ; a ; filled
        if parts.len() < 11 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::Ellipse {
            cx: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            cy: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            rx: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            ry: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
            rotation: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
            color: Color::new(
                parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[8].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[9].parse().map_err(|_| ParseError::InvalidNumber)?,
            ),
            filled: parts[10] == "1",
        })
    }

    fn parse_arc(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // cx ; cy ; z ; radius ; start_angle ; end_angle ; thickness ; r ; g ; b ; a
        if parts.len() < 11 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::Arc {
            cx: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            cy: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            radius: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            start_angle: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
            end_angle: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
            thickness: parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
            color: Color::new(
                parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[8].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[9].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[10].parse().map_err(|_| ParseError::InvalidNumber)?,
            ),
        })
    }

    fn parse_polygon(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // z ; r ; g ; b ; a ; filled ; n ; x1 ; y1 ; x2 ; y2 ; ...
        if parts.len() < 7 {
            return Err(ParseError::MissingParams);
        }

        let z: f32 = parts[0].parse().map_err(|_| ParseError::InvalidNumber)?;
        let color = Color::new(
            parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
        );
        let filled = parts[5] == "1";
        let n: usize = parts[6].parse().map_err(|_| ParseError::InvalidNumber)?;

        if parts.len() < 7 + n * 2 {
            return Err(ParseError::MissingParams);
        }

        let mut points = Vec::with_capacity(n);
        for i in 0..n {
            let x: f32 = parts[7 + i * 2].parse().map_err(|_| ParseError::InvalidNumber)?;
            let y: f32 = parts[8 + i * 2].parse().map_err(|_| ParseError::InvalidNumber)?;
            points.push((x, y));
        }

        Ok(Command::Polygon { points, z, color, filled })
    }

    fn parse_rounded_rect(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // x ; y ; z ; w ; h ; radius ; r ; g ; b ; a ; filled
        if parts.len() < 11 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::RoundedRect {
            x: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            y: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            width: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            height: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
            radius: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
            color: Color::new(
                parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[8].parse().map_err(|_| ParseError::InvalidNumber)?,
                parts[9].parse().map_err(|_| ParseError::InvalidNumber)?,
            ),
            filled: parts[10] == "1",
        })
    }

    fn parse_clear(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.len() >= 8 {
            // Region clear: x ; y ; w ; h ; r ; g ; b ; a
            Ok(Command::Clear {
                region: Some((
                    parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
                )),
                color: Color::new(
                    parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[7].parse().map_err(|_| ParseError::InvalidNumber)?,
                ),
            })
        } else if parts.len() >= 4 {
            // Full clear: r ; g ; b ; a
            Ok(Command::Clear {
                region: None,
                color: Color::new(
                    parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
                    parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
                ),
            })
        } else {
            Err(ParseError::MissingParams)
        }
    }

    fn parse_viewport(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.len() < 2 {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::Viewport {
            width: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            height: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
        })
    }

    fn parse_image(&self, parts: &[&str]) -> Result<Command, ParseError> {
        // x ; y ; z ; w ; h ; rot ; format ; base64data
        if parts.len() < 8 {
            return Err(ParseError::MissingParams);
        }

        let format = ImageFormat::from_str(parts[6]).ok_or(ParseError::InvalidFormat)?;
        let data = base64::Engine::decode(
            &base64::engine::general_purpose::STANDARD,
            parts[7],
        ).map_err(|_| ParseError::InvalidBase64)?;

        Ok(Command::Image {
            x: parts[0].parse().map_err(|_| ParseError::InvalidNumber)?,
            y: parts[1].parse().map_err(|_| ParseError::InvalidNumber)?,
            z: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
            width: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
            height: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
            rotation: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
            format,
            data,
        })
    }

    fn parse_query(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.is_empty() {
            return Err(ParseError::MissingParams);
        }

        match parts[0] {
            "version" => Ok(Command::QueryVersion),
            "size" => Ok(Command::QuerySize),
            "features" => Ok(Command::QueryFeatures),
            _ => Err(ParseError::UnknownCommand),
        }
    }

    fn parse_input_mode(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.is_empty() {
            return Err(ParseError::MissingParams);
        }

        Ok(Command::InputMode {
            raw: parts[0] == "raw",
        })
    }

    fn parse_cursor(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.is_empty() {
            return Err(ParseError::MissingParams);
        }

        match parts[0] {
            "hide" => Ok(Command::CursorHide),
            "show" => Ok(Command::CursorShow),
            "set" if parts.len() >= 4 => {
                let data = base64::Engine::decode(
                    &base64::engine::general_purpose::STANDARD,
                    parts[1],
                ).map_err(|_| ParseError::InvalidBase64)?;

                Ok(Command::CursorSet {
                    image_data: data,
                    hotspot_x: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
                    hotspot_y: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
                })
            }
            _ => Err(ParseError::InvalidFormat),
        }
    }

    fn parse_layer(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.len() < 2 {
            return Err(ParseError::MissingParams);
        }

        match parts[0] {
            "push" if parts.len() >= 7 => Ok(Command::LayerPush {
                id: parts[1].to_string(),
                x: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
                y: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
                width: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
                height: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
                opacity: parts[6].parse().map_err(|_| ParseError::InvalidNumber)?,
            }),
            "pop" => Ok(Command::LayerPop {
                id: parts[1].to_string(),
            }),
            _ => Err(ParseError::InvalidFormat),
        }
    }

    fn parse_legacy(&self, parts: &[&str]) -> Result<Command, ParseError> {
        if parts.len() < 2 {
            return Err(ParseError::MissingParams);
        }

        match parts[0] {
            "create" if parts.len() >= 6 => Ok(Command::LegacyCreate {
                id: parts[1].to_string(),
                x: parts[2].parse().map_err(|_| ParseError::InvalidNumber)?,
                y: parts[3].parse().map_err(|_| ParseError::InvalidNumber)?,
                cols: parts[4].parse().map_err(|_| ParseError::InvalidNumber)?,
                rows: parts[5].parse().map_err(|_| ParseError::InvalidNumber)?,
                font_size: parts.get(6).and_then(|s| s.parse().ok()).unwrap_or(16.0),
            }),
            "destroy" => Ok(Command::LegacyDestroy {
                id: parts[1].to_string(),
            }),
            "write" if parts.len() >= 3 => {
                let data = base64::Engine::decode(
                    &base64::engine::general_purpose::STANDARD,
                    parts[2],
                ).map_err(|_| ParseError::InvalidBase64)?;

                Ok(Command::LegacyWrite {
                    id: parts[1].to_string(),
                    data,
                })
            }
            "focus" => Ok(Command::LegacyFocus {
                id: parts[1].to_string(),
            }),
            _ => Err(ParseError::InvalidFormat),
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub enum ParseError {
    #[error("invalid UTF-8")]
    InvalidUtf8,
    #[error("not a VTNext sequence")]
    NotVtNext,
    #[error("invalid format")]
    InvalidFormat,
    #[error("missing parameters")]
    MissingParams,
    #[error("invalid number")]
    InvalidNumber,
    #[error("invalid base64")]
    InvalidBase64,
    #[error("unknown command")]
    UnknownCommand,
}
