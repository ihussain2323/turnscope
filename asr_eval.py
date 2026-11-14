"""Run an offline Whisper evaluation on synthetic payment-support utterances."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import time
import wave

ROOT = Path(__file__).resolve().parent


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def word_errors(reference, hypothesis):
    prev = list(range(len(hypothesis) + 1))
    for i, word in enumerate(reference, 1):
        row = [i]
        for j, candidate in enumerate(hypothesis, 1):
            row.append(min(row[-1] + 1, prev[j] + 1, prev[j-1] + (word != candidate)))
        prev = row
    return prev[-1]


def has_phrase(words, phrase):
    return any(words[i:i+len(phrase)] == phrase for i in range(len(words)-len(phrase)+1))


def prepare(source, target, noise_rms):
    with wave.open(str(source), 'rb') as src:
        if (src.getnchannels(), src.getsampwidth(), src.getframerate()) != (1, 2, 16000):
            raise ValueError(f'{source}: expected mono 16-bit PCM at 16 kHz')
        pcm = array('h', src.readframes(src.getnframes()))
    if sys.byteorder != 'little':
        pcm.byteswap()
    rng = random.Random(42)
    for i, x in enumerate(pcm):
        pcm[i] = max(-32768, min(32767, x + round(rng.gauss(0, noise_rms)))) if noise_rms else x
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(target), 'wb') as out:
        out.setparams((1, 2, 16000, 0, 'NONE', 'PCM'))
        out.writeframes(pcm.tobytes())
    return len(pcm) / 16000


def score(cli, model):
    cases = json.loads((ROOT / 'speech/cases.json').read_text())
    report = {'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'conditions': []}
    with tempfile.TemporaryDirectory() as directory:
        audio = Path(directory) / 'input.wav'
        prefix = Path(directory) / 'transcript'
        for noise in (0, 1200, 3600):
            rows = []
            for case in cases:
                seconds = prepare(ROOT / 'speech' / (case['id'] + '.wav'), audio, noise)
                start = time.perf_counter()
                subprocess.run([cli, '-m', str(model), '-f', str(audio), '-l', 'en', '-t', '2',
                                '-otxt', '-of', str(prefix), '-nt', '-ng'], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                elapsed = time.perf_counter() - start
                hypothesis = prefix.with_suffix('.txt').read_text().strip()
                reference, decoded = tokens(case['reference']), tokens(hypothesis)
                rows.append(dict(id=case['id'], reference=case['reference'], hypothesis=hypothesis,
                                 target_phrase=case['target'], target_recovered=has_phrase(decoded, tokens(case['target'])),
                                 reference_words=len(reference), errors=word_errors(reference, decoded),
                                 audio_seconds=seconds, wall_seconds=round(elapsed, 3)))
            report['conditions'].append(dict(noise_rms_pcm16=noise,
                word_error_rate=round(sum(r['errors'] for r in rows)/sum(r['reference_words'] for r in rows), 4),
                target_phrases_recovered=sum(r['target_recovered'] for r in rows), cases=rows))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', default='whisper-cli')
    parser.add_argument('--model', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(score(args.cli, args.model), indent=2))
    except subprocess.CalledProcessError as exc:
        parser.exit(2, exc.stderr.decode(errors='replace')[-2000:] + '\n')
    except (OSError, ValueError, wave.Error) as exc:
        parser.exit(2, f'{parser.prog}: {exc}\n')
