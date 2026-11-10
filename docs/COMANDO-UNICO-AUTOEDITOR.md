# AutoEditorVideo — comando PowerShell único

A entrada pública proposta é `autoeditor.ps1`. Os scripts antigos ainda existem como **motores internos**, pois removê-los imediatamente quebraria chamadas entre arquivos, workflows e comandos existentes.

## Exemplos

```powershell
.\autoeditor.ps1
.\autoeditor.ps1 -Canal diagnostico
.\autoeditor.ps1 -Canal br -Acao validar -Id 101-death-note-ep01
.\autoeditor.ps1 -Canal br -Acao produzir -Id 101-death-note-ep01
.\autoeditor.ps1 -Canal en -Acao resumo
.\autoeditor.ps1 -Canal en -Acao renderizar -Id 202-death-note-40-segundos
.\autoeditor.ps1 -Canal gamer -Acao validar
.\autoeditor.ps1 -Canal fofinhos -Acao planejar
.\autoeditor.ps1 -Canal kids -Acao planejar -Id 1
.\autoeditor.ps1 -Canal alchemy -Acao planejar
```

### Uploads exigem confirmação

```powershell
.\autoeditor.ps1 -Canal en -Acao enviar -Id 202-death-note-40-segundos -ConfirmarEnvio
```

A privacidade padrão é `private`. Para tornar público, informe também `-Privacidade public -ConfirmarPublico`. A confirmação não substitui as validações internas de OAuth, canal, thumbnail e qualidade.

O modo BR usa `criar-publicar-short.ps1`, EN usa `canal-ingles.ps1`, Gamer usa `canal-gamer.ps1`, Kids usa `gerar-historia-kids.ps1` e Fofinhos usa `fofinhos-ep01.ps1`. O modo Alchemy nesta versão somente mostra o índice editorial; geração/publicação ainda não foram unificadas.

## Limitações desta fase

- É uma **interface unificada**, não um único motor autossuficiente.
- Scripts legados ainda são necessários, inclusive `gerar-shorts-en.ps1`.
- Não altera workflows do GitHub Actions nem agenda vídeos.
- Ainda falta executar testes PowerShell no Windows e verificar compatibilidade das rotas.
- Não mesclar antes de validar dependências e comportamento de publicação.
