#!/usr/bin/env python3
"""Arquivo Otaku: miniaturas, metadados e upload YouTube (OAuth oficial).

O comando preparar NAO envia nada ao YouTube. O comando enviar e tudo
publicam por padrao como PRIVADO; so --privacidade public torna publico.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import io
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "gerados"
PREVIEW_VIDEO = ASSETS / "arquivo-otaku-piloto-codex.mp4"
EPISODE = ROOT / "conteudos" / "001-death-note.json"
OUTPUT = ASSETS / "publicacao-youtube"
STATE = OUTPUT / "estado-upload.json"
METADATA = OUTPUT / "metadata.json"
CLIENT_SECRET = ROOT / ".secrets" / "youtube-oauth-client.json"
TOKEN = ROOT / ".secrets" / "youtube-token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

BASE_STYLE = (
    "Faithful 2000s hand drawn 2D Japanese television anime, crisp ink line art, "
    "cel shading, suspenseful mood, expressive faces, cinematic dramatic light, "
    "precise anatomy, high quality original composition, not photorealistic, "
    "no 3D, no CGI, no lettering, no logos, no watermarks"
)
YOUTUBE_PROMPT = (
    "YouTube anime commentary thumbnail artwork, 16:9 landscape composition 1536x1024 "
    "with the main character Light Yagami from Death Note on the RIGHT HALF, intense "
    "calculating expression and brown hair, red and blue moody contrast, suspenseful "
    "dark city behind, LEFT HALF dark and visually uncluttered for a large title overlay. "
    + BASE_STYLE
)
TIKTOK_PROMPT = (
    "Vertical TikTok and YouTube Shorts cover artwork, 9:16 portrait composition 1024x1536, "
    "Light Yagami from Death Note in a dramatic close up with brown layered hair and serious eyes, "
    "suspenseful nighttime background, face centered slightly above the middle, "
    "dark uncluttered central area reserved for later typography. " + BASE_STYLE
)

def read_episode(path: Path = EPISODE) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {"titulo": "Por que Death Note prende tanto sem grandes batalhas?", "serie": "Death Note", "tags": ["#DeathNote", "#Anime", "#ArquivoOtaku"], "roteiro": "Análise de Death Note e do duelo entre Light e L."}

def text_metadata(ep: dict) -> dict:
    series = (str(ep.get("serie") or "Death Note")).strip()
    explicit_title = str(ep.get('titulo_youtube') or '').strip()
    explicit_description = str(ep.get('descricao_youtube') or '').strip()
    if series.casefold() == "death note":
        # Respeita o novo titulo do plano editorial quando informado via --episodio,
        # mas preserva o titulo do piloto antigo quando o episodio nao tem plano novo.
        proposed = str(ep.get('titulo') or '').strip()
        if proposed.startswith('O segredo de Death Note:'):
            title = (proposed + ' 🧠 #Shorts')[:100]
        else:
            title = "Por que Death Note prende tanto SEM LUTAS? 🧠 #Shorts"
        discussion = ("A disputa psicológica entre Light Yagami e L transforma cada "
                      "conversa em um jogo de estratégia e consequências.")
    else:
        title = (str(ep.get('titulo') or f'O segredo de {series}').strip()[:88] + " #Shorts")
        discussion = str(ep.get('tese_original') or ep.get('observacoes') or 'Uma análise original do tema e dos personagens.')
    title = (explicit_title or title)[:100]
    description = (
        f"O que torna {series} tão interessante? 👀\n\n"
        f"Neste vídeo do Arquivo Otaku: {discussion}\n\n"
        "Qual é sua opinião? Conte nos comentários!\n\n"
        "Análise e comentário com ilustrações geradas por IA; a obra e os personagens "
        "pertencem aos respectivos titulares.\n\n"
        "#Anime #Otaku #AnimeBrasil #Shorts"
    )
    if explicit_description:
        description = explicit_description[:5000]
    # Nao repetir tags de Death Note nos proximos episodios de outras franquias.
    tags = (["Death Note", "Light Yagami", "L"] if series.casefold() == "death note" else [series])
    tags.extend(["Anime", "Otaku", "Anime Brasil", "Arquivo Otaku", "Anime Shorts"])
    return {"titulo":title, "descricao":description[:5000], "tags":tags, "categoria":"24", "idioma":"pt-BR", "feito_para_criancas":False, "tema":ep.get("titulo", "")}

def parse_metadata_ai(text: str, fallback: dict) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match: return fallback
    try: obj = json.loads(match.group())
    except ValueError: return fallback
    if not isinstance(obj, dict): return fallback
    title = str(obj.get("titulo") or "").strip()
    description = str(obj.get("descricao") or "").strip()
    if not (5 <= len(title) <= 100 and 50 <= len(description) <= 5000): return fallback
    result = dict(fallback)
    result["titulo"] = title
    result["descricao"] = description
    return result

def get_proxy_auth() -> tuple[str, str]:
    path = ROOT / "chatgpt-codex-proxy" / ".env"
    if not path.is_file(): raise RuntimeError("Proxy sem arquivo .env. Execute testar-codex-proxy.ps1 primeiro.")
    text = path.read_text(encoding="utf-8-sig")
    m = re.search(r"(?m)^PROXY_API_KEY\s*=\s*(.+?)\s*$", text)
    if not m: raise RuntimeError("PROXY_API_KEY nao encontrada no .env.")
    return "http://127.0.0.1:8080/v1", m.group(1).strip().strip("\"'")

def proxy_account_status() -> dict:
    """Read-only local health check. Never print account IDs, emails or tokens."""
    import requests
    base, key = get_proxy_auth()
    try:
        response = requests.get(
            base.removesuffix('/v1') + '/admin/accounts',
            headers={'Authorization': f'Bearer {key}'},
            timeout=(5, 12),
        )
        response.raise_for_status()
        accounts = response.json().get('accounts', [])
        if not isinstance(accounts, list):
            raise RuntimeError('Resposta inesperada da lista de contas')
        return {
            'total': len(accounts),
            'elegiveis': sum(1 for a in accounts if a.get('eligible_now') is True),
            'inativas': sum(1 for a in accounts if a.get('status') != 'active'),
        }
    except requests.RequestException as exc:
        raise RuntimeError('Nao foi possivel consultar contas do proxy local') from exc


def verify_oauth_config() -> None:
    """Fail before calling paid/limited image or text providers."""
    if not CLIENT_SECRET.is_file():
        raise RuntimeError(
            'Credenciais OAuth ausentes. Para publicar no YouTube, crie um cliente '
            'OAuth tipo Aplicativo para computador em Google Cloud e salve o JSON em '
            + str(CLIENT_SECRET) + '. Execute -Etapa preparar para trabalhar sem upload.'
        )
    try:
        data = json.loads(CLIENT_SECRET.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        raise RuntimeError('JSON OAuth encontrado, mas nao foi possivel ler/validar o arquivo') from exc
    client = data.get('installed') if isinstance(data, dict) else None
    if not isinstance(client, dict) or not client.get('client_id') or not client.get('client_secret'):
        raise RuntimeError('JSON incorreto: baixe as credenciais OAuth do tipo Aplicativo para computador, nao chave de API ou cliente Web')


def diagnose(args) -> None:
    print('[DIAGNOSTICO] Nenhum upload ou geracao de IA sera executado.')
    for name, target in (
        ('MP4 do piloto', args.video),
        ('OAuth cliente', CLIENT_SECRET),
        ('OAuth token salvo', TOKEN),
        ('Metadados', METADATA),
        ('Miniatura YouTube', OUTPUT/'miniatura-youtube.jpg'),
        ('Capa vertical', OUTPUT/'capa-tiktok-shorts.jpg'),
    ):
        print(f"[{'OK' if target.is_file() else 'PENDENTE'}] {name}")
    try:
        status = proxy_account_status()
        print(f"[PROXY] Contas cadastradas: {status['total']}; elegiveis agora: {status['elegiveis']}; inativas: {status['inativas']}")
        if status['elegiveis'] == 0:
            print('[ACAO] Proxy sem conta elegivel. Execute .\testar-codex-proxy.ps1 -Acao status e, se preciso, -Acao login. Verifique cota/cooldown.')
    except Exception as exc:
        print(f'[PROXY] Indisponivel para diagnostico: {type(exc).__name__}. Verifique Docker e autenticacao local.')
    if CLIENT_SECRET.is_file():
        try: verify_oauth_config(); print('[OK] Estrutura do cliente OAuth validada.')
        except RuntimeError as exc: print('[PENDENTE] '+str(exc))
    else:
        print('[ACAO] Configure OAuth no Google Cloud antes da etapa enviar. NAO compartilhe credenciais no chat.')


def ai_text(ep: dict, fallback: dict, model: str) -> dict:
    import requests
    base, key = get_proxy_auth()
    task = (
        "Crie titulo e descricao em portugues do Brasil para um Short do canal Arquivo Otaku. "
        "Retorne EXCLUSIVAMENTE JSON com chaves titulo e descricao. Titulo max 100 caracteres, "
        "atrativo sem clickbait enganoso. Descricao 400-1200 caracteres, CTA e hashtags, "
        "sem inventar fatos. Mencione que e analise. NAO inclua spoilers importantes. "
        "Tema e roteiro autenticos: " + json.dumps({"tema":ep.get("titulo"),"roteiro":ep.get("roteiro")}, ensure_ascii=False)
    )
    resp = requests.post(base + "/chat/completions", headers={"Authorization":f"Bearer {key}"}, json={"model":model,"messages":[{"role":"user","content":task}],"stream":False}, timeout=(10,90))
    resp.raise_for_status()
    return parse_metadata_ai(resp.json()["choices"][0]["message"]["content"],fallback)

def choose_source(video: Path, existing: Path | None = None) -> Path:
    # Prioriza imagem aprovada se estiver no computador do usuario.
    for p in [existing, ASSETS / "teste-codex-proxy.png", ROOT / "teste-codex-proxy.png", ASSETS / "teste-light-2d.png"]:
        if p is not None and p.is_file(): return p
    OUTPUT.mkdir(parents=True,exist_ok=True)
    path = OUTPUT / "frame-fonte.jpg"
    cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y","-ss","00:00:02","-i",str(video),"-frames:v","1",str(path)]
    try: subprocess.run(cmd,check=True,timeout=90)
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise RuntimeError("Nao encontrei imagem aprovada nem consegui extrair quadro. Instale ffmpeg ou informe --imagem-fonte.")
    if not path.is_file(): raise RuntimeError("Nao foi possivel extrair frame para miniatura")
    return path

def generate_ai_image(prompt: str, model: str, size: str, out: Path) -> Path:
    import requests
    base, key = get_proxy_auth()
    resp=requests.post(base+"/images/generations", headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}, json={"model":model,"prompt":prompt,"n":1,"size":size}, timeout=(20,300))
    if not resp.ok: raise RuntimeError(f"Geracao de imagem: HTTP {resp.status_code}: {resp.text[:260]}")
    data=resp.json()["data"][0]
    if data.get("b64_json"):
        blob=base64.b64decode(data["b64_json"])
    elif data.get("url"):
        url=data["url"]
        if url.startswith("data:"): blob=base64.b64decode(url.split(",",1)[1])
        else:
            if not url.startswith("https://"): raise RuntimeError("URL de imagem insegura recebida do proxy")
            get=requests.get(url,timeout=(10,120));get.raise_for_status();blob=get.content
    else: raise RuntimeError("Resposta do modelo nao possui b64_json nem URL")
    if len(blob)>25_000_000: raise RuntimeError("Imagem gerada maior que limite de 25MB")
    from PIL import Image
    with Image.open(io.BytesIO(blob)) as im:
        im.convert("RGB").save(out,format="JPEG",quality=93)
    return out

def font(size: int):
    from PIL import ImageFont
    names = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for item in names:
        if Path(item).exists():
            return ImageFont.truetype(item,size=size)
    return ImageFont.load_default()

def _fit_text(draw, text: str, max_width: int, start_size: int, min_size: int = 38):
    # Fit generated headlines without cutting letters or depending on a single font.
    for size in range(start_size, min_size - 1, -2):
        chosen = font(size)
        if draw.textbbox((0, 0), text, font=chosen, stroke_width=5)[2] <= max_width:
            return chosen
    return font(min_size)


def cover_hook(ep: dict) -> str:
    if str(ep.get('capa_texto') or '').strip():
        return str(ep['capa_texto']).strip()[:32].upper()
    if str(ep.get("serie", "")).lower() == "death note":
        return "SEM LUTAS?"
    title = str(ep.get("gancho") or ep.get("titulo") or "SEGREDO DO ANIME")
    return title.replace("?", "?").strip()[:30].upper()


def cover_image(src: Path, out: Path, width: int, height: int, headline: str, subtitle: str, portrait: bool):
    """Readable cover without oversized top bars or black footer blocks.

    16:9: large typography at left, bright face at right.
    9:16: face at upper/middle field and typography within mobile-safe center.
    """
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    with Image.open(src) as im:
        photo = im.convert("RGB")
    def cover(image, w, h, center_x=.5, center_y=.4):
        scale = max(w/image.width, h/image.height)
        nw, nh = round(image.width*scale), round(image.height*scale)
        resized = image.resize((nw, nh), Image.Resampling.LANCZOS)
        left = min(max(0, round((nw-w)*center_x)), nw-w)
        top = min(max(0, round((nh-h)*center_y)), nh-h)
        return resized.crop((left,top,left+w,top+h))
    from PIL import Image as _Image
    def overlay_gradient(canvas, *, axis='y', start=.38, finish=.88, alpha=215):
        layer = _Image.new("RGBA", canvas.size, (0,0,0,0))
        mask = _Image.new("L", canvas.size)
        if axis == 'y':
            vals = [int(alpha * max(0., min(1., (y/height-start)/max(.01,finish-start))))
                    for y in range(height)]
            for y,a in enumerate(vals):
                ImageDraw.Draw(mask).line((0,y,width,y),fill=a)
        else:
            d=ImageDraw.Draw(mask)
            for x in range(width):
                strength=max(0., min(1., (finish-x/width)/max(.01,finish-start)))
                d.line((x,0,x,height),fill=int(alpha*strength))
        layer.paste((2,5,15,255),(0,0,width,height))
        layer.putalpha(mask)
        return _Image.alpha_composite(canvas.convert('RGBA'),layer)
    if portrait:
        canvas=cover(photo,width,height,center_y=.19)
        # Gentle lift in the upper portrait prevents the expression disappearing.
        canvas=ImageEnhance.Brightness(canvas).enhance(1.04)
        canvas=overlay_gradient(canvas,axis='y',start=.43,finish=.81,alpha=226)
        draw=ImageDraw.Draw(canvas)
        # Small corner brand, never a large horizontal bar over the eyes.
        badge=(52,235,358,298)
        draw.rounded_rectangle(badge,radius=17,fill=(4,8,17,216))
        draw.text((74,251),'ARQUIVO OTAKU',font=font(28),fill='#f1f4ff')
        title_font=_fit_text(draw,headline,width-135,130,75)
        text_y=int(height*.62)
        draw.text((width//2,text_y),headline,font=title_font,anchor='mm',fill='#FFFFFF',
                  stroke_width=7,stroke_fill='#04040B')
        sub_font=_fit_text(draw,subtitle,width-170,48,30)
        draw.text((width//2,text_y+132),subtitle,font=sub_font,anchor='mm',
                  fill='#FF637A',stroke_width=3,stroke_fill='#05050B')
    else:
        # Blur a wide background behind the headline and retain an unblurred
        # character portrait on the right. Logo is subordinate to the hook.
        canvas=cover(photo,width,height).filter(ImageFilter.GaussianBlur(22))
        canvas=ImageEnhance.Brightness(canvas).enhance(.55)
        character=cover(photo,int(width*.59),height,center_x=.5,center_y=.21)
        canvas.paste(character,(width-character.width,0))
        canvas=overlay_gradient(canvas,axis='x',start=.26,finish=.72,alpha=252)
        draw=ImageDraw.Draw(canvas)
        draw.text((69,74),'ARQUIVO OTAKU',font=font(29),fill='#FF6576')
        draw.rectangle((69,125,242,132),fill='#FF566B')
        tokens=headline.split()
        lines='\n'.join(tokens) if len(tokens)==2 else headline
        size=108
        while size>70:
            title_font=font(size)
            bbox=draw.multiline_textbbox((0,0),lines,font=title_font,spacing=8,stroke_width=5)
            if bbox[2]-bbox[0]<=int(width*.51):break
            size-=2
        draw.multiline_text((69,217),lines,font=font(size),spacing=9,fill='#FFFFFF',
                            stroke_width=5,stroke_fill='#06070C')
        sub_font=_fit_text(draw,subtitle,590,37,28)
        draw.text((69,577),subtitle,font=sub_font,fill='#FFB5BF',
                  stroke_width=2,stroke_fill='#080913')
    out.parent.mkdir(parents=True,exist_ok=True)
    canvas.convert('RGB').save(out,'JPEG',quality=92,optimize=True,progressive=True)
    return out

def prepare(args):
    from PIL import Image  # require Pillow
    if not args.video.is_file():raise RuntimeError(f"Video nao encontrado: {args.video}. Gere primeiro com .\\gerar-video-codex.ps1")
    OUTPUT.mkdir(parents=True,exist_ok=True)
    ep=read_episode(args.episodio)
    baseline=text_metadata(ep)
    ai_available = True
    if args.arte_ia or args.texto_ia:
        try:
            status = proxy_account_status()
            if status['elegiveis'] == 0:
                ai_available = False
                print('[AVISO] Proxy sem contas elegiveis: nao tentarei geracoes por IA. Revise -Acao status / -Acao login / cota.')
        except Exception as exc:
            ai_available = False
            print(f'[AVISO] Nao consegui verificar contas do proxy ({type(exc).__name__}); geracao por IA ignorada.')
    old_manifest=OUTPUT/'manifesto.json'
    source_changed=False
    if old_manifest.is_file():
        try:
            existing_manifest=json.loads(old_manifest.read_text(encoding='utf-8-sig'))
            source_changed=(Path(existing_manifest.get('video','')).resolve()!=args.video.resolve())
        except (OSError,ValueError):source_changed=True
    if not METADATA.is_file() or args.refazer or source_changed:
        meta=baseline
        if args.texto_ia and ai_available:
            try:
                meta=ai_text(ep,baseline,args.modelo_texto)
                print("[OK] Titulo e descricao gerados pela IA do proxy")
            except Exception as e:
                print(f"[AVISO] IA de texto indisponivel ({type(e).__name__}). Usando metadados locais.")
        METADATA.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    else:
        meta=json.loads(METADATA.read_text(encoding="utf-8-sig"))
        print("[OK] Mantendo titulo e descricao existentes em metadata.json")
    source=choose_source(args.video,args.imagem_fonte)
    yt_source, short_source=source,source
    if args.arte_ia and ai_available and (args.refazer or not (OUTPUT/"arte-youtube.jpg").is_file()):
        try:yt_source=generate_ai_image(YOUTUBE_PROMPT,args.modelo_imagem,"1536x1024",OUTPUT/"arte-youtube.jpg")
        except Exception as e:print(f"[AVISO] Falhou arte IA YouTube ({type(e).__name__}): {str(e)[:130]}. Usando quadro local.")
    elif not args.refazer and (OUTPUT/"arte-youtube.jpg").is_file():yt_source=OUTPUT/"arte-youtube.jpg"
    if args.arte_ia and ai_available and (args.refazer or not (OUTPUT/"arte-shorts.jpg").is_file()):
        try:short_source=generate_ai_image(TIKTOK_PROMPT,args.modelo_imagem,"1024x1536",OUTPUT/"arte-shorts.jpg")
        except Exception as e:print(f"[AVISO] Falhou arte IA Shorts ({type(e).__name__}): {str(e)[:130]}. Usando quadro local.")
    elif not args.refazer and (OUTPUT/"arte-shorts.jpg").is_file():short_source=OUTPUT/"arte-shorts.jpg"
    cover_image(yt_source,OUTPUT/"miniatura-youtube.jpg",1280,720,cover_hook(ep),str(ep.get('serie') or 'ANIME').upper(),False)
    if args.capa_final_shorts:
        from PIL import Image
        approved = args.capa_final_shorts.expanduser().resolve()
        if not approved.is_file():
            raise RuntimeError("Capa aprovada de Shorts ausente: " + str(approved))
        with Image.open(approved) as image:
            image.load()
            width, height = image.size
            if height < 640 or abs(width / height - 9 / 16) > .02:
                raise RuntimeError("Capa aprovada deve ser vertical 9:16 e ter pelo menos 640px de altura")
            destination = OUTPUT / "capa-tiktok-shorts.jpg"
            if approved != destination.resolve():
                if image.format == "JPEG":
                    shutil.copy2(approved, destination)
                else:
                    image.convert("RGB").save(destination, "JPEG", quality=94, optimize=True)
        print("[CAPA] Usando a capa 9:16 final aprovada, sem redesenhar: "+str(approved))
    else:
        cover_image(short_source,OUTPUT/"capa-tiktok-shorts.jpg",1080,1920,cover_hook(ep),str(ep.get('serie') or 'ANIME').upper(),True)
    # Store exact source MP4 and generated files, avoid storing secrets.
    manifest={"video":str(args.video.resolve()),"miniatura_youtube":str((OUTPUT/"miniatura-youtube.jpg").resolve()),"capa_shorts":str((OUTPUT/"capa-tiktok-shorts.jpg").resolve()),"metadata":str(METADATA.resolve()),"prompts":{"youtube":YOUTUBE_PROMPT,"shorts":TIKTOK_PROMPT}}
    (OUTPUT/"manifesto.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OK] Miniatura YouTube: " + str(OUTPUT/"miniatura-youtube.jpg"))
    print("[OK] Capa TikTok/Shorts: " + str(OUTPUT/"capa-tiktok-shorts.jpg"))
    print("[OK] Titulo: "+meta["titulo"])
    print("[OK] Metadados editaveis: "+str(METADATA))
    return manifest

def auth_youtube():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError: raise RuntimeError("Dependencias YouTube ausentes. Execute instalar-publicacao.ps1 ou python -m pip install -r requirements-publicacao.txt")
    verify_oauth_config()
    credentials=None
    if TOKEN.is_file():
        try: credentials=Credentials.from_authorized_user_file(str(TOKEN),SCOPES)
        except Exception: credentials=None
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow=InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET),SCOPES)
            credentials=flow.run_local_server(port=0,host="localhost",open_browser=True,authorization_prompt_message="Abra esta URL para autorizar acesso ao canal certo: {url}",prompt="consent")
        TOKEN.parent.mkdir(parents=True,exist_ok=True)
        TOKEN.write_text(credentials.to_json(),encoding="utf-8")
    return build("youtube","v3",credentials=credentials,cache_discovery=False)

def video_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def save_state(value: dict, per_video: Path) -> None:
    # Persist one record per MP4, and a compatibility copy for old scripts.
    data=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    for path in (per_video,STATE):
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.tmp')
        temporary.write_text(data,encoding='utf-8')
        temporary.replace(path)


def upload(args):
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError:
        raise RuntimeError("Bibliotecas de upload ausentes; instale requirements-publicacao.txt")
    if not METADATA.is_file():
        raise RuntimeError("Nao ha metadata.json. Execute -Etapa preparar primeiro")
    if not args.video.is_file(): raise RuntimeError("MP4 nao encontrado")
    meta=json.loads(METADATA.read_text(encoding="utf-8-sig"))
    title=meta.get("titulo","").strip()
    desc=meta.get("descricao","").strip()
    if not (1<=len(title)<=100):raise RuntimeError("Titulo obrigatorio: preencha titulo em metadata.json (ate 100 caracteres)")
    if len(desc)>5000:raise RuntimeError("Descricao excede 5000 caracteres")
    current_digest=video_digest(args.video)
    historical_state=OUTPUT/('estado-upload-'+current_digest[:12]+'.json')
    previous={}
    for saved in (historical_state,STATE):
        if saved.is_file():
            candidate=json.loads(saved.read_text(encoding='utf-8-sig'))
            if candidate.get('video_sha256')==current_digest:
                previous=candidate
                break
    youtube=auth_youtube()
    video_id=previous.get("video_id")
    if video_id:
        print("[OK] Upload ja registrado. Nao repetindo video: https://youtu.be/"+video_id)
    else:
        body={"snippet":{"title":title,"description":desc,"tags":meta.get("tags",[]),"categoryId":str(meta.get("categoria",24)),"defaultLanguage":meta.get("idioma","pt-BR")},"status":{"privacyStatus":args.privacidade,"selfDeclaredMadeForKids":bool(meta.get("feito_para_criancas",False))}}
        media=MediaFileUpload(str(args.video),mimetype="video/mp4",chunksize=4*1024*1024,resumable=True)
        request=youtube.videos().insert(part="snippet,status",body=body,media_body=media)
        response=None
        print("[INFO] Iniciando upload YouTube com privacidade: "+args.privacidade)
        # Avoid restarting uploads blindly; if partial transmission fails, stop for investigation.
        while response is None:
            progress,response=request.next_chunk()
            if progress is not None:print(f"[INFO] Upload: {progress.progress()*100:.1f}%",flush=True)
        video_id=response.get("id")
        if not video_id:raise RuntimeError("API nao retornou ID de video; confira YouTube Studio antes de repetir")
        previous={"video_id":video_id,"link":"https://youtu.be/"+video_id,"privacidade_solicitada":args.privacidade,"enviado_em":datetime.now(timezone.utc).isoformat(),"thumbnail_status":"pending","video_path":str(args.video.resolve()), "video_sha256":current_digest}
        save_state(previous,historical_state)
        print("[OK] Video enviado: https://youtu.be/"+video_id)
    if previous.get("thumbnail_status") != "success":
        thumb=OUTPUT/"capa-tiktok-shorts.jpg" if args.usar_capa_shorts else OUTPUT/"miniatura-youtube.jpg"
        if not thumb.is_file():print("[AVISO] Sem miniatura JPG. Execute -Etapa preparar.")
        else:
            try:
                # Shorts thumbnail upload availability depends on channel eligibility and API.
                media=MediaFileUpload(str(thumb),mimetype="image/jpeg",resumable=False)
                youtube.thumbnails().set(videoId=video_id,media_body=media).execute()
                previous["thumbnail_status"]="success"
                previous["thumbnail_file"]=str(thumb.resolve())
                save_state(previous,historical_state)
                print("[OK] Miniatura anexada ao YouTube")
            except HttpError as exc:
                code=getattr(exc.resp,"status","?")
                previous["thumbnail_status"]=f"error_http_{code}"
                previous["thumbnail_file"]=str(thumb.resolve())
                previous["thumbnail_error"]=str(exc)[:350]
                save_state(previous,historical_state)
                print(f"[AVISO] VIDEO ENVIADO, mas YouTube recusou a capa (HTTP {code}). "
                      f"A capa correta ficou em {thumb}. Abra o YouTube Studio no computador "
                      "e use Shorts > Detalhes > Miniatura > Enviar arquivo. "
                      "Nao repita o upload do MP4.")
    print("[FINAL] YouTube: https://youtu.be/"+video_id)
    print("[FINAL] Estado por video: "+str(historical_state))

def ensure_gitignore():
    """Nunca deixar credenciais OAuth ou material de publicacao no versionamento."""
    ignore=ROOT / ".gitignore"
    existing=ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    needed=[line for line in (".secrets/", "assets/gerados/publicacao-youtube/") if line not in existing.splitlines()]
    if needed:
        with ignore.open("a",encoding="utf-8") as f:
            f.write("\n# Arquivo Otaku: credenciais e arquivos de publicacao\n"+"\n".join(needed)+"\n")

def main():
    ensure_gitignore()
    p=argparse.ArgumentParser(description="Arquivo Otaku — gerar capas, metadata e enviar ao YouTube")
    p.add_argument("--etapa",choices=["preparar","enviar","tudo","diagnostico"],default="preparar")
    p.add_argument("--video",type=Path,default=PREVIEW_VIDEO)
    p.add_argument("--episodio",type=Path,default=EPISODE)
    p.add_argument("--imagem-fonte",type=Path)
    p.add_argument("--capa-final-shorts",type=Path,help="Usa JPG/PNG vertical aprovado sem redesenhar a capa")
    p.add_argument("--privacidade",choices=["private","unlisted","public"],default="public")
    p.add_argument("--modelo-imagem",choices=["gpt-image-1.5","gpt-image-2"],default="gpt-image-1.5")
    p.add_argument("--modelo-texto",default="gpt-6.1-sol")
    p.add_argument("--arte-ia",action="store_true",help="gera duas novas artes; consome cota do Codex Proxy")
    p.add_argument("--texto-ia",action="store_true",help="escreve titulo e descricao via Codex Proxy")
    p.add_argument("--usar-capa-shorts",action="store_true",default=True)
    p.add_argument("--refazer",action="store_true",help="recria titulo e artes (nao apaga registro de upload)")
    args=p.parse_args()
    args.video=args.video.expanduser().resolve()
    if args.etapa == "diagnostico":
        diagnose(args)
        return
    if args.etapa in ("enviar","tudo"):
        verify_oauth_config()  # Before calling AI services or changing generated files.
    if args.etapa in ("preparar","tudo"):prepare(args)
    if args.etapa in ("enviar","tudo"):upload(args)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("[ERRO] "+str(exc),file=sys.stderr)
        sys.exit(1)
