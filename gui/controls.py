"""
gui/controls.py
---------------
Reusable UI components: Button, Toggle, Slider, Label, Section.
All use pygame.draw — no external widget lib required.
"""

import pygame
from typing import Callable, List, Optional, Tuple
from gui import theme


def draw_rounded_rect(surface, color, rect, radius: int, border_color=None, border_width: int = 1):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)


class Button:
    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        label: str,
        callback: Callable,
        active: bool = False,
        enabled: bool = True,
        accent: bool = False
    ):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.active = active
        self.enabled = enabled
        self.accent = accent
        self._hovered = False

    def handle_event(self, event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False

    def draw(self, surface, font):
        if not self.enabled:
            bg = theme.BTN_DISABLED
            tc = theme.BTN_TEXT_DISABLED
            border = theme.BORDER
        elif self.active or self.accent:
            bg = theme.ACCENT_PINK
            tc = theme.BTN_TEXT_ACTIVE
            border = theme.ACCENT_ROSE
        elif self._hovered:
            bg = theme.BTN_HOVER
            tc = theme.TEXT_PRIMARY
            border = theme.ACCENT_ROSE
        else:
            bg = theme.BTN_NORMAL
            tc = theme.BTN_TEXT_NORMAL
            border = theme.BORDER

        draw_rounded_rect(surface, bg, self.rect, theme.CORNER_RADIUS, border, 1)
        text = font.render(self.label, True, tc)
        tr = text.get_rect(center=self.rect.center)
        surface.blit(text, tr)

    def update_label(self, new_label: str):
        self.label = new_label


class ToggleGroup:
    """Mutually exclusive set of buttons — radio-button behavior."""

    def __init__(self, buttons: List[Button]):
        self.buttons = buttons

    def set_active(self, index: int):
        for i, btn in enumerate(self.buttons):
            btn.active = (i == index)

    def handle_event(self, event) -> bool:
        for btn in self.buttons:
            if btn.handle_event(event):
                return True
        return False

    def draw(self, surface, font):
        for btn in self.buttons:
            btn.draw(surface, font)


class Slider:
    """Horizontal drag slider returning float in [min_val, max_val]."""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        min_val: float,
        max_val: float,
        value: float,
        label: str,
        fmt: str = ".0f",
        suffix: str = ""
    ):
        self.rect = pygame.Rect(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.label = label
        self.fmt = fmt
        self.suffix = suffix
        self._dragging = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._update_value(event.pos[0])
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        if event.type == pygame.MOUSEMOTION and self._dragging:
            self._update_value(event.pos[0])
            return True
        return False

    def _update_value(self, mx: int):
        t = (mx - self.rect.x) / self.rect.width
        t = max(0.0, min(1.0, t))
        self.value = self.min_val + t * (self.max_val - self.min_val)

    def draw(self, surface, font_sm, font_md):
        # Label row: left = label name, right = current value
        lbl  = font_sm.render(self.label, True, theme.TEXT_SECONDARY)
        val_str = f"{self.value:{self.fmt}}{self.suffix}"
        val  = font_sm.render(val_str, True, theme.ACCENT_CYAN)
        label_y = self.rect.y - lbl.get_height() - 3
        surface.blit(lbl, (self.rect.x, label_y))
        surface.blit(val, (self.rect.right - val.get_width(), label_y))

        # Track
        cy = self.rect.centery
        track = pygame.Rect(self.rect.x, cy - 2, self.rect.width, 4)
        draw_rounded_rect(surface, theme.BORDER, track, 2)

        # Fill
        t = (self.value - self.min_val) / (self.max_val - self.min_val)
        fill_w = max(0, int(t * self.rect.width))
        if fill_w > 0:
            fill = pygame.Rect(self.rect.x, cy - 2, fill_w, 4)
            draw_rounded_rect(surface, theme.ACCENT_PINK, fill, 2)

        # Thumb
        tx = self.rect.x + fill_w
        pygame.draw.circle(surface, theme.ACCENT_ROSE, (tx, cy), 6)
        pygame.draw.circle(surface, theme.BG_CARD,     (tx, cy), 3)


class MetricCard:
    """Compact metric display: label + value."""

    def __init__(self, rect: Tuple[int, int, int, int], label: str, value: str = "--"):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value

    def draw(self, surface, font_sm, font_val):
        """font_val is the font used for the value — caller passes font_md."""
        draw_rounded_rect(surface, theme.BG_CARD, self.rect, theme.CORNER_RADIUS, theme.BORDER, 1)
        lbl = font_sm.render(self.label, True, theme.TEXT_MUTED)
        val = font_val.render(self.value, True, theme.ACCENT_CYAN)
        # Stack label on top, value below — fits in ~38px card
        surface.blit(lbl, (self.rect.x + 7, self.rect.y + 5))
        surface.blit(val, (self.rect.x + 7, self.rect.y + 5 + lbl.get_height() + 1))

    def update(self, value: str):
        self.value = str(value)


def draw_section_header(surface, font, text: str, x: int, y: int, width: int) -> int:
    """Draw a labeled section divider. Returns y position after underline."""
    label = font.render(text, True, theme.ACCENT_ROSE)
    surface.blit(label, (x, y))
    line_y = y + label.get_height() + 2
    pygame.draw.line(surface, theme.BORDER, (x, line_y), (x + width, line_y), 1)
    return line_y + 6
