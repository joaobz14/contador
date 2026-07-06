"""
Abrir Separador.pyw
Lancador da tela do Separador de Etiquetas para duplo-clique no Windows.

Por ser .pyw, o Windows abre com o pythonw (sem a janela preta de terminal).
Garante que o programa rode na pasta deste arquivo, onde ficam o
credenciais.json, o estado_grupos.json e o cache (caminhos relativos).

Obs.: o duplo-clique depende de o Windows ter o .pyw associado ao pythonw.
Se nada acontecer ao clicar, use o "Abrir Separador.bat", que e mais garantido.
"""

import os
import sys

# Este arquivo mora em atalhos/; o projeto (e os credenciais) ficam na pasta-mae.
_PASTA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_PASTA)
sys.path.insert(0, _PASTA)

import separador_gui

if __name__ == "__main__":
    separador_gui.main()
