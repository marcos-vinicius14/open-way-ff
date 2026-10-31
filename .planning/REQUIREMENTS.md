# Requirements: WayFire 🔥

**Defined:** 2026-10-30
**Core Value:** Emulação competitiva de Free Fire no Linux com sensibilidade X e Y independente (puxada de capa), conversão de mouse para touch via `/dev/uinput` com latência instantânea (<1ms) e rotação infinita de câmera sem travar na borda da tela.

## v1 Requirements

### Input & Sensitivity Engine

- [x] **CORE-01**: Injetor de toque virtual multitouch de baixa latência (<1ms) via Linux Kernel `/dev/uinput` (`python-evdev`).
- [x] **CORE-02**: Captura de baixo nível de mouse e teclado com hotkey de trava/destrava do cursor (suspender mouse).
- [x] **CORE-03**: Motor de sensibilidade horizontal (X) e vertical (Y) com multiplicador independente para subida de capa.
- [x] **CORE-04**: Algoritmo anti-borda com recentralização invisível de toque (1ms) para rotação contínua e infinita de câmera 360°.

### Waydroid Control & Performance

- [x] **WAY-01**: Controlador de ciclo de vida do Waydroid em Python (iniciar/parar contêiner e sessão, lançamento direto de app).
- [x] **WAY-02**: Gerenciamento dinâmico de resoluções de tela competitivas (1920x1080 16:9, 1440x1080 e 1024x768 esticado 4:3).
- [x] **WAY-03**: Spoofing de propriedades de hardware (ASUS ROG Phone) para desbloquear 90/120 FPS e gráficos no Ultra no Free Fire.

### Keymapping & Profiles

- [x] **MAP-01**: Gerenciador de perfis JSON em `~/.config/wayfire/profiles/` com importação, exportação e perfil padrão competitivo (`default_freefire.json`).
- [x] **MAP-02**: Componentes de mapeamento customizáveis: TapButton (Single/Hold/Turbo), DPad analógico WASD, AimController (mira/câmera) e FireButton (gatilho).
- [x] **MAP-03**: Algoritmo de proteção contra o bug do analógico com reset suave ao suspender mouse.

### Graphical Overlay & UI

- [x] **UI-01**: Overlay transparente Wayland (GTK4 / Layer Shell) para visualização OSD com controle de opacidade (0% a 100%).
- [x] **UI-02**: Modo de edição interativo estilo GG Mouse Pro (duplo clique cria bolinha em escuta, captura instantânea da próxima tecla física, arrastar/soltar, exclusão e redimensionamento).
- [x] **UI-03**: Launcher principal estilo central de jogos com sliders de sensibilidade X/Y, seletor de resolução em 1 clique, seletor de perfis e botão "Jogar Free Fire".

### Packaging & Distribution

- [ ] **PKG-01**: Script de instalação automatizada em um comando (`install.sh`) com configuração de permissões udev para `/dev/uinput`.
- [ ] **PKG-02**: Empacotamento oficial para Arch Linux / AUR (`PKGBUILD`).

## v2 Requirements

### Advanced Features & Extended Ecosystem

- **EXT-01**: Suporte a gravação e reprodução de macros competitivas complexas.
- **EXT-02**: Integração com curvas de aceleração de mouse customizáveis (ex: curva Sigmoide / Raw Accel).
- **EXT-03**: Perfis pré-definidos para outros jogos de tiro (COD Mobile, PUBG Mobile, Arena Breakout).
- **EXT-04**: Hub comunitário para compartilhamento e download direto de perfis pela interface.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Emulação via Máquinas Virtuais (QEMU/VirtualBox) | Desempenho e latência inferiores; o WayFire foca 100% no contêiner LXC nativo Waydroid |
| Injeção de toques via comandos ADB (`input tap`) | Latência de 100-200ms inaceitável para jogos de tiro competitivo |
| Servidor Scrcpy sobre socket TCP/ADB | Exige depuração USB e adiciona camada extra de latência comparado ao uinput direto |
| Suporte a compositores X11 legados | Waydroid e overlays modernos utilizam protocolos Wayland (zwlr_layer_shell_v1) nativamente |
| Trapaças, aimbots ou modificação de memória | O WayFire é estritamente um emulador e mapeador de periféricos, respeitando a integridade do jogo |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Complete |
| CORE-02 | Phase 1 | Complete |
| CORE-03 | Phase 1 | Complete |
| CORE-04 | Phase 1 | Complete |
| WAY-01 | Phase 2 | Complete |
| WAY-02 | Phase 2 | Complete |
| WAY-03 | Phase 2 | Complete |
| MAP-01 | Phase 2 | Complete |
| MAP-02 | Phase 3 | Complete |
| UI-01 | Phase 3 | Complete |
| UI-02 | Phase 3 | Complete |
| MAP-03 | Phase 4 | Complete |
| UI-03 | Phase 4 | Complete |
| PKG-01 | Phase 5 | Pending |
| PKG-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-30*
*Last updated: 2026-10-30 after initialization*
