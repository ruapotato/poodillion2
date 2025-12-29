//! Shape rendering (rectangles, lines, etc.)

use glow::HasContext;

pub struct ShapeRenderer {
    program: glow::Program,
    vao: glow::VertexArray,
    vbo: glow::Buffer,
}

impl ShapeRenderer {
    pub fn new(gl: &glow::Context) -> Self {
        let program = Self::create_shader_program(gl);
        let (vao, vbo) = Self::create_buffers(gl);

        Self { program, vao, vbo }
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
            gl.vertex_attrib_pointer_f32(0, 3, glow::FLOAT, false, 28, 0);

            // Color (r, g, b, a)
            gl.enable_vertex_attrib_array(1);
            gl.vertex_attrib_pointer_f32(1, 4, glow::FLOAT, false, 28, 12);

            (vao, vbo)
        }
    }

    pub fn draw_rect(
        &self,
        gl: &glow::Context,
        x: f32,
        y: f32,
        z: f32,
        width: f32,
        height: f32,
        rotation: f32,
        color: [f32; 4],
        filled: bool,
        viewport: (f32, f32),
    ) {
        let rot_rad = rotation.to_radians();
        let cos_r = rot_rad.cos();
        let sin_r = rot_rad.sin();

        // Center of rectangle
        let cx = width / 2.0;
        let cy = height / 2.0;

        // Corner offsets from center
        let corners = [
            (-cx, -cy),
            (cx, -cy),
            (cx, cy),
            (-cx, cy),
        ];

        // Rotate and translate
        let transformed: Vec<(f32, f32)> = corners
            .iter()
            .map(|(px, py)| {
                let rx = px * cos_r - py * sin_r + x + cx;
                let ry = px * sin_r + py * cos_r + y + cy;
                (rx, ry)
            })
            .collect();

        let vertices: Vec<f32> = if filled {
            // Two triangles
            vec![
                transformed[0].0, transformed[0].1, z, color[0], color[1], color[2], color[3],
                transformed[1].0, transformed[1].1, z, color[0], color[1], color[2], color[3],
                transformed[2].0, transformed[2].1, z, color[0], color[1], color[2], color[3],
                transformed[0].0, transformed[0].1, z, color[0], color[1], color[2], color[3],
                transformed[2].0, transformed[2].1, z, color[0], color[1], color[2], color[3],
                transformed[3].0, transformed[3].1, z, color[0], color[1], color[2], color[3],
            ]
        } else {
            // Line loop (as lines)
            vec![
                transformed[0].0, transformed[0].1, z, color[0], color[1], color[2], color[3],
                transformed[1].0, transformed[1].1, z, color[0], color[1], color[2], color[3],
                transformed[1].0, transformed[1].1, z, color[0], color[1], color[2], color[3],
                transformed[2].0, transformed[2].1, z, color[0], color[1], color[2], color[3],
                transformed[2].0, transformed[2].1, z, color[0], color[1], color[2], color[3],
                transformed[3].0, transformed[3].1, z, color[0], color[1], color[2], color[3],
                transformed[3].0, transformed[3].1, z, color[0], color[1], color[2], color[3],
                transformed[0].0, transformed[0].1, z, color[0], color[1], color[2], color[3],
            ]
        };

        self.draw_vertices(gl, &vertices, if filled { glow::TRIANGLES } else { glow::LINES }, viewport);
    }

    pub fn draw_line(
        &self,
        gl: &glow::Context,
        x1: f32,
        y1: f32,
        x2: f32,
        y2: f32,
        z: f32,
        thickness: f32,
        color: [f32; 4],
        viewport: (f32, f32),
    ) {
        // Calculate perpendicular offset for thickness
        let dx = x2 - x1;
        let dy = y2 - y1;
        let len = (dx * dx + dy * dy).sqrt();

        if len < 0.001 {
            return;
        }

        let nx = -dy / len * thickness / 2.0;
        let ny = dx / len * thickness / 2.0;

        let vertices = vec![
            x1 + nx, y1 + ny, z, color[0], color[1], color[2], color[3],
            x1 - nx, y1 - ny, z, color[0], color[1], color[2], color[3],
            x2 - nx, y2 - ny, z, color[0], color[1], color[2], color[3],
            x1 + nx, y1 + ny, z, color[0], color[1], color[2], color[3],
            x2 - nx, y2 - ny, z, color[0], color[1], color[2], color[3],
            x2 + nx, y2 + ny, z, color[0], color[1], color[2], color[3],
        ];

        self.draw_vertices(gl, &vertices, glow::TRIANGLES, viewport);
    }

    /// Draw a circle
    pub fn draw_circle(
        &self,
        gl: &glow::Context,
        cx: f32,
        cy: f32,
        z: f32,
        radius: f32,
        color: [f32; 4],
        filled: bool,
        segments: u32,
        viewport: (f32, f32),
    ) {
        let segments = segments.max(8);
        let mut vertices = Vec::new();

        if filled {
            // Triangle fan from center
            for i in 0..segments {
                let angle1 = (i as f32 / segments as f32) * std::f32::consts::TAU;
                let angle2 = ((i + 1) as f32 / segments as f32) * std::f32::consts::TAU;

                // Center
                vertices.extend_from_slice(&[cx, cy, z, color[0], color[1], color[2], color[3]]);
                // Point 1
                vertices.extend_from_slice(&[
                    cx + radius * angle1.cos(),
                    cy + radius * angle1.sin(),
                    z, color[0], color[1], color[2], color[3],
                ]);
                // Point 2
                vertices.extend_from_slice(&[
                    cx + radius * angle2.cos(),
                    cy + radius * angle2.sin(),
                    z, color[0], color[1], color[2], color[3],
                ]);
            }
            self.draw_vertices(gl, &vertices, glow::TRIANGLES, viewport);
        } else {
            // Line loop
            for i in 0..segments {
                let angle1 = (i as f32 / segments as f32) * std::f32::consts::TAU;
                let angle2 = ((i + 1) as f32 / segments as f32) * std::f32::consts::TAU;

                vertices.extend_from_slice(&[
                    cx + radius * angle1.cos(),
                    cy + radius * angle1.sin(),
                    z, color[0], color[1], color[2], color[3],
                ]);
                vertices.extend_from_slice(&[
                    cx + radius * angle2.cos(),
                    cy + radius * angle2.sin(),
                    z, color[0], color[1], color[2], color[3],
                ]);
            }
            self.draw_vertices(gl, &vertices, glow::LINES, viewport);
        }
    }

    /// Draw an ellipse
    pub fn draw_ellipse(
        &self,
        gl: &glow::Context,
        cx: f32,
        cy: f32,
        z: f32,
        rx: f32,
        ry: f32,
        rotation: f32,
        color: [f32; 4],
        filled: bool,
        segments: u32,
        viewport: (f32, f32),
    ) {
        let segments = segments.max(8);
        let rot_rad = rotation.to_radians();
        let cos_r = rot_rad.cos();
        let sin_r = rot_rad.sin();

        let mut vertices = Vec::new();

        if filled {
            for i in 0..segments {
                let angle1 = (i as f32 / segments as f32) * std::f32::consts::TAU;
                let angle2 = ((i + 1) as f32 / segments as f32) * std::f32::consts::TAU;

                // Center
                vertices.extend_from_slice(&[cx, cy, z, color[0], color[1], color[2], color[3]]);

                // Point 1 (rotated)
                let px1 = rx * angle1.cos();
                let py1 = ry * angle1.sin();
                let x1 = cx + px1 * cos_r - py1 * sin_r;
                let y1 = cy + px1 * sin_r + py1 * cos_r;
                vertices.extend_from_slice(&[x1, y1, z, color[0], color[1], color[2], color[3]]);

                // Point 2 (rotated)
                let px2 = rx * angle2.cos();
                let py2 = ry * angle2.sin();
                let x2 = cx + px2 * cos_r - py2 * sin_r;
                let y2 = cy + px2 * sin_r + py2 * cos_r;
                vertices.extend_from_slice(&[x2, y2, z, color[0], color[1], color[2], color[3]]);
            }
            self.draw_vertices(gl, &vertices, glow::TRIANGLES, viewport);
        } else {
            for i in 0..segments {
                let angle1 = (i as f32 / segments as f32) * std::f32::consts::TAU;
                let angle2 = ((i + 1) as f32 / segments as f32) * std::f32::consts::TAU;

                let px1 = rx * angle1.cos();
                let py1 = ry * angle1.sin();
                let x1 = cx + px1 * cos_r - py1 * sin_r;
                let y1 = cy + px1 * sin_r + py1 * cos_r;

                let px2 = rx * angle2.cos();
                let py2 = ry * angle2.sin();
                let x2 = cx + px2 * cos_r - py2 * sin_r;
                let y2 = cy + px2 * sin_r + py2 * cos_r;

                vertices.extend_from_slice(&[x1, y1, z, color[0], color[1], color[2], color[3]]);
                vertices.extend_from_slice(&[x2, y2, z, color[0], color[1], color[2], color[3]]);
            }
            self.draw_vertices(gl, &vertices, glow::LINES, viewport);
        }
    }

    /// Draw a polygon from a list of points
    pub fn draw_polygon(
        &self,
        gl: &glow::Context,
        points: &[(f32, f32)],
        z: f32,
        color: [f32; 4],
        filled: bool,
        viewport: (f32, f32),
    ) {
        if points.len() < 3 {
            return;
        }

        let mut vertices = Vec::new();

        if filled {
            // Simple triangle fan from first vertex (works for convex polygons)
            for i in 1..points.len() - 1 {
                vertices.extend_from_slice(&[
                    points[0].0, points[0].1, z, color[0], color[1], color[2], color[3],
                ]);
                vertices.extend_from_slice(&[
                    points[i].0, points[i].1, z, color[0], color[1], color[2], color[3],
                ]);
                vertices.extend_from_slice(&[
                    points[i + 1].0, points[i + 1].1, z, color[0], color[1], color[2], color[3],
                ]);
            }
            self.draw_vertices(gl, &vertices, glow::TRIANGLES, viewport);
        } else {
            // Line loop
            for i in 0..points.len() {
                let next = (i + 1) % points.len();
                vertices.extend_from_slice(&[
                    points[i].0, points[i].1, z, color[0], color[1], color[2], color[3],
                ]);
                vertices.extend_from_slice(&[
                    points[next].0, points[next].1, z, color[0], color[1], color[2], color[3],
                ]);
            }
            self.draw_vertices(gl, &vertices, glow::LINES, viewport);
        }
    }

    /// Draw an arc
    pub fn draw_arc(
        &self,
        gl: &glow::Context,
        cx: f32,
        cy: f32,
        z: f32,
        radius: f32,
        start_angle: f32,
        end_angle: f32,
        thickness: f32,
        color: [f32; 4],
        segments: u32,
        viewport: (f32, f32),
    ) {
        let segments = segments.max(8);
        let start_rad = start_angle.to_radians();
        let end_rad = end_angle.to_radians();
        let angle_span = end_rad - start_rad;

        let mut vertices = Vec::new();

        for i in 0..segments {
            let t1 = i as f32 / segments as f32;
            let t2 = (i + 1) as f32 / segments as f32;
            let angle1 = start_rad + angle_span * t1;
            let angle2 = start_rad + angle_span * t2;

            let inner_r = radius - thickness / 2.0;
            let outer_r = radius + thickness / 2.0;

            // Quad for this segment
            let x1_inner = cx + inner_r * angle1.cos();
            let y1_inner = cy + inner_r * angle1.sin();
            let x1_outer = cx + outer_r * angle1.cos();
            let y1_outer = cy + outer_r * angle1.sin();
            let x2_inner = cx + inner_r * angle2.cos();
            let y2_inner = cy + inner_r * angle2.sin();
            let x2_outer = cx + outer_r * angle2.cos();
            let y2_outer = cy + outer_r * angle2.sin();

            // Two triangles
            vertices.extend_from_slice(&[
                x1_inner, y1_inner, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x1_outer, y1_outer, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x2_outer, y2_outer, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x1_inner, y1_inner, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x2_outer, y2_outer, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x2_inner, y2_inner, z, color[0], color[1], color[2], color[3],
            ]);
        }

        self.draw_vertices(gl, &vertices, glow::TRIANGLES, viewport);
    }

    /// Draw a rounded rectangle
    pub fn draw_rounded_rect(
        &self,
        gl: &glow::Context,
        x: f32,
        y: f32,
        z: f32,
        width: f32,
        height: f32,
        radius: f32,
        color: [f32; 4],
        filled: bool,
        viewport: (f32, f32),
    ) {
        let radius = radius.min(width / 2.0).min(height / 2.0);
        let segments_per_corner = 8;

        let mut vertices = Vec::new();

        if filled {
            // Center rectangle
            let cx = x + width / 2.0;
            let cy = y + height / 2.0;

            // Main body (cross shape)
            // Horizontal bar
            self.add_rect_vertices(&mut vertices, x + radius, y, width - 2.0 * radius, height, z, color);
            // Vertical bar (top)
            self.add_rect_vertices(&mut vertices, x, y + radius, radius, height - 2.0 * radius, z, color);
            // Vertical bar (bottom)
            self.add_rect_vertices(&mut vertices, x + width - radius, y + radius, radius, height - 2.0 * radius, z, color);

            // Corners
            self.add_corner_vertices(&mut vertices, x + radius, y + radius, z, radius, 180.0, 270.0, segments_per_corner, color);
            self.add_corner_vertices(&mut vertices, x + width - radius, y + radius, z, radius, 270.0, 360.0, segments_per_corner, color);
            self.add_corner_vertices(&mut vertices, x + width - radius, y + height - radius, z, radius, 0.0, 90.0, segments_per_corner, color);
            self.add_corner_vertices(&mut vertices, x + radius, y + height - radius, z, radius, 90.0, 180.0, segments_per_corner, color);

            self.draw_vertices(gl, &vertices, glow::TRIANGLES, viewport);
        } else {
            // Outline
            // Top edge
            vertices.extend_from_slice(&[
                x + radius, y, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x + width - radius, y, z, color[0], color[1], color[2], color[3],
            ]);

            // Top-right corner
            self.add_arc_vertices(&mut vertices, x + width - radius, y + radius, z, radius, -90.0, 0.0, segments_per_corner, color);

            // Right edge
            vertices.extend_from_slice(&[
                x + width, y + radius, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x + width, y + height - radius, z, color[0], color[1], color[2], color[3],
            ]);

            // Bottom-right corner
            self.add_arc_vertices(&mut vertices, x + width - radius, y + height - radius, z, radius, 0.0, 90.0, segments_per_corner, color);

            // Bottom edge
            vertices.extend_from_slice(&[
                x + width - radius, y + height, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x + radius, y + height, z, color[0], color[1], color[2], color[3],
            ]);

            // Bottom-left corner
            self.add_arc_vertices(&mut vertices, x + radius, y + height - radius, z, radius, 90.0, 180.0, segments_per_corner, color);

            // Left edge
            vertices.extend_from_slice(&[
                x, y + height - radius, z, color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                x, y + radius, z, color[0], color[1], color[2], color[3],
            ]);

            // Top-left corner
            self.add_arc_vertices(&mut vertices, x + radius, y + radius, z, radius, 180.0, 270.0, segments_per_corner, color);

            self.draw_vertices(gl, &vertices, glow::LINES, viewport);
        }
    }

    fn add_rect_vertices(&self, vertices: &mut Vec<f32>, x: f32, y: f32, w: f32, h: f32, z: f32, color: [f32; 4]) {
        // Two triangles
        vertices.extend_from_slice(&[x, y, z, color[0], color[1], color[2], color[3]]);
        vertices.extend_from_slice(&[x + w, y, z, color[0], color[1], color[2], color[3]]);
        vertices.extend_from_slice(&[x + w, y + h, z, color[0], color[1], color[2], color[3]]);
        vertices.extend_from_slice(&[x, y, z, color[0], color[1], color[2], color[3]]);
        vertices.extend_from_slice(&[x + w, y + h, z, color[0], color[1], color[2], color[3]]);
        vertices.extend_from_slice(&[x, y + h, z, color[0], color[1], color[2], color[3]]);
    }

    fn add_corner_vertices(&self, vertices: &mut Vec<f32>, cx: f32, cy: f32, z: f32, radius: f32, start: f32, end: f32, segments: u32, color: [f32; 4]) {
        let start_rad = start.to_radians();
        let end_rad = end.to_radians();
        let angle_span = end_rad - start_rad;

        for i in 0..segments {
            let t1 = i as f32 / segments as f32;
            let t2 = (i + 1) as f32 / segments as f32;
            let angle1 = start_rad + angle_span * t1;
            let angle2 = start_rad + angle_span * t2;

            vertices.extend_from_slice(&[cx, cy, z, color[0], color[1], color[2], color[3]]);
            vertices.extend_from_slice(&[
                cx + radius * angle1.cos(), cy + radius * angle1.sin(), z,
                color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                cx + radius * angle2.cos(), cy + radius * angle2.sin(), z,
                color[0], color[1], color[2], color[3],
            ]);
        }
    }

    fn add_arc_vertices(&self, vertices: &mut Vec<f32>, cx: f32, cy: f32, z: f32, radius: f32, start: f32, end: f32, segments: u32, color: [f32; 4]) {
        let start_rad = start.to_radians();
        let end_rad = end.to_radians();
        let angle_span = end_rad - start_rad;

        for i in 0..segments {
            let t1 = i as f32 / segments as f32;
            let t2 = (i + 1) as f32 / segments as f32;
            let angle1 = start_rad + angle_span * t1;
            let angle2 = start_rad + angle_span * t2;

            vertices.extend_from_slice(&[
                cx + radius * angle1.cos(), cy + radius * angle1.sin(), z,
                color[0], color[1], color[2], color[3],
            ]);
            vertices.extend_from_slice(&[
                cx + radius * angle2.cos(), cy + radius * angle2.sin(), z,
                color[0], color[1], color[2], color[3],
            ]);
        }
    }

    fn draw_vertices(&self, gl: &glow::Context, vertices: &[f32], mode: u32, viewport: (f32, f32)) {
        unsafe {
            gl.use_program(Some(self.program));

            let proj_loc = gl.get_uniform_location(self.program, "projection");
            let proj = orthographic_projection(viewport.0, viewport.1);
            gl.uniform_matrix_4_f32_slice(proj_loc.as_ref(), false, &proj);

            gl.bind_vertex_array(Some(self.vao));
            gl.bind_buffer(glow::ARRAY_BUFFER, Some(self.vbo));

            let bytes: &[u8] = bytemuck::cast_slice(vertices);
            gl.buffer_sub_data_u8_slice(glow::ARRAY_BUFFER, 0, bytes);

            gl.enable(glow::BLEND);
            gl.blend_func(glow::SRC_ALPHA, glow::ONE_MINUS_SRC_ALPHA);

            gl.draw_arrays(mode, 0, (vertices.len() / 7) as i32);
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
layout (location = 1) in vec4 aColor;

out vec4 Color;

uniform mat4 projection;

void main() {
    gl_Position = projection * vec4(aPos, 1.0);
    Color = aColor;
}
"#;

const FRAGMENT_SHADER: &str = r#"
#version 330 core
in vec4 Color;

out vec4 FragColor;

void main() {
    FragColor = Color;
}
"#;

use bytemuck;
