# Phase 2: Comunicação com Waydroid e Gerenciamento de Perfis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-31
**Phase:** 2-comunicacao-com-waydroid-e-gerenciamento-de-perfis
**Areas discussed:** Ciclo de Vida e Lançamento do Waydroid, Resolução Esticada e Comportamento de Reinício, Injeção de Spoofing ASUS ROG Phone, Schema e Validação de Perfis JSON

---

## Ciclo de Vida e Lançamento do Waydroid

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Checagem inteligente com tentativa de inicialização | Verifica `systemctl is-active waydroid-container`, tenta iniciar e orienta em caso de falha de permissão | ✓ |
| Checagem estrita sem tentar iniciar | Apenas verifica e aborta imediatamente exigindo inicialização manual | |
| Você decide | Abordagem mais flexível | |

**Escolha do usuário:** Opção 1 (Checagem inteligente com tentativa de inicialização)
**Notas:** O sistema tenta ativar o daemon do Waydroid de forma transparente e dá instruções claras caso precise de `sudo`.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Processo em background com polling de prontidão | Dispara `waydroid session start` em background assíncrono e monitora `waydroid status` até `RUNNING` | ✓ |
| Aguardar tempo fixo (sleep) | Dispara em background e aguarda tempo pré-determinado sem checar status | |
| Você decide | Método mais estável | |

**Escolha do usuário:** Opção 1 (Processo em background com polling de prontidão)
**Notas:** Garante que o jogo só será aberto quando o Android estiver 100% pronto para receber conexões.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Auto-detecção inteligente com override no perfil | Inspeciona pacotes instalados (`waydroid app list`), priorizando o perfil ou Standard | ✓ |
| Fallback sequencial simples | Tenta Standard e depois MAX caso retorne erro | |
| Exigir definição estrita no perfil | Lança exclusivamente o pacote configurado | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Auto-detecção inteligente com override no perfil)
**Notas:** Suporta jogadores de Free Fire Standard (`com.dts.freefireth`) e Free Fire MAX (`com.dts.freefiremax`) sem intervenção manual.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Parada do app com preservação opcional da sessão | Fecha o jogo via `am force-stop` preservando a sessão, com opção `--full` para parada completa | ✓ |
| Encerramento total imediato | Sempre executa `waydroid session stop` ao fechar | |
| Desconectar apenas o input | Desliga apenas o motor de captura do WayFire | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Parada do app com preservação opcional da sessão)
**Notas:** Permite fechar e reabrir o jogo sem esperar os segundos de boot da sessão Waydroid.

---

## Resolução Esticada e Comportamento de Reinício

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Integrada ao Perfil JSON com Presets Competitivos | Armazena `width` e `height` no perfil com presets rápidos (1080p, 1440x1080, 1024x768) | ✓ |
| Configuração Global do Sistema | Armazenada separadamente em `config.json` global | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Integrada ao Perfil JSON com Presets Competitivos)
**Notas:** Facilita alternar perfis com resoluções distintas automaticamente.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Verificação idempotente prévia | Consulta `waydroid prop get` antes de alterar; se já for igual, não reescreve nem reinicia | ✓ |
| Aplicação forçada a cada execução | Sempre reescreve propriedades a cada execução | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Verificação idempotente prévia)
**Notas:** Evita reinícios e lentidão quando o contêiner já estiver na resolução desejada.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Reinício transparente automático | Encerra a sessão graciosamente e reabre automaticamente com nova resolução | ✓ |
| Perguntar/Avisar o usuário | Exibe mensagem solicitando reinício manual da sessão | |
| Aplicar apenas antes de iniciar a sessão | Bloqueia troca de resolução com sessão aberta | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Reinício transparente automático)
**Notas:** Aplica a nova geometria na janela Wayland de forma transparente.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Atualização dinâmica de dimensões no Injetor | Repassa `width` e `height` dinamicamente ao `TouchInjector` e `AimEngine`, multiplicando percentuais normalizados | ✓ |
| Escala fixa virtual (0 a 32767) | Usa escala fixa virtual no uinput | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Atualização dinâmica de dimensões no Injetor)
**Notas:** Precisão pixel-perfect nos toques virtuais no HUD esticado.

---

## Injeção de Spoofing ASUS ROG Phone

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Injeção nativa via `waydroid prop set` | Aplica propriedades essenciais via comandos nativos de propriedades | ✓ |
| Modificação direta de arquivos de configuração | Edita arquivos em `/var/lib/waydroid/waydroid.cfg` ou build.prop | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Injeção nativa via `waydroid prop set`)
**Notas:** Método limpo e seguro contra corrupção de imagens de sistema.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Backup automático prévio com comando de restauração | Salva backup em `device_backup.json` e provê comando `--restore` | ✓ |
| Spoofing permanente sem backup | Assume contêiner dedicado sem salvar estado original | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Backup automático prévio com comando de restauração)
**Notas:** Segurança e reversibilidade caso o usuário queira voltar ao estado padrão.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Verificação automática inteligente no lançamento | Verifica se o modelo já é `ASUS_I005D` ao iniciar o jogo e aplica apenas se necessário | ✓ |
| Apenas por comando manual prévio | Exige execução de `wayfire spoof` manual | |
| Configuração por perfil (toggle) | Booleano por perfil | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Verificação automática inteligente no lançamento)
**Notas:** Zero atrito para o usuário com execução sob demanda transparente.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Conjunto completo essencial (Brand, Manufacturer, Model, Name, Device) | Injeta as 5 chaves cruciais para desbloqueio de 90/120 FPS e gráficos Ultra | ✓ |
| Conjunto mínimo (apenas Model e Brand) | Injeta apenas brand e model | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Conjunto completo essencial: Brand, Manufacturer, Model, Name, Device)
**Notas:** Garante compatibilidade com o motor gráfico do Free Fire.

---

## Schema e Validação de Perfis JSON

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Schema hierárquico com migração automática transparente | Adota schema moderno (`mouse_settings`, `resolution`, `widgets`, `ui_settings`) com migração no `from_dict()` | ✓ |
| Schema plano expandido | Apenas adiciona lista `widgets` no schema plano existente | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Schema hierárquico com migração automática transparente)
**Notas:** Modernização da arquitetura com total compatibilidade com arquivos já gerados.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Dataclasses polimórficas tipadas com fábrica discriminadora | Classes tipadas (`TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`) derivadas de `BaseWidget` | ✓ |
| Dicionários dinâmicos sem tipagem estrita | Lista genérica de dicionários | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Dataclasses polimórficas tipadas com fábrica discriminadora)
**Notas:** Elimina erros de digitação e prepara o terreno para o editor visual da Fase 3.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| HUD Completo Competitivo de Fábrica | Perfil `default_freefire.json` completo e pronto para jogar com todos os botões essenciais | ✓ |
| HUD Mínimo (Core) | Apenas DPad, AimController e FireButton | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (HUD Completo Competitivo de Fábrica)
**Notas:** Experiência out-of-the-box instantânea.

---

| Opção | Descrição | Selecionado |
|---|---|:---:|
| Gerenciador completo com validação e comandos CLI | CRUD completo, importação/exportação sanitizada e CLI integrada | ✓ |
| API básica interna apenas | Apenas métodos internos sem comandos CLI ou importação/exportação | |
| Você decide | | |

**Escolha do usuário:** Opção 1 (Gerenciador completo com validação e comandos CLI)
**Notas:** Gestão completa e compartilhamento de perfis no ecossistema WayFire.

---

## the agent's Discretion

- Timeout máximo de 30 segundos com polling de 0.5s para prontidão do Waydroid.
- Tratamento de exceções e mensagens amigáveis no terminal.
- Sanitização de caminhos de arquivos na importação para segurança.

## Deferred Ideas

- Overlay Visual Wayland Layer Shell com editor interativo (Fase 3).
- Proteção anti-bug do analógico virtual (Fase 4).
- Launcher Desktop moderno em GTK4 / Libadwaita (Fase 4).
