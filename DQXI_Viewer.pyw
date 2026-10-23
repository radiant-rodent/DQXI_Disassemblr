"""Double-click launcher for the DQXI Explorer (no console window).

Run with ``pythonw DQXI_Viewer.pyw`` or just double-click the file.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    from viewer.app import App

    App().mainloop()


if __name__ == "__main__":
    main()
