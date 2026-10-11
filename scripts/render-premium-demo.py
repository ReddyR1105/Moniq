"""Render newly synthesized neural narration over real, verified application footage."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.runtime/premium-recording'
DOCS = ROOT / 'docs/demo'
STEM = 'Moniq_Hacklanta_Premium_Final'


def stamp(value, sep=','):
    ms = round(value * 1000)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}{sep}{ms % 1000:03}'


def ass_stamp(value):
    cs = round(value * 100)
    return f'{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(ffmpeg, *args, capture=False):
    return subprocess.run([str(ffmpeg), '-hide_banner', *map(str, args)], check=True, capture_output=capture, text=capture, cwd=WORK)


def main(ffmpeg):
    plan = json.loads((WORK / 'narration-plan.json').read_text(encoding='utf-8'))
    recorded = json.loads((WORK / 'capture-timeline.json').read_text(encoding='utf-8'))
    if recorded.get('fast'):
        raise ValueError('Preflight footage is not a final recording.')
    originals = {name: digest(DOCS / name) for name in ('Moniq_Hacklanta_Final.mp4', 'Moniq_All_Features.mp4')}
    source = WORK / 'browser.webm'
    clips = {scene['id']: scene for scene in recorded['scenes']}
    scenes = plan['scenes']
    minimum = sum(s['boundaries'][-1]['end'] + .24 for s in scenes)
    remaining = plan['target_seconds'] - minimum
    if remaining < 0:
        raise ValueError('Rewrite the narration: speech must fit without acceleration or truncation.')
    lengths = [round((s['boundaries'][-1]['end'] + .24 + remaining / len(scenes)) * 30) / 30 for s in scenes]
    lengths[-1] = plan['target_seconds'] - sum(lengths[:-1])
    ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1920', 'PlayResY: 1080', 'WrapStyle: 0', '', '[V4+ Styles]',
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           'Style: Caption,Segoe UI,30,&H00FFFFFF,&H00FFFFFF,&H00132820,&H00132820,0,0,0,0,100,100,0,0,1,0,0,2,120,120,42,1',
           'Style: Title,Segoe UI,29,&H00D7E9D5,&H00FFFFFF,&H00132820,&H00132820,-1,0,0,0,100,100,0,0,1,0,0,7,96,96,18,1',
           'Style: Note,Segoe UI,20,&H00A9CDB8,&H00FFFFFF,&H00132820,&H00132820,0,0,0,0,100,100,0,0,1,0,0,9,96,96,23,1',
           '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    captions, manifest, narration = [], [], [f'# {STEM}\n', f'New Microsoft Edge neural narration: `{plan["voice"]}`, rate `{plan["rate"]}`. No Zira audio, music, paid API credentials, or real financial data.\n', 'Moniq is spoken “Monique” (moh-NEEK); SmartApprove is spoken “Smart Approve.” Captions keep the official spellings.\n']
    elapsed = 0.0
    for i, scene in enumerate(scenes):
        length = lengths[i]
        if length < scene['boundaries'][-1]['end'] + .12:
            raise ValueError('Scene would truncate spoken audio.')
        clip = clips[scene['id']]
        rate = length / (clip['end'] - clip['start'])
        # Preserve the actual UI. Fit all of it inside the stage without cropping,
        # then keep captions in their own reserved area below the application.
        video_filter = f'trim=duration={clip["end"]-clip["start"]:.6f},setpts={rate:.9f}*(PTS-STARTPTS),scale=1728:864:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:66:color=0x0d2a20,setsar=1,fps=30,fade=t=in:st=0:d=0.09,fade=t=out:st={length-.09:.6f}:d=0.09'
        audio_filter = f'atrim=0:{scene["boundaries"][-1]["end"]+.12:.6f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.012,afade=t=out:st={scene["boundaries"][-1]["end"]+.04:.6f}:d=0.08,apad'
        run(ffmpeg, '-y', '-v', 'error', '-ss', f'{clip["start"]:.6f}', '-i', source, '-i', WORK / (scene['id'] + '.mp3'), '-t', f'{length:.6f}', '-vf', video_filter, '-af', audio_filter, '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '1', WORK / f'clip-{i:02}.mkv')
        ass.append(f'Dialogue: 1,{ass_stamp(elapsed)},{ass_stamp(elapsed+length)},Title,,0,0,0,,{scene["title"]}')
        for boundary in scene['boundaries']:
            start, end = elapsed + boundary['start'], elapsed + boundary['end']
            wrapped = textwrap.wrap(boundary['text'], width=98, break_long_words=False, break_on_hyphens=False)
            if len(wrapped) > 2:
                raise ValueError('Caption is too long; split the narration sentence.')
            text = '\n'.join(wrapped)
            captions.append((start, end, text))
            ass.append(f'Dialogue: 2,{ass_stamp(start)},{ass_stamp(end)},Caption,,0,0,0,,{text.replace(chr(10), chr(92)+"N")}')
        narration.append(f'## {stamp(elapsed, ".")} — {scene["title"]}\n\n{scene["text"]}\n')
        manifest.append({'id': scene['id'], 'begin': elapsed, 'end': elapsed+length, 'source_begin': clip['start'], 'source_end': clip['end'], 'video_speed_ratio': 1/rate, 'speech_rate': '+15%', 'speech_last_boundary': elapsed + scene['boundaries'][-1]['end']})
        elapsed += length
        print('Encoded scene', scene['id'], flush=True)
    ass.append(f'Dialogue: 1,0:00:00.00,{ass_stamp(elapsed)},Note,,0,0,0,,SYNTHETIC DEMO · NO LIVE GMAIL ACCESS')
    (WORK / 'captions.ass').write_text('\n'.join(ass), encoding='utf-8')
    (WORK / 'clips.txt').write_text('\n'.join(f"file 'clip-{i:02}.mkv'" for i in range(len(scenes))), encoding='utf-8')
    # Two-pass integrated normalization: stable volume, -16 LUFS, <= -1.5 dBTP.
    measurement = run(ffmpeg, '-v', 'info', '-f', 'concat', '-safe', '0', '-i', 'clips.txt', '-vn', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json', '-f', 'null', '-', capture=True)
    measured = json.loads(re.findall(r'\{\s*"input_i".*?\}', measurement.stderr, re.S)[-1])
    normalize = f'loudnorm=I=-16:TP=-1.5:LRA=7:measured_I={measured["input_i"]}:measured_TP={measured["input_tp"]}:measured_LRA={measured["input_lra"]}:measured_thresh={measured["input_thresh"]}:offset={measured["target_offset"]}:linear=true:print_format=json'
    pending = WORK / 'premium-verified.mp4'
    rendered = run(ffmpeg, '-y', '-v', 'info', '-f', 'concat', '-safe', '0', '-i', 'clips.txt', '-vf', "ass=captions.ass", '-af', normalize, '-t', '90', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', pending, capture=True)
    final_normalization = json.loads(re.findall(r'\{\s*"input_i".*?\}', rendered.stderr, re.S)[-1])
    run(ffmpeg, '-v', 'error', '-xerror', '-i', pending, '-f', 'null', '-')
    # Preserve any previously supplied premium recording before replacing it.
    target = DOCS / (STEM + '.mp4')
    if target.exists():
        backup = DOCS / (STEM + '_Original_Backup.mp4')
        if backup.exists():
            backup = DOCS / (STEM + '_Backup_' + digest(target)[:12] + '.mp4')
        if not backup.exists():
            shutil.copy2(target, backup)
    shutil.copy2(pending, target)
    for name, expected in originals.items():
        if digest(DOCS / name) != expected:
            raise RuntimeError('Original recording was unexpectedly modified')
    srt = '\n\n'.join(f'{i+1}\n{stamp(start)} --> {stamp(end)}\n{text}' for i,(start,end,text) in enumerate(captions)) + '\n'
    vtt = 'WEBVTT\n\n' + '\n\n'.join(f'{stamp(start,".")} --> {stamp(end,".")}\n{text}' for start,end,text in captions) + '\n'
    (DOCS / (STEM + '.srt')).write_text(srt, encoding='utf-8')
    (DOCS / (STEM + '.vtt')).write_text(vtt, encoding='utf-8')
    (DOCS / (STEM + '_NARRATION.md')).write_text('\n'.join(narration), encoding='utf-8')
    (WORK / 'edit-timeline.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (WORK / 'encode-log.txt').write_text(rendered.stderr, encoding='utf-8')
    results = {'file': str(target), 'duration_seconds': 90, 'voice': plan['voice'], 'rate': plan['rate'], 'neural': True, 'new_audio': True, 'speech_accelerated_after_synthesis': False, 'source': 'Fresh working app browser capture; isolated synthetic databases; Gmail disabled', 'full_decode_passed': True, 'caption_cues': len(captions), 'sentence_boundary_alignment': True, 'originals_preserved': originals, 'sha256': digest(target), 'bytes': target.stat().st_size, 'normalization': final_normalization, 'human_listening_review': 'Pending owner playback; not claimed by automated validation'}
    (WORK / 'verification.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    main(parser.parse_args().ffmpeg.resolve())
