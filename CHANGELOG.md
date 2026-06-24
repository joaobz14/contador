# Changelog

Histórico das principais mudanças do projeto.

## [Não lançado]

### Bot do Telegram
- Impressão pelo bot: botão **🖨 Imprimir** por grupo nas listagens, com
  confirmação (Confirmar/Cancelar) antes de gerar a etiqueta. Reaproveita
  `imprimir_pendentes` do núcleo (imprime só os pendentes e marca o estado).
- O bot passa a aplicar a config do núcleo (`aplicar_config`): usa a **conta
  ativa** e respeita o `carimbar_sku` do `config.json`, igual à tela.
- **Multi-conta no bot:** comando `/conta` para ver/trocar a conta ativa pelo
  Telegram (com 2+ contas) e fallback para a primeira conta quando a salva
  some/é inválida (antes o bot caía no `credenciais.json` da raiz e falhava).
  A impressão recusa grupos de uma conta diferente da ativa (evita imprimir
  com o token errado depois de trocar de conta).

### Robustez
- `marcar_impresso` recarrega o estado do disco e **mescla** antes de gravar:
  a tela e o bot na mesma conta ao mesmo tempo não apagam mais a marcação um
  do outro (last-writer-merge em vez de last-writer-wins).

### Qualidade
- **CI (GitHub Actions):** roda o `pytest` em cada Pull Request e push no `main`
  (Python 3.11 e 3.12), mostrando um check verde/vermelho automático. Badge no
  topo do README.

## [1.0.0]

### Organização e segurança
- Estrutura do repositório organizada; `.gitignore`, `README`, `requirements`.
- Remoção de segredos do versionamento (`credenciais.json`) e `credenciais.example.json`.
- `pyproject.toml`, `.gitattributes` e `.editorconfig`.

### Núcleo / API
- Núcleo lança `SeparadorError` em vez de encerrar o processo (CLI e GUI tratam o erro).
- Retry com backoff em downloads de etiquetas; aborta em falha parcial (não marca impresso).
- Pipeline de coleta unificado entre CLI e GUI.
- Datas no horário de Brasília (filtro de despacho correto independente do fuso da máquina).
- Caminhos de arquivos baseados na pasta do script.

### Desempenho
- Dispensa a chamada `/sla` por envio (prazo lido do próprio detalhe do envio).
- Cache de envios finalizados: pula os já enviados nas próximas buscas.
- Paginação da busca de pedidos em paralelo.
- Melhor convivência com o limite de requisições do ML (respeita `Retry-After` + jitter).

### Robustez
- Leitura tolerante e gravação atômica dos arquivos JSON (estado, caches, credenciais).
- Retry também em falhas de rede (conexão/timeout).
- Limpeza automática de entradas antigas do estado.

### Leitura dos pedidos
- Comandos `amanha` e `dia <AAAA-MM-DD>`; seletor Hoje/Amanhã na tela.
- Estado de impressão por dia de despacho.
- Nomes amigáveis por SKU (`nomes_sku.json`).
- Tela abre parada, deixando o usuário escolher o filtro.

### Lançadores (Windows)
- `Abrir Separador.bat`, `Abrir Separador (diagnostico).bat`, `Abrir Separador.pyw`.
- `Atualizar programa.bat` (git pull por duplo-clique).

### Qualidade
- Suíte de testes automatizados (pytest).
- SessionStart hook para preparar o ambiente nas sessões da web.
