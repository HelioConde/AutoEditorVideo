"""Arquivo Otaku v0.7: planos de corte a partir de imagens existentes.

Nao chama APIs. Produz imagens locais 9:16 com recortes digitais controlados,
sem substituir os originais e sem utilizar midia de outros criadores.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import tempfile
import time
from PIL import Image, ImageEnhance, ImageStat

# Para 7 cenas, 14 planos com ~3 segundos cada (42 s de material).
# O roteiro/voz define a duracao final real; material restante nao e usado.
FRAMES_PER_SCENE = 2
CUT_DURATION_SECONDS = 3


def _crop_frame(source: Image.Image, zoom: float, horizontal: float, vertical: float) -> Image.Image:
    """Recorte em mesma proporcao, nunca esticando rostos."""
    w, h = source.size
    cw = min(w, round(w / zoom))
    ch = min(h, round(h / zoom))
    max_x, max_y = w - cw, h - ch
    left = round(max_x * min(1, max(0, horizontal)))
    top = round(max_y * min(1, max(0, vertical)))
    return source.crop((left,top,left+cw,top+ch)).resize((w,h),Image.Resampling.LANCZOS)



def _save_jpeg_atomic(frame: Image.Image, path: Path):
    """Write a unique closed temporary file before replacing the target on Windows.

    The old deterministic ``.partial.jpg`` name could remain locked by a viewer,
    antivirus scanner or interrupted prior run. Never modify the existing final
    image unless the new JPEG was successfully completed.
    """
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='wb', dir=path.parent, prefix=f'.{path.stem}-',
            suffix='.tmp.jpg', delete=False
        ) as output:
            temp_path = Path(output.name)
            frame.save(output, 'JPEG', quality=93, subsampling=0, optimize=True)
            output.flush()
            os.fsync(output.fileno())
        for attempt in range(3):
            try:
                os.replace(temp_path, path)
                temp_path = None
                return
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.3 * (attempt + 1))
    except PermissionError as error:
        raise PermissionError(
            f'Nao foi possivel salvar a cena em {path.parent}. '
            'Feche programas que usam a pasta, confirme permissoes de escrita '
            'e verifique se o Windows Defender bloqueou o acesso.'
        ) from error
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def create_shot_sequence(scenes: list[Path], destination: Path, seconds: int = CUT_DURATION_SECONDS):
    """Cria 2 enquadramentos por cena: abertura ampla e close cinematografico.

    A montagem nao presume que a mesma imagem seja uma cena nova: registra
    source_id, uso e crop no manifesto para auditoria posterior.
    """
    if not 1 <= len(scenes) <= 60:
        raise ValueError('Precisamos de pelo menos 1 imagem; 60 e limite tecnico, nao meta')
    destination.mkdir(parents=True,exist_ok=True)
    shots=[]
    for idx,source in enumerate(scenes,1):
        if not Path(source).is_file():
            raise FileNotFoundError(source)
        with Image.open(source) as obj:
            original=obj.convert('RGB')
            if min(original.size)<640:
                raise ValueError(f'Imagem com resolucao insuficiente: {source}')
            for variant in range(FRAMES_PER_SCENE):
                # Segundo quadro tem um leve close; alterna posicoes para evitar
                # enquadramento identico, mantendo os olhos no centro superior.
                zoom = 1.0 if variant == 0 else 1.15
                x = .5 if variant == 0 else (.40 if idx % 2 else .60)
                y = .46 if variant == 0 else .38
                frame=_crop_frame(original,zoom,x,y)
                identity=hashlib.sha256(f'{source.resolve()}|{source.stat().st_size}|{source.stat().st_mtime_ns}|{zoom}|{x}|{y}'.encode()).hexdigest()[:12]
                path=destination/f'otaku-v07-{idx:02d}-{variant+1}-{identity}.jpg'
                if not path.is_file():
                    _save_jpeg_atomic(frame,path)
                shots.append({'scene':idx,'shot':variant+1,'crop_zoom':zoom,
                              'file':str(path),'source':str(source),'seconds':seconds})
    manifest=destination/'plano-cortes-v07.json'
    tmp=manifest.with_suffix('.tmp')
    tmp.write_text(json.dumps({'version':'0.7','duration_per_cut_s':seconds,'shots':shots},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(manifest)
    return [Path(x['file']) for x in shots]
