"""Render the existing vector logo into a six-second Telegram avatar loop."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, '/tmp/radar-video-deps')
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[2]
SIZE, FPS, SECONDS = 800, 30, 6
NS = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', NS[1:-1])
svg = ET.parse(ROOT / 'frontend/public/radar.svg').getroot()
for style in list(svg.findall(NS + 'style')):
    svg.remove(style)
svg.insert(0, ET.Element(NS + 'rect', {'width': '96', 'height': '96', 'fill': '#0a0f1a'}))
sweep = next(e for e in svg.iter() if e.get('class') == 'sweep')
signals = [e for e in svg.iter() if 'signal' in e.get('class', '').split()]
echoes = [e for e in svg.iter() if 'echo' in e.get('class', '').split()]

rsvg = C.CDLL('librsvg-2.so.2')
cairo = C.CDLL('libcairo.so.2')
gobj = C.CDLL('libgobject-2.0.so.0')
def bind(lib, name, args, result=None):
    fn = getattr(lib, name)
    fn.argtypes, fn.restype = args, result
    return fn
new_svg = bind(rsvg, 'rsvg_handle_new_from_data', [C.c_char_p, C.c_size_t, C.c_void_p], C.c_void_p)
render = bind(rsvg, 'rsvg_handle_render_cairo', [C.c_void_p, C.c_void_p], C.c_int)
new_surface = bind(cairo, 'cairo_image_surface_create', [C.c_int, C.c_int, C.c_int], C.c_void_p)
new_ctx = bind(cairo, 'cairo_create', [C.c_void_p], C.c_void_p)
scale = bind(cairo, 'cairo_scale', [C.c_void_p, C.c_double, C.c_double])
flush = bind(cairo, 'cairo_surface_flush', [C.c_void_p])
data = bind(cairo, 'cairo_image_surface_get_data', [C.c_void_p], C.c_void_p)
stride = bind(cairo, 'cairo_image_surface_get_stride', [C.c_void_p], C.c_int)
png = bind(cairo, 'cairo_surface_write_to_png', [C.c_void_p, C.c_char_p], C.c_int)
destroy_ctx = bind(cairo, 'cairo_destroy', [C.c_void_p])
destroy_surface = bind(cairo, 'cairo_surface_destroy', [C.c_void_p])
unref = bind(gobj, 'g_object_unref', [C.c_void_p])

out = ROOT / 'outputs/radar-telegram.mp4'
encoder = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [encoder, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo',
       '-pixel_format', 'bgra', '-video_size', f'{SIZE}x{SIZE}', '-framerate', str(FPS),
       '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
       '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)]

def opacity(phase):
    points = [(0, 1), (.02, 1), (.15, .75), (.55, .25), (.94, .25), (1, 1)]
    for (a, x), (b, y) in zip(points, points[1:]):
        if a <= phase <= b:
            return x + (y - x) * (phase - a) / (b - a)
    return 1

with subprocess.Popen(cmd, stdin=subprocess.PIPE) as process:
    for frame in range(FPS * SECONDS):
        phase = frame / (FPS * SECONDS)
        sweep.set('transform', f'rotate({phase * 360:.6f} 48 48)')
        for idx, (signal, echo) in enumerate(zip(signals, echoes)):
            p = (phase + idx * .5) % 1
            signal.set('opacity', f'{opacity(p):.5f}')
            t = min(p / .22, 1)
            echo.set('r', f'{5 * (.65 + 1.15 * t):.5f}')
            echo.set('opacity', f'{.7 * (1 - t):.5f}')
        source = ET.tostring(svg)
        handle = new_svg(source, len(source), None)
        assert handle, 'Invalid SVG'
        surface = new_surface(0, SIZE, SIZE)
        ctx = new_ctx(surface)
        scale(ctx, SIZE / 96, SIZE / 96)
        assert render(handle, ctx), 'SVG render failed'
        flush(surface)
        assert stride(surface) == SIZE * 4
        process.stdin.write(C.string_at(data(surface), SIZE * SIZE * 4))
        if frame in (0, 45, 90, 135):
            assert png(surface, os.fsencode(ROOT / f'outputs/radar-frame-{frame:03}.png')) == 0
        destroy_ctx(ctx)
        destroy_surface(surface)
        unref(handle)
    process.stdin.close()
    assert process.wait() == 0, 'Video encoding failed'
print(f'{out}: {SIZE}x{SIZE}, {SECONDS}s, {FPS} fps, {out.stat().st_size} bytes')
subprocess.run([encoder, '-v', 'error', '-i', str(out), '-f', 'null', '-'], check=True)
print('All video frames decoded successfully.')
