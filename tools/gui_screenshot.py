"""
gui_screenshot.py
Roda a GUI do separador (separador_gui.py) headless, sob um display virtual,
e salva um PNG — para validar mudancas VISUAIS em ambientes sem monitor
(ex.: Claude Code na web, onde nao ha display).

Uso (com xvfb fornecendo o display):
  xvfb-run -a python3.12 tools/gui_screenshot.py [saida.png] [marketplace]

  saida.png    caminho do PNG de saida   (padrao: gui.png)
  marketplace  "Shopee" | "Mercado Livre" (padrao: Mercado Livre)
  --autoteste  agenda um callback que estoura de proposito, para a CI provar
               que o guardiao abaixo realmente reprova (ver GUARDIAO)

Pre-requisitos: tkinter + imagemagick (o `import`). O script
tools/setup_gui_tests.sh instala tudo. Abre na TELA INICIAL (nao busca
pedidos), entao nao precisa de rede nem de credenciais.

GUARDIAO — POR QUE ESTE SCRIPT PRECISA REPROVAR SOZINHO:
Ele e o corpo do job `gui-smoke` da CI, cujo proposito declarado e pegar
"quebra de import, erro de montagem/renderizacao do Tkinter na inicializacao".
So que o Tk CAPTURA excecao de callback (`after`, clique, trace), imprime no
stderr e SEGUE — e a tela agenda varios `after(...)` na abertura. Sem o
`report_callback_exception` abaixo, um erro nesses callbacks deixava o script
tirar o screenshot e sair com codigo 0: o job ficava VERDE com a tela
quebrada, e o bug seguia para o `main` e para a maquina de operacao.
Guardiao que passa quando o que ele guarda esta quebrado nao guarda nada.
"""
import os
import subprocess
import sys
import time
import tkinter as tk
import traceback

# Permite rodar de qualquer cwd (o projeto e a pasta-mae de tools/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_gui as gui  # noqa: E402

autoteste = "--autoteste" in sys.argv
argv = [a for a in sys.argv[1:] if a != "--autoteste"]
saida = argv[0] if argv else "gui.png"
marketplace = argv[1] if len(argv) > 1 else "Mercado Livre"

falhas: list[str] = []


def _registrar_falha(exc, val, tb) -> None:
    """Anota o erro que o Tk engoliria e o repete no stderr (para o log da CI)."""
    texto = "".join(traceback.format_exception(exc, val, tb))
    falhas.append(texto)
    print(f"ERRO em callback do Tk:\n{texto}", file=sys.stderr)


root = tk.Tk()
root.report_callback_exception = _registrar_falha   # antes de qualquer callback rodar
app = gui.SeparadorApp(root)
if marketplace != "Mercado Livre":
    app.marketplace_var.set(marketplace)   # reflete no radio
    app._trocar_marketplace(marketplace)
if autoteste:
    root.after(1, lambda: 1 / 0)           # so no autoteste: prova que o guardiao reprova
root.update()
time.sleep(0.3)                            # deixa o WM/render assentar
root.update()                              # drena os after(...) agendados na abertura
# subprocess com lista de args (nao os.system com f-string): um `saida` com
# espacos ou metacaracteres de shell quebrava/era interpretado (auditoria 5.15).
subprocess.run(["import", "-window", "root", saida], check=True)  # captura o display virtual
root.destroy()
print(f"Screenshot salvo: {saida}  (marketplace: {marketplace})")

# O screenshot sai ANTES de reprovar de proposito: com a tela quebrada, a
# imagem e a primeira pista de diagnostico e sumiria se o script morresse antes.
if falhas:
    print(f"\nFALHOU: {len(falhas)} erro(s) em callback do Tk durante a abertura.\n"
          "A tela montou, mas quebrou ao rodar. Veja os tracebacks acima.",
          file=sys.stderr)
    raise SystemExit(1)
