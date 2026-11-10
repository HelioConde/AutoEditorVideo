# Scripts Python e PowerShell

- Localize o entry point usado pelo launcher, sua implementação e os testes que exercitam esse caminho. Nos `.ps1` da raiz, leia também as [regras dos launchers](../docs/politicas/lancadores-e-pilotos.md) quando a tarefa envolver Gamer, Kids ou EN.
- Para scripts de vídeo, aplique as políticas de operação e de canal do [índice do projeto](../AGENTS.md). Preserve modos de simulação, identificadores, argumentos e códigos de saída utilizados pelos jobs.
- Simule integrações externas nos testes. O teste dos launchers Windows usa motores fake em `tests/test_channel_launchers.ps1`. Verifique o teste do módulo e execute `python -m pytest -q tests` para mudanças funcionais.
