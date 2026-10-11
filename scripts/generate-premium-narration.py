"""Generate new neural narration and service-timed sentence boundaries, never owner data."""
import asyncio
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.runtime' / 'premium-recording'


async def main():
    DEST.mkdir(parents=True, exist_ok=True)
    plan = json.loads((ROOT / 'docs/demo/premium-plan.json').read_text(encoding='utf-8'))
    voices = await edge_tts.list_voices()
    voice = next(v for v in voices if v['ShortName'] == plan['voice'])
    (DEST / 'voice-metadata.json').write_text(json.dumps(voice, indent=2), encoding='utf-8')
    for scene in plan['scenes']:
        spoken = scene['text']
        for original, pronunciation in plan['pronunciation'].items():
            spoken = spoken.replace(original, pronunciation)
        boundaries = []
        audio = DEST / (scene['id'] + '.mp3')
        # Always synthesize afresh. Fail explicitly rather than use Windows speech.
        with audio.open('wb') as stream:
            async for chunk in edge_tts.Communicate(spoken, plan['voice'], rate=plan['rate'], boundary='SentenceBoundary').stream():
                if chunk['type'] == 'audio':
                    stream.write(chunk['data'])
                elif chunk['type'] == 'SentenceBoundary':
                    caption = chunk['text']
                    for original, pronunciation in plan['pronunciation'].items():
                        caption = caption.replace(pronunciation, original)
                    boundaries.append({'start': chunk['offset'] / 10_000_000, 'end': (chunk['offset'] + chunk['duration']) / 10_000_000, 'text': caption})
        if audio.stat().st_size < 1000 or not boundaries:
            raise RuntimeError('Neural audio or alignment missing for ' + scene['id'])
        scene['boundaries'] = boundaries
        print(scene['id'], round(boundaries[-1]['end'], 2), 'seconds', flush=True)
    (DEST / 'narration-plan.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
