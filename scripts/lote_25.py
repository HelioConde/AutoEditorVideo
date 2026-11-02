#!/usr/bin/env python3
"""Fila de producao offline. Nao tem metodo de upload ou acesso a OAuth."""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "dados" / "lote-25-pautas.json"
RESULTS = ROOT / "assets" / "gerados" / "lotes" / "lote-25-resultados.json"
SAFE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def read_manifest(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if data.get("schema") != "arquivo-otaku/lote/v1":
        raise ValueError("Manifesto desconhecido")
    items = data.get("items")
    if not isinstance(items, list) or len(items) > 25:
        raise ValueError("Manifesto precisa conter ate 25 pautas")
    ids = [item.get("id") for item in items]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not SAFE_ID.fullmatch(i) for i in ids):
        raise ValueError("IDs invalidos ou repetidos")
    return data


def safe_episode_path(value: str, root: Path = ROOT) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("Plano deve ser caminho relativo em conteudos/")
    candidate = (root / value).resolve()
    content_root = (root / "conteudos").resolve()
    if not candidate.is_relative_to(content_root) or candidate.suffix.lower() != ".json":
        raise ValueError("Plano fora da pasta conteudos/")
    return candidate


def validate_item(item: dict, root: Path = ROOT) -> tuple[list[str], dict | None]:
    problems = []
    if item.get("aprovado") is not True:
        problems.append("roteiro nao aprovado")
    if item.get("checagem_factual") is not True:
        problems.append("fatos nao revisados")
    if item.get("direitos_revisados") is not True:
        problems.append("direitos nao revisados")
    source = item.get("episodio")
    if not source:
        return problems + ["JSON de episodio ausente"], None
    try:
        path = safe_episode_path(source, root)
        plan = json.loads(path.read_text(encoding="utf-8-sig"))
        script = str(plan.get("roteiro_melhorado", "")).strip()
        scenes = plan.get("cenas", [])
        if not SAFE_ID.fullmatch(str(plan.get("id", ""))):
            problems.append("id invalido no plano")
        if len(script.split()) < 55:
            problems.append("roteiro curto demais")
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 60:
            problems.append("o roteiro precisa de 1 a 60 cenas (limite técnico, sem quantidade fixa)")
        if len(script) > 1000 and len(script.split()) > 180:
            problems.append("revisar duracao do roteiro")
        if not str(plan.get("prova_da_obra_a_verificar", "")).strip():
            problems.append("falta fonte/prova da obra")
        if not str(plan.get("gancho_primeiros_segundos", "")).strip():
            problems.append("falta gancho inicial")
        if plan.get("id") != item.get("id"):
            problems.append("id do episodio diferente do manifesto")
        return problems, plan
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        return problems + [f"episodio invalido: {type(exc).__name__}"], None


def eligible_items(manifest: dict, root: Path = ROOT) -> tuple[list[tuple[dict, dict]], list[dict]]:
    ready, rejected = [], []
    scripts = []
    for item in manifest["items"]:
        errors, plan = validate_item(item, root)
        if plan and not errors:
            script = " ".join(plan["roteiro_melhorado"].lower().split())
            if any(SequenceMatcher(None, script, other).ratio() >= .83 for other in scripts):
                errors.append("roteiro muito semelhante a outro do lote")
            else:
                scripts.append(script)
        if errors:
            rejected.append({"id":item["id"],"problemas":errors})
        else:
            ready.append((item,plan))
    return ready,rejected


def result_path(plan: dict, reuse: bool, root: Path = ROOT) -> Path:
    mode = "reuso" if reuse else "codex"
    return root / "assets" / "gerados" / f"arquivo-otaku-{plan['id']}-{mode}.mp4"


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ffprobe_check(video: Path) -> tuple[bool,str]:
    try:
        cp = subprocess.run(["ffprobe","-v","error","-show_streams","-show_format",
                             "-of","json",str(video)],check=True,text=True,capture_output=True,timeout=45)
        data = json.loads(cp.stdout)
        streams = data.get("streams",[])
        visuals = [s for s in streams if s.get("codec_type") == "video"]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        duration = float(data.get("format",{}).get("duration",0))
        if not visuals or not audio:
            return False,"sem audio ou video"
        width,height = int(visuals[0]["width"]),int(visuals[0]["height"])
        if abs(width/height - 9/16) > .01:
            return False,"video nao esta em 9:16"
        if not 15 <= duration <= 180:
            return False,f"duracao fora do intervalo: {duration:.1f}s"
        return True,f"QA tecnico basico: {duration:.1f}s {width}x{height}"
    except (FileNotFoundError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        return False,f"ffprobe falhou: {type(exc).__name__}"


def run_batch(manifest: dict, root: Path, limit: int, reuse: bool, confirm: bool, continue_on_error: bool) -> int:
    ready, rejected = eligible_items(manifest, root)
    print(f"[LOTE] {len(ready)} aprovados; {len(rejected)} pendentes. Maximo solicitado: {limit}.")
    for row in rejected[:25]:
        print(f"[PENDENTE] {row['id']}: {', '.join(row['problemas'])}")
    if not confirm:
        print("[PREVIA] Nenhum video, imagem, upload ou chamada de IA executado.")
        return 0
    if not ready:
        print("[BLOQUEADO] Nenhum episodio passou pelo controle editorial. Nada sera gerado.")
        return 2
    state_path = root / "assets" / "gerados" / "lotes" / "lote-25-resultados.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {"items":{}}
    statuses = existing.setdefault("items",{})
    failures = 0
    for item, plan in ready[:limit]:
        path = safe_episode_path(item["episodio"], root)
        digest = file_fingerprint(path)
        out = result_path(plan, reuse, root)
        previous = statuses.get(item["id"],{})
        if previous.get("hash")==digest and previous.get("status")=="concluido" and out.is_file():
            print(f"[CACHE] {item['id']} concluido anteriormente.")
            continue
        cmd = [sys.executable,str(root / "scripts" / "gerar_video_codex.py"),"--plano",str(path)]
        if reuse:
            cmd.append("--reutilizar-imagens")
        print(f"[GERANDO] {item['id']} — {item['pauta']}",flush=True)
        try:
            rc = subprocess.call(cmd,cwd=str(root))
            if rc:
                raise RuntimeError(f"gerador retornou codigo {rc}")
            if not out.is_file():
                raise RuntimeError("gerador concluiu sem MP4 encontrado")
            passed, details = ffprobe_check(out)
            if not passed:
                raise RuntimeError(details)
            statuses[item["id"]]={"status":"concluido","hash":digest,"arquivo":str(out),"qa":details}
            print(f"[OK] {item['id']}: {details}")
        except Exception as exc:
            failures += 1
            statuses[item["id"]]={"status":"erro","hash":digest,"erro":str(exc)[:300]}
            print(f"[FALHOU] {item['id']}: {str(exc)[:300]}",file=sys.stderr)
            if not continue_on_error:
                state_path.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                return 1
        state_path.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[CONCLUIDO] Arquivos locais preparados. Nenhum video foi enviado ao YouTube.")
    return 1 if failures else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Planeja ate 25 videos; nunca publica no YouTube.")
    p.add_argument("--manifesto",type=Path,default=DEFAULT_MANIFEST)
    p.add_argument("--acao",choices=["status","renderizar"],default="status")
    p.add_argument("--limite",type=int,default=25)
    p.add_argument("--confirmar-render",action="store_true")
    p.add_argument("--reutilizar-imagens",action="store_true")
    p.add_argument("--continuar-em-erro",action="store_true")
    args = p.parse_args()
    if not 1 <= args.limite <= 25:
        p.error("limite deve ficar entre 1 e 25")
    manifest=read_manifest(args.manifesto)
    return run_batch(manifest,ROOT,args.limite,args.reutilizar_imagens,
                     args.acao=="renderizar" and args.confirmar_render,args.continuar_em_erro)


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (ValueError,OSError) as exc:
        print(f"[ERRO] {exc}",file=sys.stderr)
        raise SystemExit(2)
