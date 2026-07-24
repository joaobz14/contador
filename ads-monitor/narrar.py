#!/usr/bin/env python3
"""Camada de narrativa (opcional, com IA) sobre o monitor de Product Ads.

ads-monitor/ e propositalmente DETERMINISTICO: coletar.py so grava fatos,
recomendar.py so aplica regras fixas (avaliar_campanha) sobre o historico. Este
script e uma camada ADICIONAL e OPCIONAL por cima disso -- narra em portugues
natural o que recomendar.py ja calculou, sem inventar nenhuma conclusao nova.
Nao muda o motor de regras; se este script falhar ou nao rodar, recomendar.py
continua funcionando sozinho exatamente como antes.

Usa `claude -p` (Claude Code, ja instalado/autenticado na maquina do dono --
mesmo padrao do api-monitor/run-semanal.ps1) em vez de uma API de LLM externa:
sem credencial nova pra gerenciar, sem custo por token de terceiro.

O prompt passa SOMENTE o que o motor ja calculou (recomendacoes + campanhas
"monitorando" sem dado suficiente) e instrui explicitamente: narrar, nao
inventar -- mesmas guardas de recomendar.py (nunca concluir sobre margem, nunca
sugerir mudanca automatica, preservar "condicionada a validacao da margem").

Uso:
    python ads-monitor/narrar.py                    # janela padrao, todas as contas
    python ads-monitor/narrar.py --dias 14
    python ads-monitor/narrar.py --conta cozilatti
    python ads-monitor/narrar.py --dry-run           # so mostra o prompt, nao chama a IA
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recomendar as rm  # noqa: E402

PASTA = Path(__file__).resolve().parent
PASTA_RELATORIOS = PASTA / "relatorios"
TZ_BR = ZoneInfo("America/Sao_Paulo")

REGRAS = f"""Voce e um analista de Mercado Ads (Product Ads) do Mercado Livre.

Sua unica tarefa e ORGANIZAR EM PROSA CLARA, em portugues do Brasil, os dados
abaixo -- que ja foram calculados por um motor de regras deterministico. Voce
NAO deve calcular, inferir ou concluir nada que nao esteja explicito nos dados
recebidos.

REGRAS OBRIGATORIAS:
1. Nao invente recomendacoes alem das listadas em "recomendacoes" de cada conta.
2. Nao remova nem suavize o aviso de recomendacao "condicionada a validacao da
   margem" -- preserve-o tal como veio no campo "condicionada_margem".
3. Nao conclua lucratividade, prejuizo ou margem de nenhuma campanha -- essa
   fonte de dado nao existe no projeto ainda.
4. Nao sugira nenhuma mudanca automatica (pausar, editar lance, mudar
   orcamento) -- toda acao e manual, decidida pelo dono da conta.
5. Campanhas em "monitorando" NAO tem recomendacao (dado insuficiente: menos
   de {rm.MIN_DIAS} dias distintos ou {rm.MIN_CLICKS} cliques na janela, ou
   dentro dos limiares/saudavel). Apresente-as como "em observacao", nunca
   como problema ou oportunidade.
6. Use exatamente os numeros fornecidos -- nao arredonde de forma que mude a
   conclusao, nao calcule metricas novas a partir dos dados brutos.
7. Va direto ao ponto: um paragrafo de resumo executivo, depois uma secao por
   conta com as recomendacoes (se houver) e as campanhas em observacao.
8. Se nenhuma conta tiver recomendacao, diga isso claramente -- nao invente um
   problema so para preencher o relatorio.
9. Nao mencione preco, estoque, termos de busca, concorrencia ou qualquer
   outro dado que nao esteja no JSON fornecido.

Responda somente com o relatorio final (sem preambulo do tipo "aqui esta").
"""


def _campanhas_sem_recomendacao(conn, conta: str, dia_de: datetime.date,
                                dia_ate: datetime.date) -> list[dict]:
    """Campanhas que NAO geraram recomendacao (dado insuficiente ou saudavel)
    -- para o relatorio mostrar explicitamente quem esta "em observacao" em
    vez de simplesmente sumir do texto."""
    agregados = rm._agregar_campanhas(conn, conta, dia_de, dia_ate)
    sem_rec = []
    for ag in agregados:
        if rm.avaliar_campanha(conta, ag):
            continue
        dias = ag.get("dias") or 0
        clicks = ag.get("clicks_total") or 0
        motivo = ("dado insuficiente" if dias < rm.MIN_DIAS or clicks < rm.MIN_CLICKS
                  else "dentro dos limiares (saudavel)")
        sem_rec.append({
            "campaign_id": str(ag["campaign_id"]),
            "campaign_name": ag.get("campaign_name") or "(sem nome)",
            "dias": dias, "clicks": clicks, "motivo": motivo,
        })
    return sem_rec


def montar_dados(conn, contas: list[str], dia_ate: datetime.date,
                 janela_dias: int) -> dict:
    """Monta o payload que vai pro prompt -- so o que recomendar.py ja
    calculou, nada novo. Funcao pura o suficiente pra testar sem chamar IA."""
    dia_de = dia_ate - datetime.timedelta(days=janela_dias - 1)
    contas_payload = []
    for conta in contas:
        recs = rm.gerar_recomendacoes(conn, conta, dia_ate, janela_dias)
        contas_payload.append({
            "conta": conta,
            "recomendacoes": [
                {
                    "campaign_id": r.campaign_id,
                    "campaign_name": r.campaign_name,
                    "tipo": r.tipo,
                    "problema": r.problema,
                    "evidencia": r.evidencia,
                    "acao": r.acao,
                    "justificativa": r.justificativa,
                    "impacto_esperado": r.impacto_esperado,
                    "risco": r.risco,
                    "confianca": r.confianca,
                    "urgencia": r.urgencia,
                    "prazo_reavaliacao": r.prazo_reavaliacao,
                    "metrica_verificacao": r.metrica_verificacao,
                    "condicionada_margem": r.condicionada_margem,
                }
                for r in recs
            ],
            "monitorando": _campanhas_sem_recomendacao(conn, conta, dia_de, dia_ate),
        })
    return {
        "periodo": {"de": dia_de.isoformat(), "ate": dia_ate.isoformat(),
                    "dias": janela_dias},
        "gerado_em": datetime.datetime.now(TZ_BR).isoformat(timespec="seconds"),
        "contas": contas_payload,
    }


def montar_prompt(dados: dict) -> str:
    return (f"{REGRAS}\nDados (JSON, ja calculados pelo motor de regras):\n\n"
           f"{json.dumps(dados, ensure_ascii=False, indent=2)}")


def chamar_claude(prompt: str, *, timeout: int = 180) -> str:
    """Roda `claude -p` com o prompt via stdin, devolve a saida (stdout).
    Nunca levanta por 'claude' ausente/travado -- devolve "" e quem chama
    decide o que fazer (a camada de IA e aditiva, nao pode derrubar o motor
    de regras determinístico se falhar ou nao estiver instalada)."""
    claude = shutil.which("claude")
    if not claude:
        return ""
    try:
        r = subprocess.run(
            [claude, "-p"], input=prompt, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8",
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def salvar_relatorio(texto: str, dia_ate: datetime.date, pasta=PASTA_RELATORIOS) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(TZ_BR).strftime("%Y-%m-%d_%H%M%S")
    caminho = pasta / f"narrativa_{dia_ate.isoformat()}_{stamp}.md"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Narra em portugues (IA opcional) o que recomendar.py ja calculou.")
    ap.add_argument("--dias", type=int, default=rm.JANELA_DIAS_PADRAO,
                    help=f"tamanho da janela em dias (default {rm.JANELA_DIAS_PADRAO})")
    ap.add_argument("--conta", default=None,
                    help="uma conta especifica (default: todas com historico)")
    ap.add_argument("--db", default=str(rm.ARQUIVO_DB), help="caminho do SQLite")
    ap.add_argument("--dry-run", action="store_true",
                    help="so monta e imprime o prompt, nao chama a IA nem grava arquivo")
    args = ap.parse_args(argv)

    conn = rm.conectar_db(args.db)
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

        dados = montar_dados(conn, contas, dia_ate, args.dias)
        prompt = montar_prompt(dados)

        if args.dry_run:
            print(prompt)
            return 0

        texto = chamar_claude(prompt)
        if not texto:
            print("A IA nao respondeu (claude ausente, travado ou falhou). "
                 "Use --dry-run para conferir o prompt, ou rode "
                 "recomendar.py diretamente (motor determinístico, sem IA).")
            return 1

        caminho = salvar_relatorio(texto, dia_ate, pasta=PASTA_RELATORIOS)
        print(texto)
        print(f"\nSalvo em {caminho}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
