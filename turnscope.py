"""Measure turn timing in a channel-separated voice-agent call."""
import argparse
from array import array
import csv
import json
import math
from pathlib import Path
import sys
import wave


def activity(samples, rate, frame_ms, threshold_db):
    frame_size = max(1, round(rate * frame_ms / 1000))
    floor = (32768 * 10 ** (threshold_db / 20)) ** 2
    for start in range(0, len(samples), frame_size):
        frame = samples[start:start + frame_size]
        if sum(x * x for x in frame) / len(frame) >= floor:
            yield round(start * 1000 / rate), round((start + len(frame)) * 1000 / rate)


def segments(frames, hold_ms, minimum_ms):
    runs = []
    for start, end in frames:
        if runs and start - runs[-1][1] <= hold_ms:
            runs[-1][1] = end
        else:
            runs.append([start, end])
    return [(start, end) for start, end in runs if end - start >= minimum_ms]


def analyze(caller, agent):
    """Attribute each agent onset to the most recent preceding caller turn."""
    rows = []
    cursor = 0
    for start, end in caller:
        while cursor < len(agent) and agent[cursor][1] <= start:
            cursor += 1
        for index in range(cursor, len(agent)):
            a_start, a_end = agent[index]
            if a_start >= end:
                break
            overlap = min(end, a_end) - max(start, a_start)
            kind = 'caller_barge_in' if a_start < start else 'simultaneous' if a_start == start else 'agent_cut_in'
            rows.append(dict(event=kind, start_ms=max(start, a_start), duration_ms=overlap))
    cursor = 0
    for index, (start, end) in enumerate(caller):
        while cursor < len(agent) and agent[cursor][0] < end:
            cursor += 1
        if cursor and agent[cursor - 1][1] > end:
            continue
        if cursor < len(agent) and (index + 1 == len(caller) or agent[cursor][0] < caller[index+1][0]):
            rows.append(dict(event='response_gap', start_ms=end, duration_ms=agent[cursor][0] - end))
        else:
            rows.append(dict(event='unanswered_turn', start_ms=end, duration_ms=None))
    return sorted(rows, key=lambda row: row['start_ms'])


def inspect(path, threshold_db=-40, hold_ms=100, minimum_ms=60):
    if not math.isfinite(threshold_db) or not -100 <= threshold_db <= 0:
        raise ValueError('threshold must be between -100 and 0 dBFS')
    if hold_ms < 0 or minimum_ms < 0:
        raise ValueError('hold and minimum durations must be nonnegative')
    with wave.open(str(path), 'rb') as stream:
        if stream.getnchannels() != 2 or stream.getsampwidth() != 2:
            raise ValueError('expected stereo 16-bit PCM WAV (caller left, agent right)')
        rate = stream.getframerate()
        count = stream.getnframes()
        pcm = array('h', stream.readframes(count))
        if len(pcm) != 2 * count:
            raise ValueError('truncated WAV sample data')
        if sys.byteorder != 'little':
            pcm.byteswap()
    channels = [segments(activity(pcm[i::2], rate, 20, threshold_db), hold_ms, minimum_ms) for i in (0, 1)]
    events = analyze(*channels)
    gaps = sorted(row['duration_ms'] for row in events if row['event'] == 'response_gap')
    return dict(caller_turns=len(channels[0]), agent_turns=len(channels[1]),
                response_p95_ms=gaps[math.ceil(.95 * len(gaps))-1] if gaps else None,
                events=events, caller_segments_ms=channels[0], agent_segments_ms=channels[1])


def fixture(path):
    rate = 8000
    spans = [[(.2, 1), (2.2, 2.9), (3.6, 4.5)], [(1.36, 2.56), (3.1, 3.4), (4.22, 4.8)]]
    pcm = array('h')
    for i in range(rate * 5):
        t = i / rate
        for channel, intervals in enumerate(spans):
            level = 5000 if any(a <= t < b for a, b in intervals) else 0
            pcm.append(round(level * math.sin(2 * math.pi * (220 + channel * 110) * t)))
    if sys.byteorder != 'little':
        pcm.byteswap()
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(pcm.tobytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('fixture').add_argument('path', type=Path)
    scan = sub.add_parser('analyze')
    scan.add_argument('path', type=Path)
    scan.add_argument('--threshold-db', type=float, default=-40)
    scan.add_argument('--hold-ms', type=int, default=100)
    scan.add_argument('--minimum-ms', type=int, default=60)
    scan.add_argument('--csv', action='store_true', help='emit one row per timing event')
    args = parser.parse_args()
    try:
        if args.command == 'fixture':
            fixture(args.path)
            return
        report = inspect(args.path, args.threshold_db, args.hold_ms, args.minimum_ms)
        if args.csv:
            writer = csv.DictWriter(sys.stdout, fieldnames=['event', 'start_ms', 'duration_ms'])
            writer.writeheader()
            writer.writerows(report['events'])
        else:
            print(json.dumps(report, indent=2))
    except (OSError, ValueError, EOFError, wave.Error) as exc:
        parser.exit(2, f'{parser.prog}: {exc}\n')


if __name__ == '__main__':
    main()
