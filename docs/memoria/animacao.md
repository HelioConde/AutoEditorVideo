# Fofinhos e movimento

Referência inicial na revisão `48533df1`. O EP01 tem contrato de narração integral de 15 cenas em `conteudos/fofinhos-ep01-parte01-narracao-aprovada-v1.json`. O ovo aparece entre flores; o ponto manual das flores fica vinculado ao cenário revisado. A voz do rascunho curto foi rejeitada. A [continuidade da narração](../FOFINHOS-EP01-CONTINUIDADE-NARRACAO.md) explica a correção e seus tempos.

- **Cânone e sincronismo.** `scripts/fofinhos_ep01_canon.py` e `tests/test_fofinhos_ep01_canon.py` verificam a sequência original, pausas, posição do ovo e bloqueio da voz antiga.
- **Render e ambiente.** `scripts/fofinhos_ep01_render.py` e `tests/test_fofinhos_ep01_render.py` cobrem invalidação da revisão quando muda o jardim e efeitos ambientais da prévia canônica. A [direção de ambiente](../FOFINHOS-EP01-AMBIENTE-VIVO.md) documenta sua aplicação.
- **Reutilização.** Consultar o [catálogo de poses](../CATALOGO-POSES-EMANUELLY-V2.md) e o [cânone de referências](../politicas/fofinhos-referencias.md). A avaliação de uma malha no preview Otaku em `tests/test_otaku_v7_mesh_preview.py` pertence àquele preview. Para aplicá-la a Fofinhos, validar a identidade, os pontos de deformação e o movimento no material apropriado.
- **Validação local.** `python -m pytest -q tests/test_fofinhos_ep01_canon.py tests/test_fofinhos_ep01_render.py`. Indicadores possíveis de QA técnico incluem divergências de pausa, coordenada ou hash. A aprovação artística depende dos quadros e do movimento vistos pelo responsável.

Para uma alteração futura no EP01, verificar primeiro a versão do cenário e a aprovação de suas coordenadas. Registrar aqui a composição, o teste e a revisão visual efetivamente realizados.
