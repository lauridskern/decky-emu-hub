import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def release(emu_id):
    with open(os.path.join(FIXTURES, "releases", f"{emu_id}.json"), encoding="utf-8") as handle:
        return json.load(handle)
