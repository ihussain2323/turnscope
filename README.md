# Turnscope

A local timing probe for voice-agent calls. Feed it a stereo recording with the caller on the left and the agent on the right. It finds overlaps, estimates the wait for a reply, and emits timestamped events you can compare across agent configurations. Audio stays on your machine.

## Try it

Requires Python 3.10+ with its standard library. The fixture is five seconds of synthetic tones with known speaker boundaries.

```sh
python3 turnscope.py fixture /tmp/turnscope-call.wav
python3 turnscope.py analyze /tmp/turnscope-call.wav --csv
python3 -m unittest discover -s tests -v
```

| Event | Start (ms) | Duration (ms) |
| --- | ---: | ---: |
| response_gap | 1000 | 360 |
| caller_barge_in | 2200 | 360 |
| response_gap | 2900 | 200 |
| agent_cut_in | 4220 | 280 |

Omit `--csv` for JSON containing the underlying segments and nearest-rank p95 reply gap. Each gap runs from the end of a caller turn to the next agent onset. If the caller speaks again first, the earlier turn is labeled unanswered. Overlaps count once per intersecting pair of turns. Coincident starts get their own simultaneous label.

## Run on a call

Export separate caller and agent tracks as 16-bit, uncompressed PCM in one stereo WAV. The analyzer computes mean square amplitude in 20 ms frames, joins gaps up to `--hold-ms` (default 100), and drops resulting turns shorter than `--minimum-ms` (default 60). Change `--threshold-db` (default −40 dBFS) to suit the recording level.

Channel order determines who interrupted whom. Crosstalk, hold music and noisy channels can trigger activity. Inspect the reported boundaries against the source audio before interpreting interruptions. Response gaps include microphone, network and playback time captured in the recording. Processing uses memory proportional to call length.
