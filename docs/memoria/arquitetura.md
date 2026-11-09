# Arquitetura e testes

Referência inicial na revisão `48533df1`. Os caminhos e testes permitem revalidar cada entrada.

| Operação | Entrada ou dependência | Verificação existente |
| --- | --- | --- |
| Preparar produção | Launchers PowerShell na raiz chamam módulos em `scripts/`. O par canal + episódio está em `conteudos/otaku-production-reservations.json`. | `scripts/production_reservations.py`; `tests/test_channel_launchers.ps1` usa motores fake para os launchers dedicados. |
| Identidade de canais | `config/youtube-channel-registry.json` e `scripts/youtube_channel_registry.py` | Para consentimento dos novos canais, `tests/test_youtube_new_channels_oauth.py`. Conferir o OAuth real só no fluxo autorizado. |
| Compor e medir | Composições em `motion-remotion/src/`, dependências Node em `motion-remotion/package.json`, FFmpeg e ffprobe para mídia. | `npm run typecheck` em `motion-remotion/`; `python -m pytest -q tests/test_shorts_duration.py` para o contrato de duração dos Shorts. |
| QA Reframe EN | `scripts/qa_automatico_reframe_en.py` | `python -m pytest -q tests/test_qa_automatico_reframe_en.py`. |
| Identidade de anime | `config/otaku-character-identity-policy.json` | `python -m pytest -q tests/test_otaku_character_v2_20261108.py`. A similaridade artística exige inspeção real. |

Os arquivos `requirements-master.txt`, `requirements-publicacao.txt` e `motion-remotion/package.json` descrevem dependências por área. Use os requisitos do módulo que o teste exercita. A suíte obrigatória para mudanças funcionais está no AGENTS.md.
