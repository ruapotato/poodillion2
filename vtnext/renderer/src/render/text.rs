//! Text rendering with vector fonts

use ab_glyph::{Font, FontRef, Glyph, PxScale, ScaleFont};
use glow::HasContext;
use std::collections::HashMap;

/// Cached glyph texture
pub struct GlyphCache {
    texture: glow::Texture,
    width: u32,
    height: u32,
    glyphs: HashMap<CacheKey, CachedGlyph>,
    next_x: u32,
    next_y: u32,
    row_height: u32,
}

#[derive(Hash, Eq, PartialEq, Clone)]
struct CacheKey {
    codepoint: u32,
    size_tenths: u32, // size * 10 for hashing
}

#[derive(Clone)]
pub struct CachedGlyph {
    pub u0: f32,
    pub v0: f32,
    pub u1: f32,
    pub v1: f32,
    pub width: f32,
    pub height: f32,
    pub bearing_x: f32,
    pub bearing_y: f32,
    pub advance: f32,
}

impl GlyphCache {
    pub fn new(gl: &glow::Context) -> Self {
        let (width, height) = (2048, 2048);

        let texture = unsafe {
            let tex = gl.create_texture().expect("Failed to create texture");
            gl.bind_texture(glow::TEXTURE_2D, Some(tex));
            gl.tex_image_2d(
                glow::TEXTURE_2D,
                0,
                glow::R8 as i32,
                width as i32,
                height as i32,
                0,
                glow::RED,
                glow::UNSIGNED_BYTE,
                None,
            );
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_MIN_FILTER, glow::LINEAR as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_MAG_FILTER, glow::LINEAR as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_WRAP_S, glow::CLAMP_TO_EDGE as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_WRAP_T, glow::CLAMP_TO_EDGE as i32);
            tex
        };

        Self {
            texture,
            width,
            height,
            glyphs: HashMap::new(),
            next_x: 0,
            next_y: 0,
            row_height: 0,
        }
    }

    pub fn texture(&self) -> glow::Texture {
        self.texture
    }

    pub fn get_or_create(
        &mut self,
        gl: &glow::Context,
        font: &FontRef,
        codepoint: char,
        size: f32,
    ) -> Option<CachedGlyph> {
        let key = CacheKey {
            codepoint: codepoint as u32,
            size_tenths: (size * 10.0) as u32,
        };

        if let Some(cached) = self.glyphs.get(&key) {
            return Some(cached.clone());
        }

        // Rasterize glyph
        let scale = PxScale::from(size);
        let scaled_font = font.as_scaled(scale);

        let glyph_id = font.glyph_id(codepoint);
        let glyph = glyph_id.with_scale(scale);

        if let Some(outlined) = font.outline_glyph(glyph) {
            let bounds = outlined.px_bounds();
            let glyph_width = bounds.width() as u32;
            let glyph_height = bounds.height() as u32;

            if glyph_width == 0 || glyph_height == 0 {
                return None;
            }

            // Check if we need to move to next row
            if self.next_x + glyph_width > self.width {
                self.next_x = 0;
                self.next_y += self.row_height + 1;
                self.row_height = 0;
            }

            // Check if we're out of space
            if self.next_y + glyph_height > self.height {
                log::warn!("Glyph cache full!");
                return None;
            }

            // Rasterize to buffer
            let mut buffer = vec![0u8; (glyph_width * glyph_height) as usize];
            outlined.draw(|x, y, c| {
                let idx = (y * glyph_width + x) as usize;
                if idx < buffer.len() {
                    buffer[idx] = (c * 255.0) as u8;
                }
            });

            // Upload to texture
            unsafe {
                gl.bind_texture(glow::TEXTURE_2D, Some(self.texture));
                gl.tex_sub_image_2d(
                    glow::TEXTURE_2D,
                    0,
                    self.next_x as i32,
                    self.next_y as i32,
                    glyph_width as i32,
                    glyph_height as i32,
                    glow::RED,
                    glow::UNSIGNED_BYTE,
                    glow::PixelUnpackData::Slice(&buffer),
                );
            }

            let cached = CachedGlyph {
                u0: self.next_x as f32 / self.width as f32,
                v0: self.next_y as f32 / self.height as f32,
                u1: (self.next_x + glyph_width) as f32 / self.width as f32,
                v1: (self.next_y + glyph_height) as f32 / self.height as f32,
                width: glyph_width as f32,
                height: glyph_height as f32,
                bearing_x: bounds.min.x,
                bearing_y: bounds.min.y,
                advance: scaled_font.h_advance(glyph_id),
            };

            self.glyphs.insert(key.clone(), cached.clone());

            self.next_x += glyph_width + 1;
            self.row_height = self.row_height.max(glyph_height);

            Some(cached)
        } else {
            None
        }
    }
}

/// Text renderer using OpenGL
pub struct TextRenderer {
    program: glow::Program,
    vao: glow::VertexArray,
    vbo: glow::Buffer,
    glyph_cache: GlyphCache,
}

impl TextRenderer {
    pub fn new(gl: &glow::Context) -> Self {
        let program = Self::create_shader_program(gl);
        let (vao, vbo) = Self::create_buffers(gl);
        let glyph_cache = GlyphCache::new(gl);

        Self {
            program,
            vao,
            vbo,
            glyph_cache,
        }
    }

    fn create_shader_program(gl: &glow::Context) -> glow::Program {
        unsafe {
            let program = gl.create_program().expect("Cannot create program");

            let vertex_shader = gl.create_shader(glow::VERTEX_SHADER).expect("Cannot create shader");
            gl.shader_source(vertex_shader, VERTEX_SHADER);
            gl.compile_shader(vertex_shader);

            let fragment_shader = gl.create_shader(glow::FRAGMENT_SHADER).expect("Cannot create shader");
            gl.shader_source(fragment_shader, FRAGMENT_SHADER);
            gl.compile_shader(fragment_shader);

            gl.attach_shader(program, vertex_shader);
            gl.attach_shader(program, fragment_shader);
            gl.link_program(program);

            gl.delete_shader(vertex_shader);
            gl.delete_shader(fragment_shader);

            program
        }
    }

    fn create_buffers(gl: &glow::Context) -> (glow::VertexArray, glow::Buffer) {
        unsafe {
            let vao = gl.create_vertex_array().expect("Cannot create VAO");
            let vbo = gl.create_buffer().expect("Cannot create VBO");

            gl.bind_vertex_array(Some(vao));
            gl.bind_buffer(glow::ARRAY_BUFFER, Some(vbo));

            // Reserve space for quads (6 vertices per glyph, position + texcoord + color)
            gl.buffer_data_size(glow::ARRAY_BUFFER, 1024 * 1024, glow::DYNAMIC_DRAW);

            // Position (x, y, z)
            gl.enable_vertex_attrib_array(0);
            gl.vertex_attrib_pointer_f32(0, 3, glow::FLOAT, false, 36, 0);

            // TexCoord (u, v)
            gl.enable_vertex_attrib_array(1);
            gl.vertex_attrib_pointer_f32(1, 2, glow::FLOAT, false, 36, 12);

            // Color (r, g, b, a)
            gl.enable_vertex_attrib_array(2);
            gl.vertex_attrib_pointer_f32(2, 4, glow::FLOAT, false, 36, 20);

            (vao, vbo)
        }
    }

    pub fn draw_text(
        &mut self,
        gl: &glow::Context,
        font: &FontRef,
        text: &str,
        x: f32,
        y: f32,
        z: f32,
        rotation: f32,
        scale: f32,
        color: [f32; 4],
        viewport: (f32, f32),
    ) {
        let mut vertices: Vec<f32> = Vec::new();
        let mut cursor_x = 0.0f32;

        let font_size = 24.0 * scale;

        for ch in text.chars() {
            if let Some(glyph) = self.glyph_cache.get_or_create(gl, font, ch, font_size) {
                let gx = cursor_x + glyph.bearing_x;
                let gy = glyph.bearing_y;

                // Build quad vertices (2 triangles)
                let positions = [
                    (gx, gy),
                    (gx + glyph.width, gy),
                    (gx + glyph.width, gy + glyph.height),
                    (gx, gy),
                    (gx + glyph.width, gy + glyph.height),
                    (gx, gy + glyph.height),
                ];

                let texcoords = [
                    (glyph.u0, glyph.v0),
                    (glyph.u1, glyph.v0),
                    (glyph.u1, glyph.v1),
                    (glyph.u0, glyph.v0),
                    (glyph.u1, glyph.v1),
                    (glyph.u0, glyph.v1),
                ];

                let rot_rad = rotation.to_radians();
                let cos_r = rot_rad.cos();
                let sin_r = rot_rad.sin();

                for i in 0..6 {
                    let (px, py) = positions[i];
                    // Apply rotation around origin (0,0), then translate
                    let rx = px * cos_r - py * sin_r + x;
                    let ry = px * sin_r + py * cos_r + y;

                    vertices.push(rx);
                    vertices.push(ry);
                    vertices.push(z);
                    vertices.push(texcoords[i].0);
                    vertices.push(texcoords[i].1);
                    vertices.extend_from_slice(&color);
                }

                cursor_x += glyph.advance;
            } else if ch == ' ' {
                cursor_x += font_size * 0.3;
            }
        }

        if vertices.is_empty() {
            return;
        }

        unsafe {
            gl.use_program(Some(self.program));

            let proj_loc = gl.get_uniform_location(self.program, "projection");
            let proj = orthographic_projection(viewport.0, viewport.1);
            gl.uniform_matrix_4_f32_slice(proj_loc.as_ref(), false, &proj);

            let tex_loc = gl.get_uniform_location(self.program, "glyph_texture");
            gl.uniform_1_i32(tex_loc.as_ref(), 0);

            gl.active_texture(glow::TEXTURE0);
            gl.bind_texture(glow::TEXTURE_2D, Some(self.glyph_cache.texture()));

            gl.bind_vertex_array(Some(self.vao));
            gl.bind_buffer(glow::ARRAY_BUFFER, Some(self.vbo));

            let bytes: &[u8] = bytemuck::cast_slice(&vertices);
            gl.buffer_sub_data_u8_slice(glow::ARRAY_BUFFER, 0, bytes);

            gl.enable(glow::BLEND);
            gl.blend_func(glow::SRC_ALPHA, glow::ONE_MINUS_SRC_ALPHA);

            gl.draw_arrays(glow::TRIANGLES, 0, (vertices.len() / 9) as i32);
        }
    }
}

fn orthographic_projection(width: f32, height: f32) -> [f32; 16] {
    let left = 0.0;
    let right = width;
    let bottom = height;
    let top = 0.0;
    let near = -1000.0;
    let far = 1000.0;

    [
        2.0 / (right - left), 0.0, 0.0, 0.0,
        0.0, 2.0 / (top - bottom), 0.0, 0.0,
        0.0, 0.0, -2.0 / (far - near), 0.0,
        -(right + left) / (right - left),
        -(top + bottom) / (top - bottom),
        -(far + near) / (far - near),
        1.0,
    ]
}

const VERTEX_SHADER: &str = r#"
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec2 aTexCoord;
layout (location = 2) in vec4 aColor;

out vec2 TexCoord;
out vec4 Color;

uniform mat4 projection;

void main() {
    gl_Position = projection * vec4(aPos, 1.0);
    TexCoord = aTexCoord;
    Color = aColor;
}
"#;

const FRAGMENT_SHADER: &str = r#"
#version 330 core
in vec2 TexCoord;
in vec4 Color;

out vec4 FragColor;

uniform sampler2D glyph_texture;

void main() {
    float alpha = texture(glyph_texture, TexCoord).r;
    FragColor = vec4(Color.rgb, Color.a * alpha);
}
"#;

// Need bytemuck for casting
use bytemuck;
