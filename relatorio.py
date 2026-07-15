"""
relatorio.py
Monta textos legiveis (para o bot do Telegram) a partir dos dados do nucleo.
Funcoes puras, sem dependencia do Telegram nem de rede -> faceis de testar.
"""

from __future__ import annotations

from collections import defaultdict

import separador_etiquetas_ml as core


def texto_grupos(grupos: list, titulo: str) -> str:
    """Lista os grupos (SKU + quantidade) agrupados por quantidade do pedido."""
    if not grupos:
        return f"{titulo}: nenhum grupo para imprimir. 🎉"

    total_et = sum(g.total_etiquetas for g in grupos)
    linhas = [f"{titulo} — {len(grupos)} grupo(s), {total_et} etiqueta(s)"]

    por_qtd: dict[int, list] = defaultdict(list)
    for g in grupos:
        por_qtd[g.quantidade].append(g)

    for qtd in sorted(por_qtd):
        linhas.append(f"\nQuantidade por pedido = {qtd}:")
        for g in por_qtd[qtd]:
            linhas.append(f"  {g.total_etiquetas:>3}  {g.nome}")
    return "\n".join(linhas)


def texto_resumo(prontos: list, hoje: str, amanha: str) -> str:
    """Quantos pacotes ha em cada dia de despacho (Mercado Livre)."""
    linhas_dia = core.resumo_por_dia(prontos)
    return _formatar_resumo(linhas_dia, len(prontos), hoje, amanha,
                            loja="Mercado Livre")


def texto_resumo_contagem(contagem: dict, hoje: str, amanha: str, *, loja: str) -> str:
    """Mesmo resumo, a partir de uma contagem {dia: n} ja pronta (Shopee:
    contagem_por_dia vem da MESMA busca, sem rede extra). Dia "" = sem data."""
    linhas_dia = sorted(((d or "(sem data)"), n) for d, n in contagem.items())
    return _formatar_resumo(linhas_dia, sum(contagem.values()), hoje, amanha,
                            loja=loja)


def _formatar_resumo(linhas_dia, total: int, hoje: str, amanha: str, *, loja: str) -> str:
    """Layout unico do resumo por dia, com a LOJA no titulo (o resumo respeita a
    loja ativa do chat — sem o rotulo, um resumo Shopee pareceria do ML)."""
    if not linhas_dia:
        return f"Nenhum envio pronto para imprimir ({loja})."
    saida = [f"Resumo por dia de despacho — {loja} (hoje = {hoje})\n"]
    for data, qtd in linhas_dia:
        marca = "  <= HOJE" if data == hoje else ("  <= amanha" if data == amanha else "")
        saida.append(f"  {data}   {qtd:>3} pacote(s){marca}")
    saida.append(f"\nTotal: {total} pacote(s) em {len(linhas_dia)} dia(s).")
    return "\n".join(saida)


def texto_bom_dia(prontos: list, hoje: str, amanha: str) -> str:
    """Mensagem do aviso automatico da manha: manchete com a contagem de hoje
    seguida do resumo por dia."""
    de_hoje = sum(1 for p in prontos if (p.get("_envio") or {}).get("expected_date") == hoje)
    cabecalho = f"Bom dia! Hoje voce tem {de_hoje} pacote(s) para despachar."
    return f"{cabecalho}\n\n{texto_resumo(prontos, hoje, amanha)}"


def texto_detalhe(itens: list, chave: str) -> str:
    """Composicao de um SKU: quais produtos/variacoes/voltagens o formam e
    quantos envios de cada. Casa a chave sem diferenciar maiusculas/minusculas."""
    alvo = chave.strip().lower()
    comp: dict[tuple, set] = defaultdict(set)
    for it in itens:
        if it.chave.lower() == alvo and it.shipment_id:
            comp[(it.item_id, (it.titulo or "")[:50], it.voltagem)].add(it.shipment_id)
    if not comp:
        return f"Nada encontrado para o SKU '{chave}' hoje."
    linhas = [f"Composicao de {chave} (hoje):"]
    for (iid, tit, volt), ships in sorted(comp.items(), key=lambda x: -len(x[1])):
        v = f" [{volt}]" if volt else ""
        linhas.append(f"  {len(ships):>3}  {iid}  {tit}{v}".rstrip())
    return "\n".join(linhas)


def dividir_mensagem(texto: str, limite: int = 4000) -> list[str]:
    """Divide um texto em blocos <= limite (o Telegram corta em ~4096), quebrando
    preferencialmente em linhas. Linhas isoladas maiores que o limite sao
    fatiadas no tamanho maximo."""
    blocos: list[str] = []
    atual = ""
    for linha in texto.split("\n"):
        while len(linha) > limite:               # linha gigante: fatia na marra
            if atual:
                blocos.append(atual)
                atual = ""
            blocos.append(linha[:limite])
            linha = linha[limite:]
        if not atual:
            atual = linha
        elif len(atual) + 1 + len(linha) <= limite:
            atual = f"{atual}\n{linha}"
        else:
            blocos.append(atual)
            atual = linha
    if atual:
        blocos.append(atual)
    return blocos or [""]
