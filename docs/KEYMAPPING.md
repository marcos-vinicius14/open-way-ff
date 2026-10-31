# Mapeamento de Teclas Customizável

O **WayFire** foi concebido sob a premissa de que **nenhum jogador joga igual**. O sistema de mapeamento de teclas é 100% aberto, visual e customizável pelo próprio usuário.

---

## 🖥️ 1. O Editor Visual (Overlay Transparente)

O editor de mapeamento do WayFire roda como uma camada transparente desenhada exatamente sobre a janela do Waydroid.

### Modos de Operação:
* **Modo de Edição (`Edit Mode`)**:
  - O cursor do mouse fica livre sobre a tela.
  - O jogador pode criar, mover e configurar botões diretamente sobre a interface do Free Fire.
  - Segue o **fluxo intuitivo do GG Mouse Pro** (descrito abaixo).
* **Modo de Jogo (`Mapping Mode`)**:
  - O overlay fica visualmente discreto (opacidade ajustável de 0% a 100%).
  - Pressionar teclas do teclado gera toques virtuais instantâneos nas posições mapeadas.
  - O atalho global **`F1`** alterna entre o Modo de Edição e o Modo de Jogo a qualquer momento.

---

## ⚡ 2. Fluxo de Criação de Botões (Estilo GG Mouse Pro)

A experiência de criação foi inspirada no **GG Mouse Pro**, tornando o processo o mais rápido e natural possível:

```
[1. Clique Duplo na Tela] 
          │
          ▼
[2. Cria a "Bolinha" com estado de escuta (?)] 
          │
          ▼
[3. Pressione Qualquer Tecla] 
          │
          ▼
[4. Tecla vinculada imediatamente àquela posição!]
```

### Detalhes do Comportamento:
1. **Criar Botão (Duplo Clique)**:
   - No Modo de Edição, dê **dois cliques com o botão esquerdo** em qualquer ponto da tela (em cima do botão de pular, atirar, agachar, kit, etc.).
   - Uma **"bolinha" (círculo de mapeamento)** surge instantaneamente naquela coordenada exata.
2. **Captura Imediata (Próxima Tecla)**:
   - A bolinha recém-criada entra no estado de escuta (*Listening State*), piscando ou exibindo um indicador `[ ? ]`.
   - **A próxima tecla física pressionada pelo usuário** (teclado ou botões laterais do mouse) é imediatamente atribuída àquela bolinha.
   - O símbolo da tecla (ex: `E`, `Shift`, `Mouse 4`, `Espaço`) aparece cravado no centro do círculo.
3. **Reposicionamento e Exclusão**:
   - **Arrastar**: Clique e segure na bolinha para arrastá-la e fazer microajustes de posição.
   - **Excluir**: Clique na bolinha e aperte `Del`/`Backspace`, ou clique com o botão direito sobre ela e selecione **Remover**.
4. **Editar Tecla Existente**:
   - Para trocar a tecla de uma bolinha já existente, basta dar um clique simples nela e apertar a nova tecla desejada.

---

## 🎛️ 3. Tipos de Componentes Suportados

O usuário pode posicionar livremente qualquer um dos seguintes componentes:

### A. Botão de Ação Simples (`TapButton`)
* **Uso**: Pular, Agachar, Deitar, Recarregar, Usar Kit, etc.
* **Comportamento**: Quando a tecla física é pressionada, gera um toque no ponto $(X, Y)$ da tela. Ao soltar a tecla, o toque é liberado.
* **Opções**:
  - `Tipo`: Toque simples (*Single Tap*), Segurar (*Hold*), ou Repetição Rápida (*Turbo*).

### B. Analógico Virtual (`DPad`)
* **Uso**: Movimentação do personagem via `W, A, S, D`.
* **Comportamento**: Mapeia 4 direções e suas diagonais (ex: `W+D`).
* **Opções**:
  - Raio do analógico (*Radius*).
  - Zona morta (*Deadzone*).
  - Suporte a botão de corrida integrado.

### C. Controlador de Câmera e Mira FPS (`AimController`)
* **Uso**: Olhar ao redor, mirar e movimentar a mira com o mouse.
* **Comportamento**: Converte deltas relativos do mouse em arrastes na tela.
* **Opções Exclusivas**:
  - **Sensibilidade X**: Multiplicador horizontal (Ex: `1.2`).
  - **Sensibilidade Y**: Multiplicador vertical (Ex: `2.8` — calibrado para facilitar subir capa).
  - **Tecla de Suspender**: Tecla usada para travar/destravar o cursor do mouse (Ex: `Ctrl`, `Alt`, `F` ou `Caps Lock`).
  - **Suavização do Mouse**: Filtro para evitar trepidações em mouses de alto DPI.

### D. Botão de Disparo / Gatilho (`FireButton`)
* **Uso**: Atirar (geralmente mapeado para o `Clique Esquerdo do Mouse`).
* **Comportamento**: Otimizado para responder apenas enquanto a mira estiver travada (evita disparar ao clicar em botões de menu).

---

## 📄 3. Estrutura do Arquivo de Perfil (`JSON`)

Todas as configurações de teclas e sensibilidade são salvas em arquivos JSON legíveis e compartilháveis em `~/.config/wayfire/profiles/`.

### Exemplo de Configuração (`freefire.json`):
```json
{
  "profile_name": "Free Fire Competitivo",
  "game_package": "com.dts.freefireth",
  "resolution": {
    "width": 1440,
    "height": 1080
  },
  "mouse_settings": {
    "sensitivity_x": 1.45,
    "sensitivity_y": 3.20,
    "lock_hotkey": "Control_L",
    "smoothing": true
  },
  "ui_settings": {
    "show_keys_on_screen": true,
    "osd_opacity": 0.35
  },
  "widgets": [
    {
      "id": "aim_camera",
      "type": "aim",
      "x": 1050,
      "y": 540,
      "width": 400,
      "height": 400
    },
    {
      "id": "movement_dpad",
      "type": "dpad",
      "x": 260,
      "y": 780,
      "radius": 90,
      "keys": {
        "up": "W",
        "down": "S",
        "left": "A",
        "right": "D"
      }
    },
    {
      "id": "fire_button",
      "type": "tap",
      "key": "Mouse_Left",
      "x": 1280,
      "y": 620
    },
    {
      "id": "scope_button",
      "type": "tap",
      "key": "Mouse_Right",
      "x": 1310,
      "y": 420
    },
    {
      "id": "jump_button",
      "type": "tap",
      "key": "Space",
      "x": 1350,
      "y": 720
    },
    {
      "id": "crouch_button",
      "type": "tap",
      "key": "c",
      "x": 1220,
      "y": 880
    },
    {
      "id": "reload_button",
      "type": "tap",
      "key": "r",
      "x": 1180,
      "y": 280
    }
  ]
}
```

---

## 🔄 4. Compartilhamento e Perfis
* **Importar / Exportar**: O usuário pode exportar seu layout e sensibilidade em um arquivo `.json` para compartilhar com amigos ou em grupos.
* **Múltiplos Perfis**: Possibilidade de criar perfis para diferentes modos de jogo (ex: *Perfil Rushador*, *Perfil Sniping*, *Perfil Padrão*).
