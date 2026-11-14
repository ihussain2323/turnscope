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

## Can the recognizer still hear the payment instruction?

This experiment compares NVIDIA Parakeet TDT 0.6B v3 and Whisper tiny.en on identical audio from six original payment-support prompts. Listen to a [clean input](speech/dispute.wav), then inspect the [transcripts and scores](measurements/tiny-en.json). On the clean dispute clip, tiny.en recovered “I need to dispute a card payment from yesterday.” Adding deterministic noise at 1,200 RMS changed the decoded phrase to “I need to destroy the part team from yesterday.”

| Added noise RMS (PCM16 units) | Parakeet v3 word error rate | Whisper tiny.en word error rate | Exact phrases, Parakeet / Whisper |
| ---: | ---: | ---: | ---: |
| 0 | 1.85% | 3.70% | 6 / 6 |
| 1,200 | 31.48% | 38.89% | 1 / 2 |
| 3,600 | 70.37% | 92.59% | 0 / 0 |

Each phrase column counts successes out of six. At the middle noise level, Parakeet had fewer word errors overall but lost one more target phrase. Inspect each decoded utterance in the [Parakeet report](measurements/parakeet-v3.json) and [Whisper report](measurements/tiny-en.json).

The corpus spans 54 reference words from one synthetic voice. These measurements characterize this fixture and model only. Word error rate sums word-level edit distances across clips and divides by total reference words. Phrase recovery checks a literal contiguous token match after lowercasing and stripping punctuation. It measures exact wording, so semantically equivalent paraphrases can fail.

To reproduce Parakeet, install `sherpa-onnx==2.0.1` and `numpy==2.5.4` with Python 3.13. Extract the [int8 model archive](https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2) and run:

```sh
python3 asr_eval.py --engine parakeet --model sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
```

Parakeet loads once per run. Its per-clip times exclude model loading. Whisper launches a new process for each clip, so the timing fields measure different workloads. Model attribution and licensing are in the [NVIDIA model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).

To reproduce Whisper, build [whisper.cpp v1.8.2](https://github.com/ggml-org/whisper.cpp/tree/v1.8.2), fetch its `tiny.en` GGML model, then run:

```sh
python3 asr_eval.py --cli /path/to/whisper-cli --model /path/to/ggml-tiny.en.bin
```

The recorded run used two CPU threads with GPU inference disabled. The report contains the model SHA-256 and elapsed time including process startup per clip. The six WAV files were synthesized with the SLT voice in [Flite 2.2](https://github.com/festvox/flite/tree/v2.2). Rebuild them with `python3 speech/generate.py --flite /path/to/flite`.
