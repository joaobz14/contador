#!/usr/bin/env python3
"""Motor de recomendacao (camada 3) do monitor de Product Ads.

Le o historico ja coletado (`historico_ads.sqlite3`, tabela `campanhas_diarias`)
numa janela de dias e gera recomendacoes de acao no formato pedido: conta,
campanha, problema, evidencia, acao exata, justificativa, impacto esperado,
risco, confianca, urgencia, prazo de reavaliacao, metrica de verificacao.

So os sinais que NAO dependem de dado de margem entram aqui:
  - orcamento insuficiente (lost_impression_share_by_budget alto)
  - ranking baixo (lost_impression_share_by_ad_rank alto)
  - ROAS abaixo do objetivo definido pela propria campanha (roas_target)

Recomendacao de AUMENTAR investimento (orcamento ou ranking, que na pratica
tambem custa dinheiro via ACOS/CPC mais alto) sai sempre marcada
"Recomendacao condicionada a validacao da margem" -- SEM dado de margem por
SKU (ainda nao existe no projeto), nao da pra saber se aumentar gasto e
lucrativo. Recomendacao de REVISAR/reduzir (ROAS abaixo do alvo) nao precisa
dessa ressalva -- e uma reducao de risco, nao uma aposta de investimento.

Trava contra recomendacao em cima de dado fraco (regra do pedido original --
nunca recomendar com base em 1 dia, poucos cliques ou dado provisorio):
  - MIN_DIAS dias distintos de historico na janela (default JANELA_DIAS_PADRAO
    dias) -- campanha sem isso e listada como "monitorando", sem recomendacao.
  - MIN_CLICKS cliques somados na janela -- amostra pequena nao gera recomendacao.
  - coletar.py so grava dias FECHADOS (nunca "hoje"), entao dado provisorio
    nunca entra aqui por construcao.
Nao detecta "campanha recem-criada na ML" (precisaria de date_created, que
nao esta em campanhas_diarias) -- MIN_DIAS e um substituto aproximado (dias
que JA estao no NOSSO historico, nao a idade real da campanha).

Uso:
    python ads-monitor/recomendar.py                  # janela padrao, todas as contas
    python ads-monitor/recomendar.py --dias 14         # janela maior
    python ads-monitor/recomendar.py --conta cozilatti # so uma conta
"""
from __future__ import annotations

import argparse
import datetime
import sqlite3
from dataclasses import dataclass
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ARQUIVO_DB = PASTA / "historico_ads.sqlite3"

JANELA_DIAS_PADRAO = 7
# Minimos pra sair do "monitorando" e virar recomendacao de verdade -- numeros
# de partida, ajustaveis com mais experiencia real (nao sao um fato da API).
MIN_DIAS = 3
MIN_CLICKS = 20
# Limiares de perda (fracao 0-1, mesma escala que a API devolve) acima do
# qual o sinal vira recomendacao.
LIMIAR_ORCAMENTO = 0.15
LIMIAR_RANKING = 0.15
# Urgencia "alta" quando a perda passa deste segundo limiar (mais grave).
LIMIAR_URGENCIA_ALTA = 0.30


@dataclass
class Recomendacao:
    conta: str
    campaign_id: str
    campaign_name: str
    tipo: str
    problema: str
    evidencia: str
    acao: str
    justificativa: str
    impacto_esperado: str
    risco: str
    confianca: str
    urgencia: str
    prazo_reavaliacao: str
    metrica_verificacao: str
    condicionada_margem: bool


def conectar_db(caminho=ARQUIVO_DB) -> sqlite3.Connection:
    return sqlite3.connect(caminho)


def _agregar_campanhas(conn: sqlite3.Connection, conta: str, dia_de: datetime.date,
                       dia_ate: datetime.date) -> list[dict]:
    """Uma linha por campanha, agregando a janela [dia_de, dia_ate] (inclusive)."""
    cur = conn.execute(
        """
        SELECT campaign_id, campaign_name,
               COUNT(DISTINCT data) AS dias,
               SUM(clicks) AS clicks_total,
               AVG(lost_impression_share_by_budget) AS media_perdido_orcamento,
               AVG(lost_impression_share_by_ad_rank) AS media_perdido_ranking,
               AVG(roas) AS media_roas,
               AVG(roas_target) AS media_roas_target,
               SUM(cost) AS custo_total,
               SUM(total_amount) AS receita_total
        FROM campanhas_diarias
        WHERE conta = ? AND data >= ? AND data <= ? AND status = 'active'
        GROUP BY campaign_id, campaign_name
        """,
        (conta, dia_de.isoformat(), dia_ate.isoformat()),
    )
    colunas = [d[0] for d in cur.description]
    return [dict(zip(colunas, linha)) for linha in cur.fetchall()]


def avaliar_campanha(conta: str, ag: dict) -> list[Recomendacao]:
    """Funcao pura: 1 campanha agregada -> 0+ recomendacoes. Sem dado
    suficiente (MIN_DIAS/MIN_CLICKS), devolve [] -- "monitorando", nao vira
    recomendacao (regra: nunca recomendar em cima de amostra fraca)."""
    dias = ag.get("dias") or 0
    clicks = ag.get("clicks_total") or 0
    if dias < MIN_DIAS or clicks < MIN_CLICKS:
        return []

    cid = str(ag["campaign_id"])
    nome = ag.get("campaign_name") or "(sem nome)"
    janela = f"{dias} dia(s), {clicks} clique(s) na janela"
    recs: list[Recomendacao] = []

    perdido_orc = ag.get("media_perdido_orcamento")
    if perdido_orc is not None and perdido_orc >= LIMIAR_ORCAMENTO:
        urgencia = "alta" if perdido_orc >= LIMIAR_URGENCIA_ALTA else "media"
        recs.append(Recomendacao(
            conta=conta, campaign_id=cid, campaign_name=nome,
            tipo="orcamento_insuficiente",
            problema=f"Campanha perdendo impressoes por orcamento baixo "
                     f"({perdido_orc:.0%} das vezes que poderia ter sido exibida).",
            evidencia=f"media de lost_impression_share_by_budget={perdido_orc:.2%} "
                      f"na janela ({janela}).",
            acao="Aumentar o orcamento diario da campanha.",
            justificativa="O sinal oficial da propria plataforma indica orcamento "
                          "insuficiente para capturar as impressoes disponiveis "
                          "(nao e um calculo caseiro de custo/orcamento).",
            impacto_esperado="Reducao da perda por orcamento, mais impressoes/cliques "
                             "capturados dentro do mesmo ranking.",
            risco="Aumenta o gasto da campanha sem garantia de retorno proporcional "
                  "-- sem dado de margem por SKU, nao da pra confirmar que vale a pena.",
            confianca="alta" if dias >= 2 * MIN_DIAS else "media",
            urgencia=urgencia,
            prazo_reavaliacao="7 dias",
            metrica_verificacao="lost_impression_share_by_budget deve cair apos o ajuste.",
            condicionada_margem=True,
        ))

    perdido_rank = ag.get("media_perdido_ranking")
    if perdido_rank is not None and perdido_rank >= LIMIAR_RANKING:
        urgencia = "alta" if perdido_rank >= LIMIAR_URGENCIA_ALTA else "media"
        recs.append(Recomendacao(
            conta=conta, campaign_id=cid, campaign_name=nome,
            tipo="ranking_baixo",
            problema=f"Campanha perdendo impressoes por ranking baixo "
                     f"({perdido_rank:.0%} das vezes que poderia ter sido exibida).",
            evidencia=f"media de lost_impression_share_by_ad_rank={perdido_rank:.2%} "
                      f"na janela ({janela}).",
            acao="Revisar o ACOS/CPC objetivo da campanha, a qualidade dos anuncios "
                 "e a segmentacao de palavras-chave (sinal oficial da plataforma).",
            justificativa="O anuncio participa do leilao (tem orcamento) mas nao "
                          "tem ranking suficiente pra ser exibido -- ajuste de "
                          "competitividade, nao so de verba.",
            impacto_esperado="Mais leiloes vencidos, mais impressoes/cliques.",
            risco="Aumentar o ACOS/CPC objetivo tambem aumenta o custo por clique "
                  "-- sem dado de margem por SKU, nao da pra confirmar que vale a pena.",
            confianca="alta" if dias >= 2 * MIN_DIAS else "media",
            urgencia=urgencia,
            prazo_reavaliacao="7 dias",
            metrica_verificacao="lost_impression_share_by_ad_rank deve cair apos o ajuste.",
            condicionada_margem=True,
        ))

    roas = ag.get("media_roas")
    roas_alvo = ag.get("media_roas_target")
    if roas is not None and roas_alvo and roas < roas_alvo:
        recs.append(Recomendacao(
            conta=conta, campaign_id=cid, campaign_name=nome,
            tipo="roas_abaixo_do_alvo",
            problema=f"ROAS medio da campanha ({roas:.2f}x) abaixo do objetivo "
                     f"definido ({roas_alvo:.2f}x).",
            evidencia=f"media de roas={roas:.2f} vs. roas_target={roas_alvo:.2f} "
                      f"na janela ({janela}); custo total R${ag.get('custo_total') or 0:.2f}, "
                      f"receita total R${ag.get('receita_total') or 0:.2f}.",
            acao="Revisar a campanha: considerar reduzir orcamento, pausar ou "
                 "reavaliar a estrategia/objetivo (PROFITABILITY/INCREASE/VISIBILITY).",
            justificativa="A campanha esta consistentemente abaixo do proprio "
                          "objetivo de retorno que voce definiu para ela.",
            impacto_esperado="Reducao de gasto ineficiente ou correcao de estrategia.",
            risco="Reduzir/pausar corta tambem as vendas organicas associadas "
                  "aquela campanha (organic_units_quantity).",
            confianca="alta" if dias >= 2 * MIN_DIAS else "media",
            urgencia="media",
            prazo_reavaliacao="7 dias",
            metrica_verificacao="roas deve subir acima de roas_target apos o ajuste.",
            condicionada_margem=False,
        ))

    return recs


def gerar_recomendacoes(conn: sqlite3.Connection, conta: str, dia_ate: datetime.date,
                        janela_dias: int = JANELA_DIAS_PADRAO) -> list[Recomendacao]:
    dia_de = dia_ate - datetime.timedelta(days=janela_dias - 1)
    agregados = _agregar_campanhas(conn, conta, dia_de, dia_ate)
    recs: list[Recomendacao] = []
    for ag in agregados:
        recs.extend(avaliar_campanha(conta, ag))
    return recs


def formatar_relatorio(recs: list[Recomendacao]) -> str:
    if not recs:
        return "Nenhuma recomendacao -- ou dados insuficientes (< " \
              f"{MIN_DIAS} dias / {MIN_CLICKS} cliques na janela), ou nenhum " \
              "sinal acima do limiar."
    linhas = []
    for r in recs:
        linhas.append("=" * 70)
        linhas.append(f"[{r.urgencia.upper()}] {r.conta} — '{r.campaign_name}' "
                      f"(id {r.campaign_id}) — {r.tipo}")
        linhas.append(f"  Problema: {r.problema}")
        linhas.append(f"  Evidencia: {r.evidencia}")
        linhas.append(f"  Acao: {r.acao}")
        linhas.append(f"  Justificativa: {r.justificativa}")
        linhas.append(f"  Impacto esperado: {r.impacto_esperado}")
        linhas.append(f"  Risco: {r.risco}")
        linhas.append(f"  Confianca: {r.confianca} | Prazo de reavaliacao: "
                      f"{r.prazo_reavaliacao}")
        linhas.append(f"  Verificar depois com: {r.metrica_verificacao}")
        if r.condicionada_margem:
            linhas.append("  >>> Recomendacao condicionada a validacao da margem. <<<")
    return "\n".join(linhas)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Gera recomendacoes (sinais sem margem) a partir do historico coletado.")
    ap.add_argument("--dias", type=int, default=JANELA_DIAS_PADRAO,
                    help=f"tamanho da janela em dias (default {JANELA_DIAS_PADRAO})")
    ap.add_argument("--conta", default=None,
                    help="uma conta especifica (default: todas com historico)")
    ap.add_argument("--db", default=str(ARQUIVO_DB), help="caminho do SQLite")
    args = ap.parse_args(argv)

    conn = conectar_db(args.db)
    try:
        if args.conta:
            contas = [args.conta]
        else:
            cur = conn.execute("SELECT DISTINCT conta FROM campanhas_diarias ORDER BY conta")
            contas = [r[0] for r in cur.fetchall()]
        if not contas:
            print("Nenhum historico encontrado no banco. Rode ads-monitor/coletar.py antes.")
            return 1

        cur = conn.execute("SELECT MAX(data) FROM campanhas_diarias")
        ultimo_dia = cur.fetchone()[0]
        if not ultimo_dia:
            print("Nenhum historico encontrado no banco. Rode ads-monitor/coletar.py antes.")
            return 1
        dia_ate = datetime.date.fromisoformat(ultimo_dia)

        total = 0
        for conta in contas:
            recs = gerar_recomendacoes(conn, conta, dia_ate, args.dias)
            print(f"\n### {conta} (janela ate {dia_ate}, {args.dias} dias) ###")
            print(formatar_relatorio(recs))
            total += len(recs)
        print(f"\n{total} recomendacao(oes) no total.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
