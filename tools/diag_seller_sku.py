#!/usr/bin/env python3
"""Diagnostico SO-LEITURA: por que itens tipo ad_group ITEM nao resolveram SKU.

Pega uma amostra de item_id sem SKU (tipo ITEM) do historico_ads.sqlite3 e
busca o detalhe RAW de cada um na API (GET /items/{id}), pra comparar
seller_custom_field vs. um possivel atributo SELLER_SKU dentro de
`attributes` -- a hipotese e que o campo certo mudou pra alguns itens.

- SO GET. Nao grava nada, nao altera item nenhum.
- Nao mascara nada aqui (titulo/atributos de item nao sao segredo; nenhum
  token aparece no output).

Uso:
    python tools/diag_seller_sku.py [conta] [--limite N]
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_etiquetas_ml as core  # noqa: E402

ARQUIVO_DB = Path(__file__).resolve().parent.parent / "ads-monitor" / "historico_ads.sqlite3"


def _amostra(limite: int) -> list[tuple[str, str]]:
    conn = sqlite3.connect(ARQUIVO_DB)
    try:
        rows = conn.execute(
            "SELECT DISTINCT i.item_id, i.titulo FROM ad_group_itens_diarios i "
            "JOIN ad_groups_diarios ag USING (data, conta, ad_group_id) "
            "WHERE ag.ad_group_type='ITEM' AND i.sku IS NULL LIMIT ?", (limite,)
        ).fetchall()
    finally:
        conn.close()
    return rows


def main() -> int:
    args = sys.argv[1:]
    limite = 5
    if "--limite" in args:
        i = args.index("--limite")
        limite = int(args[i + 1])
        del args[i:i + 2]
    conta = args[0] if args else ""

    if conta:
        core.definir_conta(conta)
    cred = core.carregar_credenciais()
    token = core.obter_token(cred)

    itens = _amostra(limite)
    if not itens:
        print("Nenhum item tipo ITEM sem SKU encontrado no banco (rode o "
              "coletor antes, ou todos ja resolveram).")
        return 0

    for item_id, titulo in itens:
        print("=" * 60)
        print(f"item_id={item_id}  titulo={titulo!r}")
        try:
            det = core._get(f"{core.API}/items/{item_id}", token,
                            params={"include_attributes": "all"})
        except Exception as e:
            print(f"  ERRO ao buscar: {type(e).__name__}: {e}")
            continue
        print(f"  seller_custom_field = {det.get('seller_custom_field')!r}")
        print(f"  catalog_listing = {det.get('catalog_listing')!r}  "
              f"catalog_product_id = {det.get('catalog_product_id')!r}")
        attrs = det.get("attributes") or []
        sku_attrs = [a for a in attrs
                    if "SKU" in str(a.get("id", "")).upper()
                    or "sku" in str(a.get("name", "")).lower()]
        if sku_attrs:
            print(f"  atributos com 'SKU' no nome: {sku_attrs}")
        else:
            print(f"  nenhum atributo com 'SKU' no nome (de {len(attrs)} atributos totais)")
        print(f"  chaves de topo do item: {sorted(det.keys())}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
