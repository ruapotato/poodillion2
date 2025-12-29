//! Image rendering support

use glow::HasContext;
use image::{DynamicImage, GenericImageView};
use std::collections::HashMap;

/// Cached texture from image data
pub struct CachedTexture {
    pub texture: glow::Texture,
    pub width: u32,
    pub height: u32,
}

/// Image renderer with texture caching
pub struct ImageRenderer {
    program: glow::Program,
    vao: glow::VertexArray,
    vbo: glow::Buffer,
    texture_cache: HashMap<u64, CachedTexture>,
    next_cache_id: u64,
}

impl ImageRenderer {
    pub fn new(gl: &glow::Context) -> Self {
        let program = Self::create_shader_program(gl);
        let (vao, vbo) = Self::create_buffers(gl);

        Self {
            program,
            vao,
            vbo,
            texture_cache: HashMap::new(),
            next_cache_id: 0,
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
            gl.buffer_data_size(glow::ARRAY_BUFFER, 64 * 1024, glow::DYNAMIC_DRAW);

            // Position (x, y, z)
            gl.enable_vertex_attrib_array(0);
            gl.vertex_attrib_pointer_f32(0, 3, glow::FLOAT, false, 20, 0);

            // TexCoord (u, v)
            gl.enable_vertex_attrib_array(1);
            gl.vertex_attrib_pointer_f32(1, 2, glow::FLOAT, false, 20, 12);

            (vao, vbo)
        }
    }

    /// Load image data into a texture
    pub fn load_texture(
        &mut self,
        gl: &glow::Context,
        data: &[u8],
        format: &str,
    ) -> Option<u64> {
        let img = match format {
            "png" => image::load_from_memory_with_format(data, image::ImageFormat::Png).ok()?,
            "jpg" | "jpeg" => image::load_from_memory_with_format(data, image::ImageFormat::Jpeg).ok()?,
            "rgba" => {
                // Raw RGBA data - need width/height from somewhere
                // For now, assume square
                let pixels = data.len() / 4;
                let side = (pixels as f64).sqrt() as u32;
                if side * side * 4 != data.len() as u32 {
                    return None;
                }
                DynamicImage::ImageRgba8(
                    image::RgbaImage::from_raw(side, side, data.to_vec())?
                )
            }
            _ => return None,
        };

        let rgba = img.to_rgba8();
        let (width, height) = img.dimensions();

        let texture = unsafe {
            let tex = gl.create_texture().expect("Failed to create texture");
            gl.bind_texture(glow::TEXTURE_2D, Some(tex));

            gl.tex_image_2d(
                glow::TEXTURE_2D,
                0,
                glow::RGBA as i32,
                width as i32,
                height as i32,
                0,
                glow::RGBA,
                glow::UNSIGNED_BYTE,
                Some(rgba.as_raw()),
            );

            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_MIN_FILTER, glow::LINEAR as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_MAG_FILTER, glow::LINEAR as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_WRAP_S, glow::CLAMP_TO_EDGE as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_WRAP_T, glow::CLAMP_TO_EDGE as i32);

            tex
        };

        let id = self.next_cache_id;
        self.next_cache_id += 1;

        self.texture_cache.insert(id, CachedTexture {
            texture,
            width,
            height,
        });

        Some(id)
    }

    /// Draw an image
    pub fn draw_image(
        &mut self,
        gl: &glow::Context,
        data: &[u8],
        format: &str,
        x: f32,
        y: f32,
        z: f32,
        width: f32,
        height: f32,
        rotation: f32,
        viewport: (f32, f32),
    ) {
        // Load texture (could cache based on data hash in production)
        let img = match format {
            "png" => image::load_from_memory_with_format(data, image::ImageFormat::Png),
            "jpg" | "jpeg" => image::load_from_memory_with_format(data, image::ImageFormat::Jpeg),
            _ => return,
        };

        let img = match img {
            Ok(i) => i,
            Err(_) => return,
        };

        let rgba = img.to_rgba8();
        let (img_width, img_height) = img.dimensions();

        // Use provided dimensions or native
        let draw_width = if width > 0.0 { width } else { img_width as f32 };
        let draw_height = if height > 0.0 { height } else { img_height as f32 };

        let texture = unsafe {
            let tex = gl.create_texture().expect("Failed to create texture");
            gl.bind_texture(glow::TEXTURE_2D, Some(tex));

            gl.tex_image_2d(
                glow::TEXTURE_2D,
                0,
                glow::RGBA as i32,
                img_width as i32,
                img_height as i32,
                0,
                glow::RGBA,
                glow::UNSIGNED_BYTE,
                Some(rgba.as_raw()),
            );

            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_MIN_FILTER, glow::LINEAR as i32);
            gl.tex_parameter_i32(glow::TEXTURE_2D, glow::TEXTURE_MAG_FILTER, glow::LINEAR as i32);

            tex
        };

        // Build rotated quad
        let rot_rad = rotation.to_radians();
        let cos_r = rot_rad.cos();
        let sin_r = rot_rad.sin();

        let hw = draw_width / 2.0;
        let hh = draw_height / 2.0;

        let corners = [
            (-hw, -hh, 0.0, 0.0),
            (hw, -hh, 1.0, 0.0),
            (hw, hh, 1.0, 1.0),
            (-hw, hh, 0.0, 1.0),
        ];

        let transformed: Vec<(f32, f32, f32, f32)> = corners
            .iter()
            .map(|(px, py, u, v)| {
                let rx = px * cos_r - py * sin_r + x + hw;
                let ry = px * sin_r + py * cos_r + y + hh;
                (rx, ry, *u, *v)
            })
            .collect();

        let vertices = vec![
            transformed[0].0, transformed[0].1, z, transformed[0].2, transformed[0].3,
            transformed[1].0, transformed[1].1, z, transformed[1].2, transformed[1].3,
            transformed[2].0, transformed[2].1, z, transformed[2].2, transformed[2].3,
            transformed[0].0, transformed[0].1, z, transformed[0].2, transformed[0].3,
            transformed[2].0, transformed[2].1, z, transformed[2].2, transformed[2].3,
            transformed[3].0, transformed[3].1, z, transformed[3].2, transformed[3].3,
        ];

        unsafe {
            gl.use_program(Some(self.program));

            let proj_loc = gl.get_uniform_location(self.program, "projection");
            let proj = orthographic_projection(viewport.0, viewport.1);
            gl.uniform_matrix_4_f32_slice(proj_loc.as_ref(), false, &proj);

            let tex_loc = gl.get_uniform_location(self.program, "tex");
            gl.uniform_1_i32(tex_loc.as_ref(), 0);

            gl.active_texture(glow::TEXTURE0);
            gl.bind_texture(glow::TEXTURE_2D, Some(texture));

            gl.bind_vertex_array(Some(self.vao));
            gl.bind_buffer(glow::ARRAY_BUFFER, Some(self.vbo));

            let bytes: &[u8] = bytemuck::cast_slice(&vertices);
            gl.buffer_sub_data_u8_slice(glow::ARRAY_BUFFER, 0, bytes);

            gl.enable(glow::BLEND);
            gl.blend_func(glow::SRC_ALPHA, glow::ONE_MINUS_SRC_ALPHA);

            gl.draw_arrays(glow::TRIANGLES, 0, 6);

            // Clean up texture (in production, cache this)
            gl.delete_texture(texture);
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

out vec2 TexCoord;

uniform mat4 projection;

void main() {
    gl_Position = projection * vec4(aPos, 1.0);
    TexCoord = aTexCoord;
}
"#;

const FRAGMENT_SHADER: &str = r#"
#version 330 core
in vec2 TexCoord;

out vec4 FragColor;

uniform sampler2D tex;

void main() {
    FragColor = texture(tex, TexCoord);
}
"#;
