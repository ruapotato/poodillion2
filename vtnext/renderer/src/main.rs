//! VTNext Terminal Renderer
//!
//! A next-generation terminal with OpenGL rendering,
//! arbitrary text positioning/rotation, and game-engine style input.

mod protocol;
mod render;
mod input;

use std::io::{self, Read, Write};
use std::num::NonZeroU32;
use std::sync::mpsc;
use std::thread;

use ab_glyph::FontRef;
use anyhow::Result;
use glutin::config::ConfigTemplateBuilder;
use glutin::context::{ContextAttributesBuilder, PossiblyCurrentContext};
use glutin::display::GetGlDisplay;
use glutin::prelude::*;
use glutin::surface::{Surface, SwapInterval, WindowSurface};
use glutin_winit::{DisplayBuilder, GlWindow};
use glow::HasContext;
use raw_window_handle::HasRawWindowHandle;
use winit::event::{Event, WindowEvent, ElementState};
use winit::event_loop::{ControlFlow, EventLoop};
use winit::window::{Window, WindowBuilder};

use protocol::{Command, InputEvent, Parser};
use render::Renderer;
use input::InputHandler;

// Embedded default font (DejaVu Sans Mono or similar)
const DEFAULT_FONT: &[u8] = include_bytes!("../assets/DejaVuSansMono.ttf");

fn main() -> Result<()> {
    env_logger::init();
    log::info!("VTNext renderer starting");

    // Start stdin reader thread
    let (stdin_tx, stdin_rx) = mpsc::channel::<Vec<u8>>();
    thread::spawn(move || {
        let stdin = io::stdin();
        let mut handle = stdin.lock();
        let mut buf = [0u8; 4096];
        loop {
            match handle.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    if stdin_tx.send(buf[..n].to_vec()).is_err() {
                        break;
                    }
                }
                Err(e) => {
                    log::error!("stdin read error: {}", e);
                    break;
                }
            }
        }
    });

    let event_loop = EventLoop::new()?;

    // Create window
    let window_builder = WindowBuilder::new()
        .with_title("VTNext Terminal")
        .with_inner_size(winit::dpi::LogicalSize::new(1024, 768));

    let template = ConfigTemplateBuilder::new()
        .with_alpha_size(8)
        .with_transparency(false);

    let display_builder = DisplayBuilder::new().with_window_builder(Some(window_builder));

    let (window, gl_config) = display_builder
        .build(&event_loop, template, |configs| {
            configs
                .reduce(|accum, config| {
                    if config.num_samples() > accum.num_samples() {
                        config
                    } else {
                        accum
                    }
                })
                .unwrap()
        })
        .expect("Failed to create window");

    let window = window.expect("No window created");
    let raw_window_handle = window.raw_window_handle();

    let gl_display = gl_config.display();

    let context_attrs = ContextAttributesBuilder::new()
        .build(Some(raw_window_handle));

    let gl_context = unsafe {
        gl_display
            .create_context(&gl_config, &context_attrs)
            .expect("Failed to create GL context")
    };

    let size = window.inner_size();
    let attrs = window.build_surface_attributes(Default::default());
    let gl_surface = unsafe {
        gl_display
            .create_window_surface(&gl_config, &attrs)
            .expect("Failed to create surface")
    };

    let gl_context = gl_context
        .make_current(&gl_surface)
        .expect("Failed to make context current");

    let _ = gl_surface.set_swap_interval(&gl_context, SwapInterval::Wait(NonZeroU32::new(1).unwrap()));

    let gl = unsafe {
        glow::Context::from_loader_function_cstr(|s| {
            gl_display.get_proc_address(s) as *const _
        })
    };

    unsafe {
        gl.enable(glow::BLEND);
        gl.blend_func(glow::SRC_ALPHA, glow::ONE_MINUS_SRC_ALPHA);
        gl.enable(glow::DEPTH_TEST);
        gl.depth_func(glow::LEQUAL);
        gl.viewport(0, 0, size.width as i32, size.height as i32);
    }

    let mut renderer = Renderer::new(&gl);
    renderer.set_viewport(size.width as f32, size.height as f32);

    let font = FontRef::try_from_slice(DEFAULT_FONT)
        .expect("Failed to load font");

    let mut parser = Parser::new();
    let mut input_handler = InputHandler::new();
    let mut raw_input_mode = true;
    let mut pending_commands: Vec<Command> = Vec::new();
    let mut mouse_pos = (0.0f32, 0.0f32);

    let send_event = |event: &InputEvent| {
        let encoded = event.encode();
        let _ = io::stdout().write_all(encoded.as_bytes());
        let _ = io::stdout().flush();
    };

    let send_response = |response: &str| {
        let _ = io::stdout().write_all(response.as_bytes());
        let _ = io::stdout().flush();
    };

    event_loop.run(move |event, elwt| {
        elwt.set_control_flow(ControlFlow::Poll);

        match event {
            Event::WindowEvent { event, .. } => match event {
                WindowEvent::CloseRequested => {
                    elwt.exit();
                }

                WindowEvent::Resized(size) => {
                    if size.width > 0 && size.height > 0 {
                        gl_surface.resize(
                            &gl_context,
                            NonZeroU32::new(size.width).unwrap(),
                            NonZeroU32::new(size.height).unwrap(),
                        );
                        renderer.set_viewport(size.width as f32, size.height as f32);
                        unsafe {
                            gl.viewport(0, 0, size.width as i32, size.height as i32);
                        }

                        let evt = input_handler.handle_resize(size.width as f32, size.height as f32);
                        send_event(&evt);
                    }
                }

                WindowEvent::ModifiersChanged(mods) => {
                    input_handler.update_modifiers(&mods);
                }

                WindowEvent::KeyboardInput { event, is_synthetic: false, .. } => {
                    if raw_input_mode {
                        if let Some(input_event) = input_handler.handle_keyboard(
                            event.physical_key,
                            event.state,
                            event.repeat,
                        ) {
                            send_event(&input_event);
                        }

                        if event.state == ElementState::Pressed {
                            if let Some(ref text) = event.text {
                                for char_event in input_handler.handle_text(text) {
                                    send_event(&char_event);
                                }
                            }
                        }
                    }
                }

                WindowEvent::CursorMoved { position, .. } => {
                    mouse_pos = (position.x as f32, position.y as f32);
                    if raw_input_mode {
                        let evt = input_handler.handle_mouse_move(
                            position.x as f32,
                            position.y as f32,
                        );
                        send_event(&evt);
                    }
                }

                WindowEvent::MouseInput { state: btn_state, button, .. } => {
                    if raw_input_mode {
                        let evt = input_handler.handle_mouse_button(
                            button,
                            btn_state,
                            mouse_pos,
                        );
                        send_event(&evt);
                    }
                }

                WindowEvent::MouseWheel { delta, .. } => {
                    if raw_input_mode {
                        let (dx, dy) = match delta {
                            winit::event::MouseScrollDelta::LineDelta(x, y) => (x, y),
                            winit::event::MouseScrollDelta::PixelDelta(pos) => {
                                (pos.x as f32, pos.y as f32)
                            }
                        };
                        let evt = input_handler.handle_scroll(dx, dy, mouse_pos);
                        send_event(&evt);
                    }
                }

                WindowEvent::Focused(focused) => {
                    let evt = input_handler.handle_focus(focused);
                    send_event(&evt);
                }

                WindowEvent::RedrawRequested => {
                    // Process stdin
                    while let Ok(data) = stdin_rx.try_recv() {
                        let (commands, _plain_text) = parser.feed(&data);
                        pending_commands.extend(commands);
                    }

                    // Process pending commands
                    for cmd in pending_commands.drain(..) {
                        match &cmd {
                            Command::QueryVersion => {
                                send_response("\x1b]vtnr;version;0;1;0\x07");
                            }
                            Command::QuerySize => {
                                let (w, h) = renderer.viewport();
                                send_response(&format!("\x1b]vtnr;size;{};{}\x07", w as u32, h as u32));
                            }
                            Command::QueryFeatures => {
                                send_response("\x1b]vtnr;features;text;rect;line\x07");
                            }
                            Command::InputMode { raw } => {
                                raw_input_mode = *raw;
                                input_handler.set_raw_mode(*raw);
                            }
                            _ => {
                                renderer.execute_command(&gl, &font, &cmd);
                            }
                        }
                    }

                    // Swap buffers
                    gl_surface.swap_buffers(&gl_context)
                        .expect("Failed to swap buffers");

                    window.request_redraw();
                }

                _ => {}
            },

            Event::AboutToWait => {
                window.request_redraw();
            }

            _ => {}
        }
    })?;

    Ok(())
}
