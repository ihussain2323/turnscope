"""Regenerate the checked-in speech using Flite 2.2."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--flite', default='flite')
args = parser.parse_args()
directory = Path(__file__).resolve().parent
for case in json.loads((directory / 'cases.json').read_text()):
    subprocess.run([args.flite, '-voice', 'slt', '-t', case['reference'],
                    '-o', str(directory / (case['id'] + '.wav'))], check=True)
