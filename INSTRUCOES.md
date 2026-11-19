# Rotina de publicação — Instagram @licittax

Este repositório gera e publica automaticamente posts no Instagram da Licittax
(conta `17841464593621126`, conector `instagram` do Windsor.ai).

- `gerar_post.py` — gera arte (JPEG 1080x1350) + legenda.
- `posts/` — imagens publicadas (servidas publicamente pelo GitHub, o Instagram baixa daqui).
- `historico.json` — o que já foi postado (licitações, temas de dicas, publicações).

## Passo a passo de uma execução

Tipo do post: **licitacao** ou **dica** (informado na tarefa programada).

1. Repositório: se `/home/user/licittax-claude` não existir, anexe com `add_repo`
   (owner `gleaoadv-commits`, repo `licittax-claude`, access `push`) e clone.
   Trabalhe na branch `main` e faça `git pull` antes de começar.

2. Gerar o post:
   - **licitacao**: `python3 gerar_post.py licitacao`
   - **dica**: escolha um tema sobre licitações que **não esteja** em `historico.json > dicas`
     (ex.: modalidades, fases do pregão, habilitação, ME/EPP e LC 123, SICAF, impugnação e
     recurso, garantia contratual, reequilíbrio, atestados de capacidade técnica, dispensa,
     inexigibilidade, ata de registro de preços, PNCP, sanções, prazos). Escreva um JSON com
     `tema`, `selo` (ex.: "Você sabia?", "Dica Licittax", "Atenção"), `titulo` (até ~60
     caracteres), `itens` (3 a 5 frases curtas), `fonte` (dispositivo legal exato) e
     `legenda` (texto do Instagram com emojis moderados, chamada para o direct e hashtags
     terminando em `#licittax`). Rode `python3 gerar_post.py dica arquivo.json`.
     **Só afirme o que tem certeza** sobre a Lei 14.133/2021 e normas relacionadas; cite o
     artigo. Na dúvida, escolha outro tema. Não invente números ou estatísticas.

3. Conferir a imagem gerada (abrir o JPEG) — texto legível, sem sobreposição.

4. Publicar a imagem no GitHub:
   `git add posts historico.json && git commit -m "Post <id>" && git push origin main`.
   URL pública: `https://raw.githubusercontent.com/gleaoadv-commits/licittax-claude/main/posts/<id>.jpg`

5. Publicar no Instagram: Windsor.ai `execute_action`, connector `instagram`,
   account `17841464593621126`, action `create_image_post`, params
   `{"image_url": <URL acima>, "caption": <conteúdo de posts/<id>.txt>}`.
   A publicação direta já está autorizada pelo dono da conta. Se o Instagram ainda não
   conseguir baixar a imagem (cache do GitHub), aguarde ~1 min e tente de novo (até 3x).

6. Registrar em `historico.json > publicados` `{data, tipo, id, media_id}` e dar commit/push.

7. Se algo falhar (PNCP fora do ar, erro do Instagram), não invente dados: registre o erro
   na resposta final da sessão.
