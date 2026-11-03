#!/usr/bin/env python3
"""Edge TTS em PT-BR com limites de palavra reais para legendas ASS.

Não altera narrações existentes nem envia nada ao YouTube.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import re

VOICE='pt-BR-AntonioNeural'
RATE='+8%'


def ass_stamp(value:float)->str:
    cs=max(0,round(value*100))
    hours,cs=divmod(cs,360000)
    minutes,cs=divmod(cs,6000)
    seconds,cs=divmod(cs,100)
    return f'{hours}:{minutes:02}:{seconds:02}.{cs:02}'


def ass_dialogues(boundaries:list[dict])->str:
    header="""[Script Info]
Title: Arquivo Otaku
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,2,95,95,380,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows=[]
    for item in boundaries:
        start=float(item['start'])
        end=float(item['end'])
        label=re.sub(r'[\r\n{}]',' ',str(item['text'])).strip()
        if end>start>=0 and label:
            rows.append(f'Dialogue: 0,{ass_stamp(start)},{ass_stamp(end)},Main,,0,0,0,,{label}')
    if not rows:raise ValueError('TTS sem marcações de palavras válidas')
    return header+'\n'.join(rows)+'\n'


def ensure_voice(episode:dict,folder:Path,*,create:bool=False,voice:str=VOICE,engine:str='edge')->tuple[Path,Path]:
    if engine == 'voicestudio':
        from voice_studio_adapter import ensure_voice_studio
        return ensure_voice_studio(episode,folder,create=create)
    if engine != 'edge':
        raise ValueError('Motor de voz desconhecido: '+str(engine))
    # Nunca reutilizar o audio VoiceStudio como se fosse Edge TTS.
    cached=sorted((p for p in folder.glob('voz-*.mp3') if not p.name.startswith('voz-voicestudio-')),
                  key=lambda p:p.stat().st_mtime,reverse=True)
    subtitles=folder/'legendas.ass'
    if cached and subtitles.is_file():return cached[0],subtitles
    if not create:
        raise FileNotFoundError('Voz/legendas não encontradas. Use -CriarVoz para gerar uma única vez.')
    script=episode.get('script','').strip()
    if not script:raise ValueError('Roteiro de narração ausente')
    async def render():
        import edge_tts
        speaker=edge_tts.Communicate(script,voice,rate=RATE,boundary='WordBoundary')
        data=bytearray();words=[]
        async for event in speaker.stream():
            if event['type']=='audio':
                data.extend(event.get('data',b''))
            elif event['type']=='WordBoundary':
                start=event.get('offset',0)/10_000_000
                dur=event.get('duration',0)/10_000_000
                if dur>0:words.append({'start':start,'end':start+dur,'text':event.get('text','')})
        if len(data)<1000:raise RuntimeError('TTS não gerou MP3 válido')
        if not words:raise RuntimeError('TTS não retornou alinhamento de palavras. Não criar legendas falsas.')
        return bytes(data),words
    audio,words=asyncio.run(render())
    folder.mkdir(parents=True,exist_ok=True)
    mp3=folder/'voz-master.mp3'
    temp=mp3.with_suffix('.partial')
    temp.write_bytes(audio);temp.replace(mp3)
    subtitles.write_text(ass_dialogues(words),encoding='utf-8')
    (folder/'marcacoes-voz.json').write_text(json.dumps({
        'voice':voice,'rate':RATE,'source':'edge-tts WordBoundary','words':words
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return mp3,subtitles
