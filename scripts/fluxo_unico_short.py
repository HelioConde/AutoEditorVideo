#!/usr/bin/env python3
"""Single-command Arquivo Otaku Short pipeline: voice -> AI art -> MP4 -> metadata -> YouTube.

Recover from independent generation failures using cache; never ignore invalid
voice, unapproved art, over-60-second MP4, missing cover, or failed upload.
No YouTube upload without --publicar. Designed for PowerShell 5.1 / Windows.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from roteiro_para_storyboard import select_episode
from shorts_duration import validate_video

PROFILES = ("equilibrado", "vivo", "ultrassutil")
MODELS = ("gpt-image-1.5", "gpt-image-2")
OUTPUT = ROOT / "assets" / "gerados" / "shorts-animados"
PUBLICATION = ROOT / "assets" / "gerados" / "publicacao-youtube"
OAUTH = ROOT / ".secrets" / "youtube-oauth-client.json"


class PipelineError(RuntimeError):
    pass


def run_command(parts: list[str], *, label: str) -> bool:
    """Run stages synchronously and retain their native logs, no shell quoting."""
    print(f"\n[ETAPA] {label}", flush=True)
    result = subprocess.run(parts, cwd=ROOT, check=False)
    if result.returncode:
        print(f"[AVISO] {label}: codigo {result.returncode}. O cache local foi preservado.",
              file=sys.stderr, flush=True)
    return result.returncode == 0


def require_success(parts: list[str], *, label: str) -> None:
    if not run_command(parts, label=label):
        raise PipelineError(f"{label} falhou. Nao sera feita publicacao.")


def get_storyboard(episode_id: str, *, max_hold: float):
    from master_scenes import production_storyboard, read_storyboard
    path = production_storyboard(episode_id, max_hold)
    plan = read_storyboard(path)
    if plan.get("id") != episode_id:
        raise PipelineError("O storyboard fixado pertence a outro episodio.")
    return plan


def pending_calls(plan: dict, scene: dict, model: str) -> int:
    from master_scenes import estimate
    return len(estimate(plan, [scene], model))


def generate_scene_with_retry(
    plan: dict, scene: dict, *, model: str, budget: list[int], attempts: int,
    runner=run_command,
) -> bool:
    """Continue after failure; a failed scene never counts as approved.

    Conservatively debit at least one request on each failed attempt, even
    if no new cache entry appeared. Real provider billing is not observable.
    """
    for attempt in range(1, attempts + 1):
        missing = pending_calls(plan, scene, model)
        if missing > budget[0]:
            print(f"[COTA] Cena {scene['id']} precisa {missing} chamadas; "
                  f"restam {budget[0]}. Nao enviando.", flush=True)
            return False
        args = [
            sys.executable, str(ROOT / "scripts" / "master_scenes.py"),
            "--id", plan["id"], "--cena", str(int(scene["id"])),
            "--modelo", model, "--max-chamadas", str(missing),
        ]
        ok = runner(args, label=f"Cena IA {scene['id']} — tentativa {attempt}/{attempts}")
        new_missing = pending_calls(plan, scene, model)
        made = max(0, missing - new_missing)
        budget[0] -= min(budget[0], (max(1, made) if not ok else made))
        if ok:
            return True
        if attempt < attempts:
            print(f"[RETOMADA] Cena {scene['id']} falhou; usando respostas em cache "
                  "e tentando apenas o que falta.", flush=True)
    return False


def generate_scenes(episode_id: str, *, model: str, budget: int,
                    attempts: int, max_hold: float) -> dict:
    from renderizar_master_remotion import validate_scenes
    plan = get_storyboard(episode_id, max_hold=max_hold)
    scenes = plan["scenes"]
    outstanding = sum(pending_calls(plan, scene, model) for scene in scenes)
    print(f"[PLANO] {len(scenes)} cenas; ate {outstanding} chamadas de imagem ainda "
          f"necessarias; teto configurado: {budget}.", flush=True)
    if outstanding > budget:
        raise PipelineError(
            f"Cenas requerem {outstanding} chamadas mas -MaxChamadas={budget}. "
            "Nenhuma geracao iniciada. Aumente o orcamento ou reutilize cache."
        )
    remaining = [budget]
    failed = []
    for scene in scenes:
        if not generate_scene_with_retry(
                plan, scene, model=model, budget=remaining, attempts=attempts):
            failed.append(scene["id"])
    if failed:
        raise PipelineError(
            "A geracao foi retomada quando possivel, mas estas cenas continuam "
            "sem resultado aprovado: " + ", ".join(failed) +
            ". Nao publicar video parcial. Execute o mesmo comando para retomar."
        )
    try:
        valid = validate_scenes(plan, model)
    except (ValueError, RuntimeError, FileNotFoundError, KeyError) as exc:
        raise PipelineError(
            "Imagens foram geradas, mas o QA/revisao visual nao aprovou todas "
            "as cenas. Confira as revisoes e repita o comando. " + str(exc)
        ) from exc
    if len(valid) != len(scenes):
        raise PipelineError("QA visual retornou menos cenas que o storyboard.")
    print(f"[QA VISUAL] {len(valid)} cenas validas. Orcamento nao utilizado: "
          f"{remaining[0]}.", flush=True)
    return plan


def paths(episode_id: str, profile: str) -> tuple[Path, Path]:
    folder = OUTPUT / episode_id
    return (folder / f"{episode_id}-master-multicenas-personagens-v3-{profile}.mp4",
            folder / f"{episode_id}-master-capa.jpg")


def ensure_voice(episode_id: str, *, model: str, attempts: int) -> None:
    base = [
        sys.executable, str(ROOT / "scripts" / "renderizar_master_remotion.py"),
        "--id", episode_id, "--modelo", model, "--somente-voz", "--criar-voz",
    ]
    for attempt in range(1, attempts + 1):
        if run_command(base, label=f"Voz e legendas — tentativa {attempt}/{attempts}"):
            return
        if attempt < attempts:
            print("[RETOMADA] Tentando novamente a voz sem perder o cache.", flush=True)
    raise PipelineError(
        "Voz ou sincronizacao indisponivel. Sem voz valida, nenhum MP4 sera publicado."
    )


def ensure_render(
    episode_id: str, *, model: str, profile: str, refazer: bool,
    attempts: int,
) -> tuple[Path, Path]:
    video, cover = paths(episode_id, profile)
    if video.is_file() and not refazer:
        seconds = validate_video(video, stage=f"MP4 em cache {episode_id}")
        print(f"[CACHE MP4] Reutilizando video valido ({seconds:.2f}s): {video}",
              flush=True)
    else:
        args = [
            sys.executable, str(ROOT / "scripts" / "renderizar_master_remotion.py"),
            "--id", episode_id, "--modelo", model, "--renderizar",
            "--perfil-personagens", profile,
        ]
        for attempt in range(1, attempts + 1):
            if run_command(args, label=f"Render Remotion — tentativa {attempt}/{attempts}"):
                break
        else:
            raise PipelineError("Renderizacao falhou. Nenhum video sera enviado.")
        validate_video(video, stage=f"MP4 final {episode_id}")
    # Always regenerate the episode-specific cover from approved AI scene layers.
    require_success([
        sys.executable, str(ROOT / "scripts" / "renderizar_master_remotion.py"),
        "--id", episode_id, "--modelo", model, "--somente-capa",
    ], label=f"Capa correta do episodio {episode_id}")
    if not cover.is_file() or cover.stat().st_size < 10000:
        raise PipelineError("Capa vertical ausente ou incompleta: " + str(cover))
    from PIL import Image
    with Image.open(cover) as image:
        image.load()
        width, height = image.size
        if image.format != "JPEG" or height < 640 or abs(width / height - 9 / 16) > .02:
            raise PipelineError("A capa nao e um JPEG vertical 9:16 valido")
    return video, cover


def metadata_for(episode_id: str) -> Path:
    from metadata_shorts import publisher_episode
    ep = select_episode(episode_id)
    data = publisher_episode(ep)
    if not data["descricao_youtube"].strip() or not data["capa_texto"].strip():
        raise PipelineError("Metadados sem descricao ou chamada da capa")
    target = PUBLICATION / "episodios" / (episode_id + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"[METADADOS] Titulo, descricao e texto da capa: {target}", flush=True)
    return target


@contextmanager
def exclusive_upload():
    PUBLICATION.mkdir(parents=True, exist_ok=True)
    lock = PUBLICATION / ".fluxo-unico-upload.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PipelineError(
            "Outro publicador pode estar usando a pasta compartilhada. "
            "Nao execute dois uploads simultaneamente. Verifique processos "
            f"e remova um lock obsoleto manualmente se necessario: {lock}"
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid()}) + "\n")
        yield
    finally:
        lock.unlink(missing_ok=True)


def publish(episode_id: str, *, video: Path, cover: Path, metadata: Path,
            privacy: str, schedule: str = "") -> None:
    if not OAUTH.is_file():
        raise PipelineError("OAuth YouTube ausente. Configure " + str(OAUTH))
    validate_video(video, stage="Antes do envio ao YouTube")
    with exclusive_upload():
        args = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(ROOT / "publicar-youtube.ps1"),
            "-Etapa", "tudo",
            "-Privacidade", privacy,
            "-Video", str(video),
            "-Episodio", str(metadata),
            "-ImagemFonte", str(cover),
            "-CapaFinalShorts", str(cover),
            "-Refazer",
        ]
        if schedule:
            args.extend(["-AgendarEm", schedule])
        # Do not retry a remote upload automatically; the HTTP response can be
        # lost even when YouTube has accepted the media.
        require_success(args, label=f"Upload YouTube {episode_id} ({privacy})")
        digest = hashlib.sha256()
        with video.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        record = PUBLICATION / f"estado-upload-{digest.hexdigest()[:12]}.json"
        if not record.is_file():
            raise PipelineError(
                "Publicador concluiu sem registro de upload. Confira YouTube Studio."
            )
        state = json.loads(record.read_text(encoding="utf-8-sig"))
        if not state.get("video_id"):
            raise PipelineError("Nao foi possivel confirmar ID do video. Verifique Studio.")
        if schedule:
            from publicar_arquivo_otaku import parse_publish_at
            recorded = state.get("agendado_para", "")
            if (not state.get("agendamento_confirmado") or
                    not recorded or parse_publish_at(recorded) != parse_publish_at(schedule)):
                raise PipelineError(
                    "MP4 enviado mas agendamento nao confirmado. "
                    "Confira no Studio e nao reenvie."
                )
            print(f"[AGENDADO] {state['agendado_para']}", flush=True)
        print(f"[YOUTUBE] https://youtu.be/{state['video_id']}", flush=True)
        if state.get("thumbnail_status") != "success":
            print(
                "[CAPA PENDENTE NO YOUTUBE] O JPEG correto foi enviado/guardado, "
                "mas a API nao confirmou a miniatura. Ajuste no app YouTube "
                "se o recurso estiver disponivel. Nao reenvie o MP4.",
                flush=True,
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Um comando para produzir Short com voz, imagens IA, QA, capa e publicar"
    )
    parser.add_argument("--id", default="101-death-note-ep01")
    parser.add_argument("--modelo", choices=MODELS, default="gpt-image-1.5")
    parser.add_argument("--perfil", choices=PROFILES, default="equilibrado")
    parser.add_argument("--max-chamadas", type=int, default=45)
    parser.add_argument("--tentativas", type=int, default=2)
    parser.add_argument("--max-segundos-por-plano", type=float, default=6)
    parser.add_argument("--privacidade", choices=("private", "unlisted", "public"),
                        default="private")
    parser.add_argument("--publicar", action="store_true")
    parser.add_argument("--agendar-em", default="",
                        help="Data/hora ISO8601 com fuso para agendamento nativo do YouTube")
    parser.add_argument("--refazer", action="store_true")
    parser.add_argument("--somente-validar", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.max_chamadas <= 180:
        parser.error("--max-chamadas precisa estar entre 0 e 180")
    if not 1 <= args.tentativas <= 3:
        parser.error("--tentativas precisa estar entre 1 e 3")
    if not 2.5 <= args.max_segundos_por_plano <= 12:
        parser.error("--max-segundos-por-plano precisa estar entre 2.5 e 12")
    if args.agendar_em:
        from publicar_arquivo_otaku import parse_publish_at, schedule_status
        schedule_status(args.privacidade, parse_publish_at(args.agendar_em))
        if not args.publicar:
            raise PipelineError("Agendamento exige --publicar explicitamente.")
    episode = select_episode(args.id)
    if not episode.get("cover") or not episode.get("script"):
        raise PipelineError("Episodio sem roteiro/capa no catalogo.")
    if args.publicar and not OAUTH.is_file():
        raise PipelineError("Configure OAuth antes de gerar imagens: " + str(OAUTH))
    if args.somente_validar:
        video, cover = paths(args.id, args.perfil)
        validate_video(video, stage="Preflight")
        if not cover.is_file():
            raise PipelineError("Capa ainda nao gerada: " + str(cover))
        metadata_for(args.id)
        print("[PREVIEW] Video/capa prontos. Nenhum pedido de IA ou upload.")
        return 0
    print(f"[INICIO] {episode['title']} | publicar={args.publicar} | "
          f"privacidade={args.privacidade} | max chamadas IA={args.max_chamadas}",
          flush=True)
    ensure_voice(args.id, model=args.modelo, attempts=args.tentativas)
    generate_scenes(args.id, model=args.modelo, budget=args.max_chamadas,
                    attempts=args.tentativas, max_hold=args.max_segundos_por_plano)
    video, cover = ensure_render(args.id, model=args.modelo,
                                 profile=args.perfil, refazer=args.refazer,
                                 attempts=args.tentativas)
    metadata = metadata_for(args.id)
    print(f"[PRONTO] {video}\n[CAPA] {cover}", flush=True)
    if args.publicar:
        publish(args.id, video=video, cover=cover,
                metadata=metadata, privacy=args.privacidade,
                schedule=args.agendar_em)
    else:
        print("[SEM UPLOAD] Gere primeiro e reveja o resultado; para "
              "publicar, use -Publicar no comando PowerShell.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PipelineError, ValueError, RuntimeError, OSError,
            subprocess.SubprocessError) as exc:
        print("[BLOQUEADO] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
