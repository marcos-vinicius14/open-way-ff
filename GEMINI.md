<!-- GSD:project-start source:PROJECT.md -->

## Project

**WayFire 🔥**

WayFire é uma camada de software nativa em Python projetada para transformar o ecossistema do Waydroid em uma experiência de emulação Android completa, especializada em jogos competitivos de tiro — com foco primário no Free Fire. O projeto opera como um companion/wrapper de alto desempenho sobre o kernel Linux, eliminando a sobrecarga de VMs tradicionais e fornecendo latência quase zero (<1ms), resposta direta de GPU e taxa máxima de FPS.

**Core Value:** Emulação competitiva de Free Fire no Linux com controle absoluto de Sensibilidade X e Y independente ("puxada de capa"), injeção direta de toques via `/dev/uinput` com latência instantânea (<1ms) e editor visual de mapeamento de teclas intuitivo estilo GG Mouse Pro.

### Constraints

- **Tecnologia**: Python 3 com `python-evdev`, GTK4, Libadwaita e `gtk4-layer-shell`.
- **Permissões**: Acesso de escrita em `/dev/uinput` e leitura em `/dev/input/event*` (configurado via regras udev / grupo `input`).
- **Desempenho**: Latência de processamento de input <1ms, sem drops de FPS.
- **Compatibilidade**: Waydroid rodando sobre Linux x86_64 com aceleração de hardware (Mesa/VA-API).

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
