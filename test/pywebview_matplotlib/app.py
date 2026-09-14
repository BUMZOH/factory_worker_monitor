from pathlib import Path
import subprocess
import sys

import webview


BASE_DIR = Path(__file__).resolve().parent


class Api:
    def show_graph1(self, target_date):
        """Start graph 1 with the target date."""
        subprocess.Popen(
            [
                sys.executable,
                str(BASE_DIR / "graph1.py"),
                target_date,
            ]
        )


api = Api()

window = webview.create_window(
    "Matplotlib Sample",
    "index.html",
    js_api=api,
    width=500,
    height=300,
)

webview.start()