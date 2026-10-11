"""Measure final audio and check caption bounds; subjective voice review remains human."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.runtime/premium-recording'


def main(ffmpeg):
    video = ROOT / 'docs/demo/Moniq_Hacklanta_Premium_Final.mp4'
    analysis = subprocess.run([str(ffmpeg), '-hide_banner', '-i', str(video), '-vn', '-af', 'silencedetect=noise=-45dB:d=0.6,loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    loudness = json.loads(re.findall(r'\{\s*"input_i".*?\}', analysis.stderr, re.S)[-1])
    silence = [float(n) for n in re.findall(r'silence_duration: ([\d.]+)', analysis.stderr)]
    assert -17 <= float(loudness['input_i']) <= -15, 'Unexpected integrated narration volume'
    assert float(loudness['input_tp']) < -1, 'Insufficient peak headroom'
    assert max(silence, default=0) < 1.3, 'Review a long silent gap'
    plan = json.loads((WORK / 'narration-plan.json').read_text(encoding='utf-8'))
    timeline = json.loads((WORK / 'edit-timeline.json').read_text(encoding='utf-8'))
    cues, previous = 0, 0
    for scene, spoken in zip(timeline, plan['scenes'], strict=True):
        assert scene['id'] == spoken['id']
        for boundary in spoken['boundaries']:
            start, end = scene['begin'] + boundary['start'], scene['begin'] + boundary['end']
            assert start >= previous - .002 and start < end <= scene['end'] <= 90.001
            previous, cues = end, cues + 1
    metadata = json.loads((WORK / 'voice-metadata.json').read_text(encoding='utf-8'))
    assert metadata['VoiceType'] == 'Neural' and metadata['Locale'] == 'en-US'
    assert metadata['ShortName'] == 'en-US-AndrewMultilingualNeural'
    report = {'measured_lufs': float(loudness['input_i']), 'measured_true_peak_db': float(loudness['input_tp']), 'loudness_range_lu': float(loudness['input_lra']), 'longest_detected_silence_seconds': max(silence, default=0), 'silence_intervals_seconds': silence, 'caption_cues': cues, 'caption_bounds_monotonic': True, 'provider_voice_type': metadata['VoiceType'], 'provider_voice_personalities': metadata['VoiceTag']['VoicePersonalities'], 'subjective_listening_review': 'Pending owner review; not assessed by these automated measurements'}
    (WORK / 'audio-caption-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (WORK / 'final-audio-analysis.txt').write_text(analysis.stderr, encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    main(parser.parse_args().ffmpeg.resolve())
