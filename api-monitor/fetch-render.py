"""Pre-renderiza as fontes SPA da Shopee (JavaScript no cliente) e salva o HTML
renderizado em api-monitor/fetched/<slug>.html, para o run-semanal.ps1/claude
comparar arquivos locais em vez de depender do WebFetch (que numa SPA pega so a
casca vazia).

Usa o Playwright dirigindo o Edge JA instalado no Windows (channel="msedge"),
entao NAO baixa navegador — so precisa do pacote: `pip install playwright`.
O Edge --dump-dom via linha de comando devolvia vazio no --headless=new; o
Playwright espera a SPA hidratar e pega o page.content() de verdade.

Best-effort: se o Playwright nao estiver instalado, o Edge nao abrir, ou a
pagina nao renderizar, avisa e sai com codigo 0 — o run-semanal segue e o claude
marca a fonte como "bloqueada". Nunca derruba a rotina.
"""
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
OUT = AQUI / "fetched"

FONTES = {
    "shopee-announcements": "https://open.shopee.com/announcements",
    "shopee-documents": "https://open.shopee.com/documents",
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("  aviso: playwright nao instalado. Rode uma vez:  pip install playwright")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    try:
        pw = sync_playwright().start()
    except Exception as e:
        print(f"  aviso: nao consegui iniciar o Playwright: {e}")
        return 0

    try:
        try:
            browser = pw.chromium.launch(channel="msedge", headless=True)
        except Exception as e:
            print(f"  aviso: nao consegui abrir o Edge (channel=msedge): {e}")
            return 0
        ctx = browser.new_context(user_agent=UA, locale="pt-BR",
                                  viewport={"width": 1366, "height": 900})
        for slug, url in FONTES.items():
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass                     # a SPA pode manter conexoes abertas; segue
                html = page.content()
                destino = OUT / f"{slug}.html"
                tmp = destino.with_suffix(".html.part")
                tmp.write_text(html, encoding="utf-8")
                tmp.replace(destino)         # gravacao atomica
                marca = "ok" if len(html) >= 2000 else "SUSPEITO (curto)"
                print(f"  {slug}: {len(html)} chars [{marca}] -> {destino.name}")
            except Exception as e:
                print(f"  {slug}: FALHOU {type(e).__name__}: {str(e)[:200]}")
            finally:
                page.close()
        browser.close()
    finally:
        pw.stop()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                    # rede da rotina nunca cai por causa daqui
        print(f"  aviso: fetch-render.py falhou: {e}")
        sys.exit(0)
