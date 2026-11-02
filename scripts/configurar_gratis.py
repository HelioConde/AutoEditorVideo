#!/usr/bin/env python3
"""Prepara um runtime MPT isolado neste projeto com o fornecedor AI Horde."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.mpt-runtime'
os.environ['MPT_HOME'] = str(RUNTIME)


def main():
    from app.config import config  # Inicializa o config.toml oficial do MPT.
    filename = Path(config.config_file)
    raw = filename.read_text(encoding='utf-8-sig')
    assert '[app]' in raw, 'config.toml sem secao [app]'
    # Substitui somente a secao [app] mantendo as outras configuracoes intactas.
    start = re.search(r'(?m)^\[app\]\s*$', raw)
    after = re.search(r'(?m)^\[[^\]]+\]\s*$', raw[start.end():])
    end = start.end() + after.start() if after else len(raw)
    section = raw[start.end():end]
    updates = {
        'video_source': '"openai_image"',
        'openai_image_base_url': '"http://127.0.0.1:7861/v1"',
        'openai_image_api_keys': '[]',
        'openai_image_model': '"ai-horde-community"',
        'openai_image_size': '"512x768"',
        'openai_image_prompt_template': '"original anime-inspired editorial illustration, cinematic composition, detailed 2d hand-drawn look, vertical framing, no text, no watermark, {term}"',
        'match_materials_to_script': 'true',
    }
    for key, value in updates.items():
        pattern = r'(?m)^' + re.escape(key) + r'\s*=\s*.*$'
        new_line = f'{key} = {value}'
        if re.search(pattern, section):
            section = re.sub(pattern, lambda _m, v=new_line: v, section, count=1)
        else:
            section += '\n' + new_line + '\n'
    updated = raw[:start.end()] + section + raw[end:]
    import toml
    toml.loads(updated)  # Pre-flight do arquivo todo.
    filename.write_text(updated, encoding='utf-8')
    print('MoneyPrinterTurbo configurado em:', filename)
    print('Fornecedor de imagens: ponte local AI Horde (sem API paga)')
    print('Config isolada pelo MPT_HOME; nao altera sua instalacao geral.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
