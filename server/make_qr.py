from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote

import qrcode


parser = argparse.ArgumentParser()
parser.add_argument("--base-url", required=True)
parser.add_argument("--token", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()

payload = f"mangalens://pair?base_url={quote(args.base_url, safe='')}&token={quote(args.token, safe='')}"
args.output.parent.mkdir(parents=True, exist_ok=True)
qrcode.make(payload).save(args.output)
print(payload)

