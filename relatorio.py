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
    """Quantos pacotes ha em cada dia de despacho."""
    linhas_dia = core.resumo_por_dia(prontos)
    if not linhas_dia:
        return "Nenhum envio pronto para imprimir."
    saida = [f"Resumo por dia de despacho (hoje = {hoje})\n"]
    for data, qtd in linhas_dia:
        marca = "  <= HOJE" if data == hoje else ("  <= amanha" if data == amanha else "")
        saida.append(f"  {data}   {qtd:>3} pacote(s){marca}")
    saida.append(f"\nTotal: {len(prontos)} pacote(s) em {len(linhas_dia)} dia(s).")
    return "\n".join(saida)
