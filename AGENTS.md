# Arquivo Otaku — orientações para agentes

Projeto local de produção de Shorts em PT-BR: radar editorial, roteiro revisado,
imagens anime via Codex Proxy local, edição com MoneyPrinterTurbo/FFmpeg,
miniaturas e upload OAuth para YouTube.

Regras obrigatórias:
- Nunca enviar `.env`, `.secrets`, tokens OAuth, credenciais de terceiros, vídeos,
  imagens geradas, caches nem dados de conta ao repositório.
- Toda geração de imagens deve considerar cotas e respeitar `no available accounts`.
  Não contornar cotas, não trocar conta automaticamente para burlar limites.
- `-SomenteConfigurar`, QA, radar e testes não podem gastar cota nem publicar.
- Evitar upload duplicado; publicar apenas quando o usuário solicita. Confirmar
  o modo de privacidade e registrar o ID retornado.
- Não inventar métricas, fontes de notícias nem prometer monetização.
- Interface do GitHub Pages é informativa, não executa o backend Windows.
- Usar `python -m pytest -q tests` antes de entregar mudanças funcionais.
- Para conteúdos de anime, revisar direitos de imagem, música e fontes originais.
