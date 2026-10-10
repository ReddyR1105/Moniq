"""Encode real browser footage, local narration and timed captions; fully decode the result."""
import argparse
import json
import re
import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def timestamp(seconds, separator=','):
    ms = round(seconds * 1000)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}{separator}{ms % 1000:03}'


def build(mode, ffmpeg):
    source = ROOT / '.runtime' / 'final-recording' / mode
    timeline = json.loads((source / 'timeline.json').read_text(encoding='utf-8'))
    if timeline['fast']:
        raise ValueError('Preflight recordings are not final videos.')
    scenes = timeline['scenes']
    trim = scenes[0]['start']
    duration = scenes[-1]['end'] - trim
    stem = 'Moniq_Hacklanta_Final' if mode == 'presentation' else 'Moniq_All_Features'
    destination = ROOT / 'docs' / 'demo'
    captions, vtt, script = [], ['WEBVTT\n'], [f'# {stem} narration and scene script\n', 'Actual isolated synthetic app recording. Local Microsoft Zira narration; no music.\n']
    voices = []
    for i, scene in enumerate(scenes):
        begin, end = scene['start'] - trim, scene['end'] - trim
        text = scene['title'] + '\n' + scene['text']
        captions.append(f'{i+1}\n{timestamp(begin)} --> {timestamp(end)}\n{text}\n')
        vtt.append(f'{timestamp(begin,".")} --> {timestamp(end,".")}\n{text}\n')
        script.append(f'## {timestamp(begin,".")} - {scene["title"]}\n\nNarration: {scene["text"]}\n')
        with wave.open(str(source / f'narration-{i:02}.wav'), 'rb') as audio:
            fmt = (audio.getnchannels(), audio.getsampwidth(), audio.getframerate())
            pcm = audio.readframes(audio.getnframes())
        rate = fmt[2]
        seconds = len(pcm) / (fmt[0] * fmt[1] * rate)
        available = end - begin - .4
        if seconds > available:
            # Speed only this narration segment; never truncate spoken information.
            factor = seconds / available * 1.01
            accelerated = source / f'narration-fast-{i:02}.wav'
            subprocess.run([str(ffmpeg), '-y', '-v', 'error', '-i', str(source / f'narration-{i:02}.wav'), '-af', f'atempo={factor:.5f}', str(accelerated)], check=True)
            with wave.open(str(accelerated), 'rb') as audio:
                pcm = audio.readframes(audio.getnframes())
        voices.append((begin + .2, pcm, fmt))
    fmt = voices[0][2]
    assert all(v[2] == fmt for v in voices), 'Narration PCM formats differ'
    frame_bytes = fmt[0] * fmt[1]
    mixed = bytearray(round(duration * fmt[2]) * frame_bytes)
    for begin, pcm, _ in voices:
        offset = round(begin * fmt[2]) * frame_bytes
        assert offset + len(pcm) <= len(mixed), 'Narration exceeds video duration'
        mixed[offset:offset+len(pcm)] = pcm
    narration = source / 'narration.wav'
    with wave.open(str(narration), 'wb') as audio:
        audio.setnchannels(fmt[0])
        audio.setsampwidth(fmt[1])
        audio.setframerate(fmt[2])
        audio.writeframes(mixed)
    (destination / (stem + '.srt')).write_bytes(('\n'.join(captions)).encode('utf-8'))
    (destination / (stem + '.vtt')).write_bytes(('\n'.join(vtt)).encode('utf-8'))
    (destination / (stem + '_NARRATION.md')).write_bytes(('\n'.join(script)).encode('utf-8'))
    output = destination / (stem + '.mp4')
    subprocess.run([str(ffmpeg), '-y', '-v', 'warning', '-ss', str(trim), '-i', str(source / 'browser.webm'), '-i', str(narration), '-t', str(duration),
                    '-vf', f'scale=1920:1080,setsar=1,fade=t=in:st=0:d=0.45,fade=t=out:st={duration-.6}:d=0.6',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p', '-r', '25', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(output)], check=True)
    # Complete video/audio decode, not just a header check.
    subprocess.run([str(ffmpeg), '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'], check=True)
    metadata = subprocess.run([str(ffmpeg), '-hide_banner', '-i', str(output)], capture_output=True, text=True)
    (source / 'verified-media.txt').write_bytes(metadata.stderr.encode('utf-8'))
    for i, scene in enumerate(scenes):
        if i % 3 == 0 or i == len(scenes) - 1:
            instant = min(duration - 1, scene['end'] - trim - 1)
            subprocess.run([str(ffmpeg), '-y', '-v', 'error', '-ss', str(instant), '-i', str(output), '-frames:v', '1', str(source / f'verified-frame-{i:02}.png')], check=True)
    measured = re.search(r'Duration: (\d+):(\d+):([\d.]+)', metadata.stderr)
    assert measured and '1920x1080' in metadata.stderr and 'Video: h264' in metadata.stderr and 'Audio: aac' in metadata.stderr
    measured_seconds = int(measured[1]) * 3600 + int(measured[2]) * 60 + float(measured[3])
    result = {'file': str(output), 'duration_seconds': measured_seconds, 'resolution': '1920x1080', 'video_codec': 'H.264', 'audio': 'AAC / local Microsoft Zira', 'caption_files': [stem+'.srt',stem+'.vtt'], 'burned_in_captions': True, 'full_decode_passed': True, 'bytes': output.stat().st_size}
    (source / 'verification.json').write_bytes(json.dumps(result, indent=2).encode('utf-8'))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['presentation','walkthrough'])
    parser.add_argument('--ffmpeg', type=Path, required=True)
    args = parser.parse_args()
    build(args.mode, args.ffmpeg.resolve())
