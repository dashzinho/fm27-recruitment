"""Folder layout:  <root>/{fm27.py, prefs.json, app/, data/, output/}"""
import os
APP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
for _d in (DATA, OUT):
    os.makedirs(_d, exist_ok=True)
