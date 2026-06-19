# Changelog

Histórico das principais mudanças do projeto.

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
