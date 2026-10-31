# WayFire 🔥
### Emulador Competitivo e Companion de Free Fire para Linux (Baseado em Waydroid)

O **WayFire** é uma camada de software nativa em Python projetada para transformar o ecossistema do **Waydroid** em uma experiência de emulação Android completa, especializada em jogos competitivos de tiro — com foco primário no **Free Fire**.

Diferente de emuladores tradicionais de Windows (BlueStacks, LDPlayer, SmartGaga) que dependem de máquinas virtuais pesadas (QEMU/VirtualBox), o WayFire aproveita a arquitetura de contêiner LXC do Waydroid, executando o jogo diretamente sobre o kernel do Linux com **latência quase zero, resposta direta de GPU e desempenho máximo de FPS**.

---

## 🎯 Proposta de Valor e Objetivos

1. **Sensibilidade X e Y Realmente Ajustável (Puxada de Capa)**:
   - Sensibilidade horizontal (X) para movimentação 360° fluida.
   - Sensibilidade vertical (Y) com multiplicador independente e ajuste fino para subida de mira na cabeça.
   - Ajuste de aceleração linear e curva de resposta do mouse.

2. **Mapeamento de Teclas 100% Customizável pelo Usuário**:
   - Camada visual transparente (Overlay) para posicionar, redimensionar e configurar qualquer botão na tela.
   - Suporte a botões de clique único, analógico WASD, mira FPS com trava de cursor, disparo, agachar, deitar e macros.
   - Perfis salvos em arquivos `.json` com importação e exportação fáceis.

3. **Integração Total com Waydroid Sem Complicações**:
   - Gerenciamento automático de resolução esticada competitiva (ex: `1440x1080` ou `1024x768`) com 1 clique.
   - Otimização automática de DPI e propriedades de aparelho (spoofing para ASUS ROG Phone para liberar 90/120 FPS).
   - Injeção direta de comandos de toque via subsistema de input do Linux (`uinput`).

---

## 📂 Documentação do Projeto

- [Como o WayFire conversa com o Waydroid](ARCHITECTURE.md)
- [Sistema de Mapeamento de Teclas Customizável](KEYMAPPING.md)
- [Roadmap de Desenvolvimento e Fases](ROADMAP.md)
