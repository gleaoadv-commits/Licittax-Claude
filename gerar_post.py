#!/usr/bin/env python3
"""Gera posts de Instagram da Licittax (imagem JPEG 1080x1350 + legenda).

Uso:
  python3 gerar_post.py licitacao [--saida DIR]
      Busca no PNCP uma licitação aberta (Brasil todo, qualquer valor),
      priorizando as áreas da Licittax, e gera arte + legenda.
  python3 gerar_post.py dica ARQUIVO.json [--saida DIR]
      Gera a arte de um post educativo a partir de um JSON:
      {"tema": "...", "titulo": "...", "itens": ["...", "..."], "legenda": "..."}

Saída: DIR/<id>.jpg, DIR/<id>.txt (legenda) e DIR/<id>.json (metadados).
O histórico do que já foi postado fica em historico.json, ao lado do script.
"""
import argparse
import datetime as dt
import json
import random
import re
import sys
import textwrap
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
FONTES = BASE / "fonts"
HISTORICO = BASE / "historico.json"

# Paleta Licittax
NAVY = (4, 24, 49)
NAVY2 = (20, 36, 69)
TEAL = (8, 72, 101)
VERDE = (31, 138, 122)
BRANCO = (255, 255, 255)
CINZA = (176, 192, 212)

W, H = 1080, 1350
MARGEM = 80

PNCP = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
MODALIDADES = {6: "Pregão Eletrônico", 4: "Concorrência Eletrônica"}

AREAS = {
    "Obras e Engenharia": [
        "obra", "engenharia", "constru", "reforma", "paviment", "asfalt", "drenagem",
        "edifica", "ponte", "saneamento", "recapeamento", "terraplenagem", "ampliacao",
    ],
    "Saúde": [
        "medicament", "hospital", "saude", "medic", "odontolog", "farmac", "laborator",
        "insumo", "cirurg", "enfermagem", "ambulancia", "vacina", "exame",
    ],
    "TI e Tecnologia": [
        "software", "informatica", "computador", "notebook", "tecnologia da informacao",
        "sistema de gestao", "licenca", "rede de dados", "servidor", "impressora",
        "internet", "nuvem", "desenvolvimento de sistema", "telefonia",
    ],
    "Serviços Gerais": [
        "limpeza", "vigilancia", "seguranca", "alimenta", "refeic", "transporte",
        "locacao", "manutencao", "conservacao", "copeiragem", "portaria", "combustive",
        "veiculo", "coleta", "lavanderia", "jardinagem",
    ],
}


# ---------------------------------------------------------------- utilidades
def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def fonte(peso: int, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTES / f"Poppins-{peso}.woff"), tam)


def brl(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def titulo_proprio(s: str) -> str:
    minusc = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "na", "no"}
    palavras = s.lower().split()
    return " ".join(p if (i and p in minusc) else p.capitalize() for i, p in enumerate(palavras))


def carregar_historico() -> dict:
    if HISTORICO.exists():
        return json.loads(HISTORICO.read_text(encoding="utf-8"))
    return {"licitacoes": [], "dicas": []}


def salvar_historico(h: dict) -> None:
    HISTORICO.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def quebrar(draw, texto, fnt, largura):
    """Quebra texto em linhas que cabem na largura (px)."""
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fnt) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def caber(draw, texto, peso, tam_max, tam_min, largura, max_linhas):
    """Escolhe o maior tamanho de fonte em que o texto cabe em max_linhas."""
    for tam in range(tam_max, tam_min - 1, -2):
        f = fonte(peso, tam)
        linhas = quebrar(draw, texto, f, largura)
        if len(linhas) <= max_linhas:
            return f, linhas
    f = fonte(peso, tam_min)
    linhas = quebrar(draw, texto, f, largura)[:max_linhas]
    while linhas and draw.textlength(linhas[-1] + "…", font=f) > largura:
        linhas[-1] = linhas[-1].rsplit(" ", 1)[0]
    linhas[-1] += "…"
    return f, linhas


def fundo() -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for y in range(H):  # gradiente vertical navy -> navy2
        t = y / H
        cor = tuple(int(NAVY[i] + (NAVY2[i] - NAVY[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=cor)
    # detalhe geométrico
    d.ellipse([W - 230, -330, W + 230, 130], fill=TEAL)
    d.ellipse([W - 150, -250, W + 150, 50], fill=NAVY2)
    d.rectangle([0, H - 14, W, H], fill=VERDE)
    return img


def pilula(d, x, y, texto, cor_fundo, cor_texto=BRANCO, tam=26):
    f = fonte(600, tam)
    larg = d.textlength(texto, font=f)
    d.rounded_rectangle([x, y, x + larg + 44, y + tam + 26], radius=(tam + 26) // 2, fill=cor_fundo)
    d.text((x + 22, y + 10), texto, font=f, fill=cor_texto)
    return x + larg + 44


def rodape(d):
    d.line([(MARGEM, H - 150), (W - MARGEM, H - 150)], fill=TEAL, width=2)
    d.text((MARGEM, H - 122), "@licittax", font=fonte(700, 34), fill=BRANCO)
    d.text((MARGEM, H - 78), "Assessoria & Consultoria em Licitações", font=fonte(400, 24), fill=CINZA)


# ---------------------------------------------------------------- licitação
def buscar_pncp(modalidade: int, data_final: str, pagina: int) -> list:
    q = urllib.parse.urlencode({
        "dataFinal": data_final,
        "codigoModalidadeContratacao": modalidade,
        "pagina": pagina,
        "tamanhoPagina": 50,
    })
    req = urllib.request.Request(f"{PNCP}?{q}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status == 204:
            return []
        corpo = r.read()
    return json.loads(corpo).get("data", []) if corpo else []


def classificar(objeto: str):
    o = sem_acento(objeto)
    for area, chaves in AREAS.items():
        if any(c in o for c in chaves):
            return area
    return None


def escolher_licitacao(hist: dict) -> dict:
    hoje = dt.date.today()
    # propostas abertas encerrando entre 5 e 40 dias: tempo útil para participar
    data_final = (hoje + dt.timedelta(days=40)).strftime("%Y%m%d")
    ja = set(hist["licitacoes"])
    candidatos = []
    for mod in MODALIDADES:
        for pagina in random.sample(range(1, 21), 4):
            try:
                itens = buscar_pncp(mod, data_final, pagina)
            except Exception as e:  # página fora do intervalo ou erro transitório
                print(f"aviso: PNCP mod {mod} pág {pagina}: {e}", file=sys.stderr)
                continue
            for it in itens:
                if it.get("numeroControlePNCP") in ja:
                    continue
                valor = it.get("valorTotalEstimado") or 0
                enc = it.get("dataEncerramentoProposta")
                if not enc or valor <= 0:
                    continue
                enc_d = dt.datetime.fromisoformat(enc).date()
                if not (hoje + dt.timedelta(days=5) <= enc_d <= hoje + dt.timedelta(days=40)):
                    continue
                area = classificar(it.get("objetoCompra") or "")
                if not area:
                    continue
                it["_area"] = area
                candidatos.append(it)
    if not candidatos:
        raise SystemExit("Nenhuma licitação candidata encontrada no PNCP agora.")
    # alterna áreas: evita repetir a área do último post de licitação
    ultima = hist.get("ultima_area")
    variados = [c for c in candidatos if c["_area"] != ultima] or candidatos
    # dá preferência a processos de maior valor, com sorteio para variar
    variados.sort(key=lambda c: c["valorTotalEstimado"], reverse=True)
    return random.choice(variados[: max(5, len(variados) // 4)])


SIGLAS = {"ti", "epi", "epis", "sus", "ubs", "upa", "cras", "creas", "pncp", "ldo", "srp", "gps", "led", "cnh"}


def limpar_objeto(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip().rstrip(".;,")
    letras = [c for c in s if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) > 0.7:  # texto todo em CAIXA ALTA
        s = " ".join(p.upper() if sem_acento(p.strip("(),.;:")) in SIGLAS else p.lower() for p in s.split())
    return s[0].upper() + s[1:] if s else s


def arte_licitacao(it: dict, destino: Path) -> None:
    img = fundo()
    d = ImageDraw.Draw(img)
    larg = W - 2 * MARGEM
    y = 90
    x = pilula(d, MARGEM, y, "LICITAÇÃO ABERTA", VERDE)
    pilula(d, x + 14, y, it["_area"].upper(), TEAL)
    y += 110

    f_obj, linhas = caber(d, limpar_objeto(it["objetoCompra"]), 700, 54, 36, larg, 6)
    for ln in linhas:
        d.text((MARGEM, y), ln, font=f_obj, fill=BRANCO)
        y += int(f_obj.size * 1.28)
    y += 40

    org = titulo_proprio(it["orgaoEntidade"]["razaoSocial"])
    u = it["unidadeOrgao"]
    enc = dt.datetime.fromisoformat(it["dataEncerramentoProposta"])
    campos = [
        ("Valor estimado", brl(it["valorTotalEstimado"])),
        ("Órgão", org),
        ("Local", f"{u['municipioNome']} / {u['ufSigla']}"),
        ("Modalidade", it.get("modalidadeNome") or MODALIDADES.get(it["modalidadeId"], "")),
        ("Propostas até", enc.strftime("%d/%m/%Y às %Hh%M")),
    ]
    f_rot, f_val = fonte(600, 24), fonte(600, 34)
    for rot, val in campos:
        if y > H - 290:
            break
        d.rectangle([MARGEM, y + 6, MARGEM + 6, y + 76], fill=VERDE)
        d.text((MARGEM + 28, y), rot.upper(), font=f_rot, fill=CINZA)
        val_ln = quebrar(d, val, f_val, larg - 28)
        if len(val_ln) > 1:
            val_ln = [val_ln[0].rstrip(",") + "…"]
        d.text((MARGEM + 28, y + 30), val_ln[0], font=f_val, fill=BRANCO)
        y += 108
    d.text((MARGEM, H - 205), "Fonte: Portal Nacional de Contratações Públicas (PNCP)", font=fonte(400, 22), fill=CINZA)
    rodape(d)
    img.save(destino, "JPEG", quality=92)


def legenda_licitacao(it: dict) -> str:
    u = it["unidadeOrgao"]
    enc = dt.datetime.fromisoformat(it["dataEncerramentoProposta"])
    cnpj, ano, seq = it["orgaoEntidade"]["cnpj"], it["anoCompra"], it["sequencialCompra"]
    hashtag_area = {
        "Obras e Engenharia": "#obraspublicas #engenharia",
        "Saúde": "#saude #licitacaosaude",
        "TI e Tecnologia": "#tecnologia #ti",
        "Serviços Gerais": "#servicos #terceirizacao",
    }[it["_area"]]
    return textwrap.dedent(f"""\
        📢 LICITAÇÃO ABERTA — {it['_area']}

        📝 Objeto: {limpar_objeto(it['objetoCompra'])}

        🏛️ Órgão: {titulo_proprio(it['orgaoEntidade']['razaoSocial'])}
        📍 Local: {u['municipioNome']}/{u['ufSigla']}
        💰 Valor estimado: {brl(it['valorTotalEstimado'])}
        ⚖️ Modalidade: {it.get('modalidadeNome', '')}
        ⏰ Propostas até: {enc.strftime('%d/%m/%Y às %Hh%M')}
        🔎 Nº de controle PNCP: {it['numeroControlePNCP']}

        Edital completo no PNCP: pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}

        Sua empresa quer disputar este ou outros processos? A Licittax cuida da análise do edital, documentação e acompanhamento do pregão. Chama no direct! 📩

        #licitacao #licitacoes #pregao #pregaoeletronico #pncp #lei14133 #governo #comprapublica {hashtag_area} #licittax""")


def cmd_licitacao(saida: Path) -> None:
    hist = carregar_historico()
    it = escolher_licitacao(hist)
    pid = "lic-" + re.sub(r"[^0-9A-Za-z]+", "-", it["numeroControlePNCP"]).strip("-")
    arte_licitacao(it, saida / f"{pid}.jpg")
    (saida / f"{pid}.txt").write_text(legenda_licitacao(it), encoding="utf-8")
    (saida / f"{pid}.json").write_text(json.dumps(it, ensure_ascii=False, indent=2), encoding="utf-8")
    hist["licitacoes"].append(it["numeroControlePNCP"])
    hist["ultima_area"] = it["_area"]
    salvar_historico(hist)
    print(json.dumps({"id": pid, "imagem": str(saida / f"{pid}.jpg"), "legenda": str(saida / f"{pid}.txt")}, ensure_ascii=False))


# ---------------------------------------------------------------- dica
def arte_dica(dados: dict, destino: Path) -> None:
    img = fundo()
    d = ImageDraw.Draw(img)
    larg = W - 2 * MARGEM
    y = 90
    pilula(d, MARGEM, y, dados.get("selo", "VOCÊ SABIA?").upper(), VERDE)
    y += 120
    f_tit, linhas = caber(d, dados["titulo"], 800, 66, 44, larg, 4)
    for ln in linhas:
        d.text((MARGEM, y), ln, font=f_tit, fill=BRANCO)
        y += int(f_tit.size * 1.22)
    y += 50
    itens = dados.get("itens", [])[:5]
    disponivel = H - 230 - y
    for tam in range(34, 23, -2):
        f_it = fonte(400, tam)
        blocos = [quebrar(d, t, f_it, larg - 70) for t in itens]
        altura = sum(len(b) * int(tam * 1.4) + 34 for b in blocos)
        if altura <= disponivel:
            break
    for i, bloco in enumerate(blocos, 1):
        d.ellipse([MARGEM, y + 4, MARGEM + 46, y + 50], fill=TEAL)
        num = str(i)
        f_n = fonte(700, 26)
        d.text((MARGEM + 23 - d.textlength(num, font=f_n) / 2, y + 9), num, font=f_n, fill=BRANCO)
        for ln in bloco:
            d.text((MARGEM + 70, y), ln, font=f_it, fill=BRANCO)
            y += int(f_it.size * 1.4)
        y += 34
    if dados.get("fonte"):
        d.text((MARGEM, H - 205), f"Base legal: {dados['fonte']}", font=fonte(400, 22), fill=CINZA)
    rodape(d)
    img.save(destino, "JPEG", quality=92)


def cmd_dica(arquivo: Path, saida: Path) -> None:
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    hist = carregar_historico()
    pid = "dica-" + dt.datetime.now().strftime("%Y%m%d-%H%M")
    arte_dica(dados, saida / f"{pid}.jpg")
    (saida / f"{pid}.txt").write_text(dados["legenda"], encoding="utf-8")
    hist["dicas"].append({"data": dt.date.today().isoformat(), "tema": dados.get("tema", dados["titulo"])})
    salvar_historico(hist)
    print(json.dumps({"id": pid, "imagem": str(saida / f"{pid}.jpg"), "legenda": str(saida / f"{pid}.txt")}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("licitacao")
    a.add_argument("--saida", type=Path, default=BASE / "posts")
    b = sub.add_parser("dica")
    b.add_argument("arquivo", type=Path)
    b.add_argument("--saida", type=Path, default=BASE / "posts")
    args = ap.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    if args.cmd == "licitacao":
        cmd_licitacao(args.saida)
    else:
        cmd_dica(args.arquivo, args.saida)


if __name__ == "__main__":
    main()
