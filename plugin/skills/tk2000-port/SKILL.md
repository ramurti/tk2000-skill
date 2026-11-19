---
name: tk2000-port
description: Portar um jogo ou programa para o Microdigital TK2000 (TK2000 II Color, 64K, parecido com o Apple II, Brasil 1984) a partir de uma ROM de Atari 2600 (.a26/.bin), de uma imagem de disco de Apple II (.dsk/.do/.po), de fonte 6502 ou de um disassembly comentado, ou de outra linguagem. Use ao começar, continuar ou depurar um porte para o TK2000 (port, porting), ao gerar fitas (.ct2/.wav) ou discos do TK2000, ou ao responder perguntas sobre vídeo, teclado, som, memória ou formatos de fita e disco do TK2000.
---

# Portar para o TK2000

Conhecimento e ferramentas de seis portes concluídos: River Raid, Tennis, Pole Position e Enduro
(Atari 2600), Kung Fu Master (disco de Apple II) e Queen's Gambit (um motor de xadrez em
JavaScript). Tudo em `references/` foi medido, lido no fonte do emulador ou aprendido com um erro;
o que não foi verificado no hardware real está indicado como tal.

## 1. Identifique a origem e leia os arquivos certos

Leia sempre `references/maquina.md` (o próprio TK2000) primeiro. Depois:

| O que você tem | Leia | Abordagem que funcionou |
|---|---|---|
| **ROM de Atari 2600** (`.a26`/`.bin`), sem fonte | `atari-2600.md` (§8.1 sem fonte, §8.3, §15) | Desmonte até remontar idêntico, rode a lógica do original sem mudanças, substitua o kernel de vídeo (Tennis; o Enduro rodou a ROM de 4K no próprio endereço `$F000`, sob a ROM do TK2000, §17) |
| **Disco de Apple II** (`.dsk`) | `apple-ii.md` (inteiro) | Extraia os arquivos, dê boot num Apple II em py65, desmonte, realoque a página 2 ($4000 -> $A000), confira em lockstep (execução lado a lado, passo a passo), substitua o hardware por uma camada pequena (Kung Fu Master) |
| **Fonte 6502 ou disassembly comentado** | `a-partir-do-fonte.md`, depois o arquivo da máquina | Primeiro reproduza o binário distribuído byte a byte (o fonte de 1985 do Pole Position, o disassembly do River Raid) |
| **Outra linguagem** (JS, C, BASIC...) | `a-partir-do-fonte.md` §14 | Traduza comando por comando, mantenha o original como referência, confira lance a lance |

Depois, conforme a necessidade: `ritmo-de-quadros.md` (velocidade do jogo sem timer: todo porte
de jogo de ação precisa), `fita-e-disco.md` (a entrega), `ferramentas.md` (cc65, py65, o emulador
sem janela, o checklist, armadilhas do ca65).

Portes de ROM e de DSK são onde está a maior parte do trabalho futuro: prefira **rodar o código
original sem mudanças** (só endereços e E/S alterados) a reescrevê-lo; é mais rápido e a
fidelidade pode ser provada.

## 2. Prepare a máquina (uma vez)

- O emulador: https://github.com/ramurti/emulador-tk2000 (o emulador de TK2000 do Fabio
  Belavenuto, com correções de fita, disco e 64K). Os `src/*.cpp` dele são a referência do
  comportamento emulado, e o harness é compilado a partir deles. Precisa de SDL2 (macOS
  `brew install sdl2`; Debian/Ubuntu `apt install libsdl2-dev`). Os portes foram feitos em macOS;
  o suporte a Linux está sendo adaptado: onde uma ferramenta ou Makefile supõe macOS (caminhos
  `/opt/homebrew`, `sips`), use `sdl2-config` e Pillow.
- `cc65` (ca65/ld65) para o código do TK2000; `dasm` para fontes de Atari 2600 (Linux: pelas
  releases no GitHub, se a distribuição não tiver pacote); Python 3 com um venv por projeto:
  `python3 -m venv .venv && .venv/bin/pip install py65 pillow` (também `mido` para MIDI).
- Compile o executor sem janela a partir de `scripts/tk2000/harness/run.cpp` (comando em
  `ferramentas.md` §10): ele carrega uma fita ou dá boot num disco, aperta teclas em momentos
  emulados, tira capturas de tela e despeja a memória. É assim que você testa sem pedir ao dono
  do projeto para jogar.

## 3. Fluxo de trabalho

0. **Primeiro o plano, depois a execução passo a passo.** Antes de escrever código, estude o
   original e escreva um plano para o dono do projeto: as etapas (abaixo), o que cada uma
   entrega, como será testada e quais escolhas ele fará pelo caminho (disposição da tela, cada
   cor, cada som, controles, tela de título). Mostre o plano, ajuste-o com o dono do projeto e
   só então comece. Depois, faça um passo de cada vez: construa, teste você mesmo, relate com
   capturas de tela ou gravações e pare até o dono do projeto experimentar. Mantenha o plano no
   README do projeto, marcando o que já foi feito, para que uma sessão futura possa continuá-lo.
1. **Torne o original reproduzível**: um fonte ou disassembly que remonta exatamente os mesmos
   bytes, e uma simulação em py65 da máquina original rodando-o (`scripts/atari/vcs.py`,
   `scripts/apple/a2boot.py`).
2. **Planeje memória e tela** (`maquina.md` §2-3): as duas páginas de alta resolução (hi-res)
   ($2000, $A000), código em $4000-$9FFF, 16K sob a ROM no modelo de 64K ($C200-$FFFF;
   $C100-$C1FF é a ROM de boot do disco).
3. **Faça o original rodar no TK2000**, com o hardware substituído (Atari: kernel -> rotina de
   desenho; Apple: latch do teclado, paddles, carregador de arquivos, página 2).
4. **Prove que é igual ao original**: rode os dois em py65 lado a lado com as mesmas entradas e
   compare o estado a cada quadro ou instrução (`tkcheck.py`, `lockstep.py`): 0 diferenças.
   Depois percorra todas as opções de menu e teclas no emulador de verdade: a comparação só
   prova os caminhos que executou.
5. **Velocidade** (`ritmo-de-quadros.md`): meça os tiques por segundo emulado no emulador.
6. **Entregue**: uma fita que se inicia sozinha (`scripts/tk2000/mkct2.py`), um WAV para o
   hardware real (`ct2wav.py`), um disco com boot próprio (`mkdsk.py` + `boot.s`), `dist/` +
   `INSTRUCTIONS.txt`.
7. **Melhore em passos pequenos aprovados pelo dono do projeto**: cores, sons, música, menus,
   extras.
8. **Registre o que foi aprendido**: o README do projeto e o arquivo correspondente em
   `references/`.

## 4. Como trabalhar com o dono do projeto (todos os portes até agora)

- **Passos pequenos e testáveis**; uma funcionalidade por passo, testada no emulador sem janela
  antes de reportar. Olhe as suas próprias capturas de tela antes de dizer que algo funciona.
- **Mostre, depois deixe o dono do projeto escolher** (ele pediu isso explicitamente): antes de
  qualquer decisão visual ou de som, gere as opções como arquivos que o dono do projeto possa
  abrir e comparar, rotule-as A, B, C..., e diga em uma linha cada o que muda e quanto custa
  (fps, memória, tempo de carga). Depois espere a escolha; não escolha pelo dono do projeto.
  - **É isso que faz um porte bom.** O TK2000 tem 6 cores, com limites a cada 7 pixels, e um
    alto-falante de 1 bit: quase toda cor e todo som do original precisam ser aproximados, e a
    primeira aproximação raramente é a melhor. Um porte em que o agente escolheu sozinho fica
    com aparência e som piores. Por isso: todo mapeamento de cor (céu, chão, objetos, cada hora
    do dia ou fase), todo efeito sonoro, a música, a tela de título e os controles passam por
    aqui; ofereça de 2 a 4 opções de verdade (compromissos diferentes, não variações de uma
    mesma ideia), diga qual você escolheria e por quê, e mesmo assim deixe o dono do projeto
    decidir. Se ele disser que tanto faz, pergunte de novo pelas que se veem ou se ouvem o
    tempo todo.
  - **Imagens**: o original (captura do simulador) ao lado de cada opção do TK2000, mesmo
    momento, mesma escala (folhas de contato com Pillow; recortes ampliados quando o detalhe é
    pequeno, ex.: as faixas do pôr do sol); também uma versão "TV" borrada quando as cores se
    misturam.
  - **Sons**: um som de cada vez; um WAV do original (`*-2600.wav`) e um por opção do TK2000
    (`*-tk-A.wav`, `*-tk-B.wav`...), os mesmos poucos segundos da mesma corrida; depois de
    implementar a escolhida, uma gravação do programa de verdade (`*-tk.wav`) cortada nos mesmos
    tiques do jogo, para confirmar que soa como a prévia. Se não soar, descubra por quê (meça)
    antes de oferecer novas opções.
  - Quando o dono do projeto não conseguir decidir entre duas, gere as duas como fitas/discos
    jogáveis.
  - Mostre as suas próprias capturas de tela do resultado depois de implementar (do emulador,
    não só do py65).
- **Prévias na pasta `build/` do projeto**, informadas com caminhos absolutos (não /tmp).
- **Fiel ao original, mas corrija os defeitos dele** (o wrap-around do Atari, playfield
  desalinhado); melhorias de bom gosto são bem-vindas quando pedidas ou propostas; nada de
  simplificações visuais.
- **Privado e local**: os portes contêm ROMs/discos comerciais: só em repositórios privados,
  nunca adicionados ao repositório público do emulador. `dist/*.wav` fica local (nunca vai para
  commit).
- **Meça, não chute**: controles pela memória (os bits de direção do jogo), não por capturas de
  tela; som pelos cliques do alto-falante registrados; velocidade por tiques por segundo.
- Relate com clareza o que foi verificado e o que não foi.

## 5. Scripts

`scripts/README.md` lista cada ferramenta, o porte de onde veio e o que adaptar. A maioria foi
escrita para um jogo só: copie-as para a pasta `tools/` do novo projeto e mude as partes
específicas do jogo (nomes de arquivos, endereços, tabelas); não as rode no lugar. As genéricas
(`mkct2.py`, `lz.py`, `ct2wav.py`, `dos33.py`, o harness) funcionam como estão.
