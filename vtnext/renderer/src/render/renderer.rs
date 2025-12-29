//! Main renderer that combines all rendering subsystems

use super::{ImageRenderer, ShapeRenderer, TextRenderer};
use crate::protocol::{Color, Command, ImageFormat};
use ab_glyph::FontRef;
use glow::HasContext;

pub struct Renderer {
    pub text_renderer: TextRenderer,
    pub shape_renderer: ShapeRenderer,
    pub image_renderer: ImageRenderer,
    viewport: (f32, f32),
    clear_color: Color,
}

impl Renderer {
    pub fn new(gl: &glow::Context) -> Self {
        Self {
            text_renderer: TextRenderer::new(gl),
            shape_renderer: ShapeRenderer::new(gl),
            image_renderer: ImageRenderer::new(gl),
            viewport: (800.0, 600.0),
            clear_color: Color::new(0, 0, 0, 255),
        }
    }

    pub fn set_viewport(&mut self, width: f32, height: f32) {
        self.viewport = (width, height);
    }

    pub fn viewport(&self) -> (f32, f32) {
        self.viewport
    }

    pub fn clear(&self, gl: &glow::Context) {
        let [r, g, b, a] = self.clear_color.as_floats();
        unsafe {
            gl.clear_color(r, g, b, a);
            gl.clear(glow::COLOR_BUFFER_BIT | glow::DEPTH_BUFFER_BIT);
        }
    }

    pub fn execute_command(&mut self, gl: &glow::Context, font: &FontRef, cmd: &Command) {
        match cmd {
            Command::Clear { color, region } => {
                if region.is_none() {
                    self.clear_color = *color;
                    self.clear(gl);
                } else {
                    let [r, g, b, a] = color.as_floats();
                    unsafe {
                        gl.clear_color(r, g, b, a);
                        gl.clear(glow::COLOR_BUFFER_BIT);
                    }
                }
            }

            Command::Viewport { width, height } => {
                self.set_viewport(*width, *height);
                unsafe {
                    gl.viewport(0, 0, *width as i32, *height as i32);
                }
            }

            Command::Text { transform, color, content } => {
                self.text_renderer.draw_text(
                    gl,
                    font,
                    content,
                    transform.position.x,
                    transform.position.y,
                    transform.position.z,
                    transform.rotation,
                    transform.scale_x,
                    color.as_floats(),
                    self.viewport,
                );
            }

            Command::Char { transform, color, codepoint } => {
                if let Some(ch) = char::from_u32(*codepoint) {
                    let s = ch.to_string();
                    self.text_renderer.draw_text(
                        gl,
                        font,
                        &s,
                        transform.position.x,
                        transform.position.y,
                        transform.position.z,
                        transform.rotation,
                        transform.scale_x,
                        color.as_floats(),
                        self.viewport,
                    );
                }
            }

            Command::Rect { x, y, z, width, height, rotation, color, filled } => {
                self.shape_renderer.draw_rect(
                    gl,
                    *x,
                    *y,
                    *z,
                    *width,
                    *height,
                    *rotation,
                    color.as_floats(),
                    *filled,
                    self.viewport,
                );
            }

            Command::Line { x1, y1, x2, y2, z, thickness, color } => {
                self.shape_renderer.draw_line(
                    gl,
                    *x1,
                    *y1,
                    *x2,
                    *y2,
                    *z,
                    *thickness,
                    color.as_floats(),
                    self.viewport,
                );
            }

            Command::Circle { cx, cy, z, radius, color, filled } => {
                self.shape_renderer.draw_circle(
                    gl,
                    *cx,
                    *cy,
                    *z,
                    *radius,
                    color.as_floats(),
                    *filled,
                    32, // segments
                    self.viewport,
                );
            }

            Command::Ellipse { cx, cy, z, rx, ry, rotation, color, filled } => {
                self.shape_renderer.draw_ellipse(
                    gl,
                    *cx,
                    *cy,
                    *z,
                    *rx,
                    *ry,
                    *rotation,
                    color.as_floats(),
                    *filled,
                    32, // segments
                    self.viewport,
                );
            }

            Command::Arc { cx, cy, z, radius, start_angle, end_angle, thickness, color } => {
                self.shape_renderer.draw_arc(
                    gl,
                    *cx,
                    *cy,
                    *z,
                    *radius,
                    *start_angle,
                    *end_angle,
                    *thickness,
                    color.as_floats(),
                    32, // segments
                    self.viewport,
                );
            }

            Command::Polygon { points, z, color, filled } => {
                self.shape_renderer.draw_polygon(
                    gl,
                    points,
                    *z,
                    color.as_floats(),
                    *filled,
                    self.viewport,
                );
            }

            Command::RoundedRect { x, y, z, width, height, radius, color, filled } => {
                self.shape_renderer.draw_rounded_rect(
                    gl,
                    *x,
                    *y,
                    *z,
                    *width,
                    *height,
                    *radius,
                    color.as_floats(),
                    *filled,
                    self.viewport,
                );
            }

            Command::Image { x, y, z, width, height, rotation, format, data } => {
                let fmt = match format {
                    ImageFormat::Png => "png",
                    ImageFormat::Jpg => "jpg",
                    ImageFormat::Rgba => "rgba",
                };
                self.image_renderer.draw_image(
                    gl,
                    data,
                    fmt,
                    *x,
                    *y,
                    *z,
                    *width,
                    *height,
                    *rotation,
                    self.viewport,
                );
            }

            Command::LayerPush { .. } | Command::LayerPop { .. } => {
                log::warn!("Layer operations not yet implemented");
            }

            Command::LegacyCreate { .. }
            | Command::LegacyDestroy { .. }
            | Command::LegacyWrite { .. }
            | Command::LegacyFocus { .. } => {
                log::warn!("Legacy VT100 mode not yet implemented");
            }

            Command::QueryVersion
            | Command::QuerySize
            | Command::QueryFeatures
            | Command::InputMode { .. }
            | Command::CursorHide
            | Command::CursorShow
            | Command::CursorSet { .. } => {
                // Handled by main loop, not renderer
            }
        }
    }
}
