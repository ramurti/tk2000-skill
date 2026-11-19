# Como portar jogos para o TK2000

Guias práticos para levar jogos ao Microdigital TK2000 (TK2000 II Color, o computador brasileiro
parecido com o Apple II, de 1984), escritos a partir de portes concluídos, entre eles:

- **River Raid** (Activision, Atari 2600): um jogo de ação portado a partir do código 6502 do
  cartucho, com renderizador, sprites, ritmo de quadros e som próprios.
- **Kung Fu Master** (Data East, Apple II): roda a partir do código do disco original, realocado,
  com o hardware do Apple trocado por uma pequena camada (guia 8).
- **Queen's Gambit**: um programa de xadrez cujo motor era um programa JavaScript de 1 KB,
  traduzido para 6502 e depois deixado mais rápido e mais forte.

Todos foram feitos com o Claude Code (um agente de IA para programação) trabalhando junto com o
dono do projeto, em passos pequenos e testados. Os guias contam o que funcionou, o que não
funcionou e os números por trás de cada decisão.

| Guia | Leia quando |
|---|---|
| [0. Para quem está começando do zero](00-para-iniciantes.md) | Conta no Claude, VS Code, instalação e o primeiro projeto |
| [1. Primeiros passos](01-primeiros-passos.md) | Você quer um programa rodando no emulador hoje |
| [2. A máquina](02-a-maquina.md) | Você precisa da tela, do teclado, do alto-falante, do texto da ROM ou do mapa de memória |
| [3. Fitas e telas de título](03-fitas-e-telas-de-titulo.md) | Você está montando a fita: tela de carregamento, partida automática, vários arquivos |
| [4. Portando um jogo de Atari 2600](04-portando-um-jogo-de-atari-2600.md) | O original é um cartucho de 2600 |
| [5. Portando um programa de outra linguagem](05-portando-de-outra-linguagem.md) | O original está em JavaScript, C, BASIC... (um motor de jogo, uma IA) |
| [6. Testes e verificação](06-testes-e-verificacao.md) | Sempre: como provar que o porte faz o que o original faz |
| [7. Trabalhando com um agente de IA](07-trabalhando-com-um-agente-de-ia.md) | Você porta com o Claude Code ou um agente parecido |
| [8. Portando um jogo de Apple II](08-portando-um-jogo-de-apple-ii.md) | O original é uma imagem de disco de Apple II (`.dsk`) |
| [10. Curso rápido](10-curso-rapido.md) | **Novo no Claude Code?** Comece aqui: instale tudo e faça um primeiro porte (Seaquest) passo a passo |
| [9. A skill do Claude Code](09-a-skill-do-claude-code.md) | Você quer que o Claude Code faça o porte com todo este conhecimento e as ferramentas |

A referência completa por trás destes guias é a skill do Claude Code [`tk2000-port`](../../plugin/skills/tk2000-port/SKILL.md)
(mais densa, escrita para um agente que está começando um porte). As ferramentas estão em [`scripts/`](../../plugin/skills/tk2000-port/scripts) e um
programa mínimo em [`examples/hello/`](../../examples/hello).

## A máquina em uma tabela

| | TK2000 | O que isso significa para um porte |
|---|---|---|
| CPU | 6502 a 1.022.727 Hz | Igual ao Apple II: código 6502 é portado instrução por instrução |
| Vídeo | Só alta resolução (hi-res), 280 × 192, duas páginas (`$2000`, `$A000`) | Sem modo texto, sem sprites: tudo é desenhado por software |
| Cores | Pares de pixels: preto, branco, verde, azul (paleta 0) ou ciano, vermelho (paleta 1), paleta por byte de 7 pixels | Não são as cores do Apple II: os gráficos têm de ser redesenhados ou remapeados |
| Teclado | Matriz varrida por software | Sem trava de tecla: leia as teclas como um joystick |
| Som | Alto-falante de 1 bit | Som custa tempo de CPU; nada toca enquanto a CPU desenha |
| Temporizador | **Nenhum** (sem timer, sem retraço vertical) | A velocidade do jogo vem da contagem de ciclos da CPU |
| Armazenamento | Fita cassete (imagens `.ct2` no emulador) | Cerca de 170 bytes/s: um jogo de 24 KB carrega em ~2,5 minutos |
| RAM | 48 KB (+16 KB sob a ROM no modelo de 64 KB) | ~24 KB para código em `$4000-$9FFF` quando as duas páginas de hi-res são usadas |
