"""
╔══════════════════════════════════════════════════════════════╗
║         DYNAMIC PATHFINDING AGENT  ✦  v1.0                  ║
║         Built with precision. Designed with intention.       ║
╚══════════════════════════════════════════════════════════════╝
"""

import pygame
import sys
from gui.app import PathfindingApp


def main():
    pygame.init()
    pygame.display.set_caption("✦ Dynamic Pathfinding Agent")
    app = PathfindingApp()
    app.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
