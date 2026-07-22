---
tags: [conceito, config, gui, concorrencia]
aliases: [aplicar_config, atualizar_config, _sanear_config, config.json]
type: conceito
---

# ⚙️ Config e saneamento

> [!abstract]
> As preferências ficam em `config.json` (local, por máquina). O **ponto único de
> saneamento** é `aplicar_config()` (`_sanear_config`): valor inválido é descartado e
> cai no default — um config editado à mão **não pode derrubar** a GUI/bot na abertura.

## Gravar por chave, não o dict inteiro
> [!warning] `atualizar_config(**chaves)`, nunca `salvar_config` do dict inteiro (na GUI)
> Cada GUI mantém `self.config` desde a abertura; regravar o dicionário inteiro reverte
> em silêncio chaves que outra instância mudou (**lost update** — fechar uma GUI de
> manhã desfazia a conta/marketplace da outra). `atualizar_config` relê o disco **sob
> [[Trava entre processos]]**, aplica só as chaves do evento e saneia.
> `salvar_config` (dict inteiro) fica só para o bot/testes.

## Valores válidos de identificação
`MODOS_IDENT` → [[Identificação na impressão (carimbo)]].

## Relacionado
- [[separador_etiquetas_ml (núcleo)]] · [[separador_gui]] · [[Trava entre processos]] · [[Arquivos — locais vs versionados]]
