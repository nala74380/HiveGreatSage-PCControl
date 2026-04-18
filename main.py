#!/usr/bin/env python3
"""应用入口"""

import sys
from core.app import Application

def main():
    app = Application()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
