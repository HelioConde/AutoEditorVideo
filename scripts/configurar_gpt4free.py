#!/usr/bin/env python3
"""Configura fonte openai_image para servidor GPT4Free local, sem afetar config global."""
import os
import re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
os.environ['MPT_HOME'] = str(root / '.mpt-runtime')
from app.config import config
path=Path(config.config_file)
raw=path.read_text(encoding='utf-8-sig')
match=re.search(r'(?m)^\[app\]\s*$',raw)
if not match: raise RuntimeError('Nao foi encontrada secao [app]')
after=re.search(r'(?m)^\[[^\]]+\]\s*$',raw[match.end():])
end=match.end()+after.start() if after else len(raw)
section=raw[match.end():end]
updates={
    'video_source':'"openai_image"',
    'openai_image_base_url':'"http://127.0.0.1:1337/v1"',
    'openai_image_api_keys':'[]',
    'openai_image_model':'"flux"',
    'openai_image_size':'"512x768"',
    'openai_image_prompt_template':'"original high-quality anime-inspired illustration, cinematic lighting, cohesive noir atmosphere, vertical composition, no text, no watermark, {term}"',
    'match_materials_to_script':'true',
    'video_clip_duration':'6',
}
for k,v in updates.items():
    p=r'(?m)^'+re.escape(k)+r'\s*=\s*.*$'
    if re.search(p,section): section=re.sub(p,lambda _m,key=k,value=v:key+' = '+value,section,count=1)
    else: section+='\n'+k+' = '+v+'\n'
new=raw[:match.end()]+section+raw[end:]
import toml
toml.loads(new)
path.write_text(new,encoding='utf-8')
print('MoneyPrinterTurbo -> GPT4Free local, config:',path)
print('Modelo flux | sem chave no kit | uma imagem por termo de cena')
