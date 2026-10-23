"""Software 3D viewport: orbit camera + painter's algorithm into a Tk canvas."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass

import numpy as np

from .. import theme
from .obj import Mesh

LIGHT = np.array([0.35, 0.75, 0.55], dtype=np.float32)
LIGHT /= np.linalg.norm(LIGHT)


@dataclass
class Camera:
    yaw: float = 35.0
    pitch: float = 18.0
    dist: float = 3.0
    fov: float = 42.0
    pan: tuple[float, float] = (0.0, 0.0)


def _hex(color: tuple[float, float, float], intensity: float) -> str:
    r = max(0.0, min(1.0, color[0] * intensity))
    g = max(0.0, min(1.0, color[1] * intensity))
    b = max(0.0, min(1.0, color[2] * intensity))
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


class MeshViewer:
    """Draws a Mesh into a tk.Canvas with mouse orbit/pan/zoom."""

    def __init__(self, canvas: tk.Canvas, mesh: Mesh | None = None):
        self.canvas = canvas
        self.mesh: Mesh | None = None
        self.cam = Camera()
        self.wireframe = False
        self.cull = False
        self.flip_z = False
        self.show_axes = True
        self.max_faces = 12000          # draw budget for very dense scenes
        self.last_drawn = 0
        self.last_total = 0
        self._drag: tuple[int, int, str] | None = None
        self._wire_tag = "mesh"
        self.set_mesh(mesh)
        self._bind()

    # ------------------------------------------------------------------
    def set_mesh(self, mesh: Mesh | None) -> None:
        self.mesh = mesh
        self.last_drawn = 0
        self.last_total = 0
        if mesh is not None:
            self.fit()

    def fit(self) -> None:
        if self.mesh is None:
            return
        radius = self.mesh.radius
        if not math.isfinite(radius) or radius <= 0:
            radius = 1.0
        self.cam.dist = max(radius * 2.9, 1e-4)
        self.cam.pan = (0.0, 0.0)
        self.draw()

    def reset(self) -> None:
        self.cam.yaw = 35.0
        self.cam.pitch = 18.0
        self.fit()

    # ------------------------------------------------------------------
    def _bind(self) -> None:
        c = self.canvas
        c.bind("<ButtonPress-1>", lambda e: self._start(e, "orbit"))
        c.bind("<B1-Motion>", self._motion)
        c.bind("<ButtonRelease-1>", lambda e: self._end())
        c.bind("<ButtonPress-2>", lambda e: self._start(e, "pan"))
        c.bind("<B2-Motion>", self._motion)
        c.bind("<ButtonRelease-2>", lambda e: self._end())
        c.bind("<ButtonPress-3>", lambda e: self._start(e, "pan"))
        c.bind("<B3-Motion>", self._motion)
        c.bind("<ButtonRelease-3>", lambda e: self._end())
        c.bind("<MouseWheel>", self._wheel)
        c.bind("<Double-Button-1>", lambda e: self.reset())
        c.bind("<Configure>", lambda e: self.draw())

    def _start(self, event, mode: str) -> None:
        self._drag = (event.x, event.y, mode)

    def _end(self) -> None:
        self._drag = None

    def _motion(self, event) -> None:
        if self._drag is None:
            return
        x0, y0, mode = self._drag
        dx, dy = event.x - x0, event.y - y0
        self._drag = (event.x, event.y, mode)
        if mode == "orbit":
            # both axes follow the mouse: drag right turns the model right and
            # drag down tips its top towards you (matches the Rust viewer)
            self.cam.yaw = (self.cam.yaw + dx * 0.45) % 360.0
            self.cam.pitch = max(-89.0, min(89.0, self.cam.pitch + dy * 0.4))
        else:
            scale = self.cam.dist * 0.0016
            px, py = self.cam.pan
            self.cam.pan = (px + dx * scale, py - dy * scale)
        self.draw()

    def _wheel(self, event) -> None:
        factor = 0.88 if event.delta > 0 else 1.14
        self.cam.dist = max(1e-4, self.cam.dist * factor)
        self.draw()

    # ------------------------------------------------------------------
    def _rotation(self) -> np.ndarray:
        yaw = math.radians(self.cam.yaw)
        pitch = math.radians(self.cam.pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
        rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], dtype=np.float32)
        return rx @ ry

    def _project(self, pts_view: np.ndarray, w: int, h: int) -> tuple[np.ndarray, float]:
        f = 0.5 * min(w, h) / math.tan(math.radians(self.cam.fov) * 0.5)
        z = pts_view[:, 2]
        denom = np.where(np.abs(z) < 1e-6, 1e-6, z)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            sx = w * 0.5 + f * pts_view[:, 0] / denom
            sy = h * 0.5 - f * pts_view[:, 1] / denom
        return np.stack([sx, sy], axis=1), f

    def draw(self) -> None:
        c = self.canvas
        c.delete("all")
        self.last_drawn = 0
        self.last_total = 0
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return
        if self.mesh is None or len(self.mesh.faces) == 0:
            c.create_text(w // 2, h // 2, text="Select a model to view",
                          fill=theme.TEXT_FAINT, font=theme.F_BASE)
            return

        mesh = self.mesh
        rot = self._rotation()
        center = mesh.center
        view = (mesh.verts - center) @ rot.T
        if self.flip_z:
            view[:, 2] *= -1.0
        view[:, 2] += self.cam.dist
        proj, f = self._project(view, w, h)
        pan_x, pan_y = self.cam.pan
        depth_scale = f / max(self.cam.dist, 1e-6)
        proj[:, 0] += pan_x * depth_scale
        proj[:, 1] -= pan_y * depth_scale

        faces = mesh.faces
        self.last_total = int(len(faces))
        depth = view[faces, 2].mean(axis=1)

        normals = mesh.face_normals()
        view_normals = normals @ rot.T
        intensity = np.nan_to_num(0.22 + 0.78 * np.abs(view_normals @ LIGHT),
                                  nan=0.5, posinf=1.0, neginf=0.0)

        near = max(1e-5, self.cam.dist * 0.02)
        if self.cull:
            keep = view_normals[:, 2] > 0
        else:
            keep = np.ones(len(faces), dtype=bool)
        keep &= (view[faces, 2] > near).all(axis=1)

        coords = proj[faces]
        # corrupt vertices in some environment exports project to absurd places:
        # drop their faces along with anything entirely off-canvas
        keep &= np.isfinite(coords).all(axis=(1, 2)) & np.isfinite(depth)
        with np.errstate(over="ignore", invalid="ignore"):
            vfaces = mesh.verts[faces]
            world_span = (vfaces.max(axis=1) - vfaces.min(axis=1)).max(axis=1)
        span_limit = max(1e-6, float(np.max(mesh.size)) * 8.0)
        keep &= np.isfinite(world_span) & (world_span <= span_limit)
        mins = coords.min(axis=1)
        maxs = coords.max(axis=1)
        keep &= ((maxs[:, 0] > -w) & (mins[:, 0] < w * 2)
                 & (maxs[:, 1] > -h) & (mins[:, 1] < h * 2))

        order = np.argsort(depth)                               # near -> far
        order = order[keep[order]]
        if len(order) > self.max_faces:
            order = order[-self.max_faces:]                     # budget goes to the nearest
        order = order[::-1]                                     # paint far -> near

        color = mesh.color
        outline = theme.WIRE if self.wireframe else ""
        width = 1 if self.wireframe else 0
        for fi in order:
            tri = coords[fi]
            if self.wireframe:
                fill = ""
            else:
                fill = _hex(color, float(intensity[fi]))
            c.create_polygon(float(tri[0][0]), float(tri[0][1]),
                             float(tri[1][0]), float(tri[1][1]),
                             float(tri[2][0]), float(tri[2][1]),
                             fill=fill, outline=outline, width=width)
            self.last_drawn += 1

        if self.show_axes:
            self._draw_axes(rot, w, h)

    def _draw_axes(self, rot: np.ndarray, w: int, h: int) -> None:
        c = self.canvas
        origin = np.array([0.0, 0.0, max(self.cam.dist, 1e-4)], dtype=np.float32)
        scale = self.cam.dist * 0.22
        axes = (("X", np.array([scale, 0, 0], np.float32), "#e86a5b"),
                ("Y", np.array([0, scale, 0], np.float32), "#5ec98a"),
                ("Z", np.array([0, 0, scale], np.float32), "#6db3f2"))
        proj, _ = self._project(np.stack([origin]), w, h)
        ox, oy = float(proj[0][0]), float(proj[0][1])
        for label, vec, col in axes:
            tip = origin + vec @ rot.T
            p, _ = self._project(np.stack([tip]), w, h)
            x, y = float(p[0][0]), float(p[0][1])
            c.create_line(ox, oy, x, y, fill=col, width=2)
            c.create_text(x, y, text=label, fill=col, font=theme.F_TINY)
