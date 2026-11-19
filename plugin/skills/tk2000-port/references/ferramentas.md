# Ferramentas, harness de testes, checklist, material de referência

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. As pastas de jogo citadas (como `riverraid-tk2000`) são projetos do autor, não publicados; as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## 10. Ferramentas e fluxo de trabalho

- Montador: **cc65** (`ca65` + `ld65`) com uma configuração do linker: `STARTUP` em `$4000`
  (`JMP Start`), `TABLES` alinhado à página, `CODE`, `RODATA`, e uma segunda área de memória
  `LOW` (`$1200`, com arquivo de saída próprio) para os dados que transbordam. Confira o
  `build/*.map` depois de cada build: a área principal tem de terminar abaixo de `$A000`.
- Pegadinhas do ca65 encontradas:
  - `Y` é reservado: não use como nome de variável de `.repeat`
  - `.define` com vírgulas aninhadas quebra; use `.set` ou macros
  - `.set` com valores relocáveis falha; use uma macro que gera os bytes
  - desvio fora do alcance → inverta o desvio + `JMP`
  - rótulos anônimos (`:`/`:-`) dentro de macros quebram os laços em volta; use rótulos com nome
  - imediatos negativos (`#8-LINE_BIAS`) dão erro de faixa; reescreva como `sec` /
    `sbc #(LINE_BIAS-8)`
  - tabelas com mais de 255 entradas precisam de `.min()`
  - a macro `ADD_COST` estraga o A: nunca a coloque antes de código que ainda precisa do A
  - contadores de laço: `ldx #159` / `dex` / `bpl` sai depois de uma passada (159 > 127); use
    `inx` / `cpx #N` (aconteceu de novo no Tennis com uma tabela de 131 entradas)
  - mnemônicos não podem ser nomes: `cpy:` para um ponteiro de página zero é erro de sintaxe
  - referências de escopo (`DrawCol::pat`) têm de vir depois do `.proc`; as que vêm antes
    falham: use rótulos globais para operandos automodificados
  - `.repeat 192, I` e depois `I .mod 8`, `I / 8` funcionam para tabelas de linhas da tela de
    alta resolução (hi-res)
  - os rótulos locais baratos (`@x`) têm escopo entre rótulos normais, e uma atribuição de
    símbolo (`Name = *`) também encerra o escopo: para deixar outra rotina alterar um operando
    automodificado, guarde o valor do operando numa variável e deixe cada rotina alterar o seu
    próprio `@label`
  - uma tabela de glifos indexada por `7 * glyph` estoura 8 bits depois de 36 glifos: calcule o
    endereço em 16 bits (a tela inicial do Enduro desenhava lixo com 42 glifos)
- **Trocando uma rotina por uma mais rápida**: mantenha a antiga no fonte sob `.ifdef`
  (`COLLTEST`), monte um binário de teste com as duas e, em cada chamada de uma longa corrida no
  py65, rode as duas sobre cópias da memória e compare cada saída (Enduro `tools/collcheck.py`:
  6.000 chamadas, 0 diferentes). Depois meça de novo as constantes de ritmo (§7).
- **Conferências longas no py65 em segundo plano podem ficar sem CPU** no ambiente do agente
  (um lockstep de 2 minutos levou mais de 30 minutos): rode-as em primeiro plano com um tempo
  limite longo.
- **O py65 conta `DEC abs` ($CE) como 3 ciclos** (no 6502 real e no emulador: 6); todos os
  outros opcodes documentados batem. Corrija em cada instância: `mpu.cycletime =
  list(mpu.cycletime); mpu.cycletime[0xCE] = 6` (as ferramentas do Tennis fazem isso; as do
  Pole Position não, o que ali é inofensivo).
- Ferramentas em Python geram arquivos de include a partir da ROM original (sprites, gráficos
  de status) e montam as fitas; regras do `make` os regeneram.
- Ambiente Python: py65 e Pillow **não** estão no Python do sistema. Crie um venv para o
  projeto (`python3 -m venv .venv && .venv/bin/pip install py65 pillow`); a sessão do River Raid
  usou um na pasta de rascunho da sessão.
- **Emulador sem janela para testes** (o harness, `tools/harness/run.cpp`, compilado contra os
  fontes do emulador com SDL2):
  - build (macOS ou Linux; `EMU` = o `src/` do emulador; `call.cpp` igual, só com
    `Bus Cpu6502 Rom Ram`):
    ```sh
    c++ -std=c++17 -O2 -w -I$EMU $(sdl2-config --cflags) -include $EMU/pch.h tools/harness/run.cpp \
        $EMU/{Bus,Cpu6502,Rom,Ram,Video,Audio,Keyboard,Tape,Disk}.cpp $(sdl2-config --libs) -o build/run
    ```
  - `run TAPE.ct2 [-t SECONDS] [-s TIME:FILE.ppm]... [-k TIME:DURATION:KEY]... [-m ADDR:LEN]...`
  - os tempos são segundos emulados contados a partir do Play; ele mesmo digita `LOADT` e aperta
    o Play
  - KEY = left right up down space return fire(.) ou uma letra
  - as capturas de tela são PPM: converta com o Pillow (ou `sips -s format png in.ppm --out
    out.png` no macOS); monte folhas de contato com o Pillow para revisar muitos quadros de uma
    vez
  - os despejos de memória são impressos depois de cada linha de evento
  - o jogo só começa quando a carga termina (River Raid: ~130-145 s, cresce com o tamanho do
    programa); confira de novo a linha do tempo depois que o binário crescer
  - o zsh não divide `$args` em palavras: monte arrays de argumentos (`args+=(-s $t:/dev/null)`,
    depois `"${args[@]}"`), ou divida explicitamente com `${=args}` (o Enduro perdeu uma hora
    com isso: com as teclas numa string só, o executor ignorava em silêncio todas as opções
    depois dela, então nenhuma tecla era apertada e o despejo de memória faltava)
  - `-a TIME:DURATION:FILE.wav` grava o áudio do emulador (serve para conferir altura e tempo
    com uma FFT; ouvir continua sendo com o dono do projeto). Ele não gravou nada no Kung Fu: um
    `Audio.cpp` compilado com um registro do ciclo de cada clique do alto-falante
    (`SPKLOG=file`) e um script que renderiza os cliques num WAV funcionaram no lugar
  - a cópia do Kung Fu (`kungfu-tk2000/tools/harness/run.cpp`) acrescenta `-w TIME:ADDR:HEX`
    (escreve na memória, por exemplo para forçar um estado difícil de alcançar jogando) e a
    tecla `ctrl`
  - uma variante para disco: digite `CALL 49408` e insira um `.dsk` (o `CDisk` do emulador)
- Mantenha os contadores de quadros e de tiques em endereços fixos da página zero (`FRAMES`,
  `TICKS16`), para que o executor possa medir o fps e a velocidade do jogo pelos despejos de
  memória.
- Revise você mesmo as capturas de tela antes de dizer ao dono do projeto que algo funciona;
  quando a qualidade visual ou de áudio está em jogo, gere arquivos que o dono do projeto possa
  abrir direto (`build/` do projeto, caminhos absolutos).

## 11. Checklist para um porte novo

1. Obtenha o fonte/disassembly original; reproduza o binário bit a bit; monte a simulação do
   original no py65.
2. Planeje a disposição da tela (linhas do playfield, linhas de status, escala) e as cores;
   mostre opções de cor ao dono do projeto.
3. Plano de memória: código/dados em `$4000-$9FFF`, tabelas em `$0400-$1FFF`, as duas páginas
   da hi-res; divisão da página zero (variáveis originais nos seus endereços, o motor no resto).
4. Monte as ferramentas: montador de fita (com partida automática), geradores de
   sprites/blocos, executor sem janela, scripts de comparação.
5. Porte a lógica primeiro, confira-a contra o original no py65.
6. Renderizador com atualizações delta e troca de páginas; depois os sprites (pré-deslocados,
   restauração por página).
7. Ritmo de quadros com contabilidade do custo em ciclos; calibre no py65 e confira os
   tiques/s no emulador.
8. Colisões, pontuação, barra de status, estados do jogo (início, vida perdida, fim de jogo,
   reinício).
9. Som por último, um efeito de cada vez, com comparações de WAV contra o original.
10. Telas de introdução (créditos/aviso de direitos, história, título com opções), fita final
    (§6.4). Documente no README do projeto.


## 12. Arquivos para reaproveitar do River Raid (`riverraid-tk2000`)

| Arquivo | Reaproveitar para |
|---|---|
| `tools/mkct2.py` | fitas CT2 de vários arquivos com partida automática |
| `tools/harness/run.cpp` | testes no emulador sem janela |
| `tools/reference/atari.py` | rodar uma ROM de 2600 no py65 |
| `tools/reference/scanlines.py` | análise do kernel linha a linha |
| `tools/reference/calibrate.py`, `costcheck.py`, `profile.py`, `hotspots.py` | custos em ciclos, perfil |
| `tools/mksprites.py`, `tools/mkstatus.py`, `tools/colortest.py` | gráficos do 2600 → tabelas do TK2000, prévias de cor |
| `src/main.s` | laço principal, leitura da matriz do teclado, `Pace`/`Delay` |
| `src/render.s` | tabelas de linhas, padrão de renderizador delta |
| `src/sprites.s` | preparar/desenhar/restaurar/compor sprites, colisão entre sprites |
| `src/status.s` | dígitos e medidores da barra de status com estado "mostrado" por página |
| `src/sound.s` | porte da temporização do `DoSound` e o tocador de rajadas (tons, ruído, deslizes) |
| `src/title.s`, `src/story.s` | telas de créditos/título com opções, texto rolando |
| `tools/mkintro.py`, `tools/mktitle.py`, `tools/mkcredits.py`, `tools/mkstory.py` | conversão de imagens, telas, fontes de pixel com acentos |
| `cfg/tk2000.cfg`, `Makefile` | organização do build |

O Tennis (`tennis-tk2000`) acrescenta, para um cartucho de 2K sem fonte:

| Arquivo | Reaproveitar para |
|---|---|
| `tools/dis2600.py`, `tools/reference/coverage.py` | disassembly de uma ROM de 2600, versão `--tk` com o gancho |
| `tools/reference/vcs.py` | simulador de 2600 para ROMs de 2K, DEC abs corrigido |
| `tools/reference/tkcheck.py`, `cost.py` | porte vs original, ciclos por quadro e checkpoints |
| `tools/mkcourt.py`, `tools/mocknet.py`, `tools/mockup.py` | cenário estático a partir do simulador, protótipos |
| `tools/mkimages.py`, `src/shift.s` | imagens pré-deslocadas ao ligar (fita mais curta) |
| `src/sound.s`, `tools/reference/sndprev.py` | tons com o jogo congelado, cliques a partir de checkpoints, prévias em WAV |
| `src/start.s`, `tools/mkstart.py` | uma tela inicial sobre o playfield com uma fonte 5x7 |

O Kung Fu Master (`kungfu-tk2000`) acrescenta, para um disco de Apple II:

| Arquivo | Reaproveitar para |
|---|---|
| `tools/dos33.py` | catálogo DOS 3.3 e arquivos binários de um `.dsk` |
| `tools/a2boot.py` | um Apple II no py65 que dá partida num `.dsk` (Disk II, teclado, paddles), cobertura e retratos da memória |
| `tools/disa2.py`, `tools/ctx.py` | disassembly ca65 dos arquivos (bytes idênticos), `--tk` realocado, `--io` E/S do TK2000 |
| `tools/taint.py`, `tools/candidates.py`, `tools/immscan.py`, `tools/records.py` | encontrar endereços montados em tempo de execução para realocar |
| `tools/lockstep.py` | original vs porte, instrução por instrução |
| `tools/relocs.py`, `tools/mkimage.py` | tabelas de realocação/alterações, imagem a partir do início do original |
| `tools/lz.py`, `src/tk.s` | overlays compactados sob a ROM, latch de teclado / paddles / carregador de arquivos do Apple |
| `src/sfx.s`, `tools/midi2tk.py` | efeitos sonoros ligados ao jogo, uma melodia MIDI como música de bipe |
| `src/boot.s`, `tools/mkdsk.py` | um disco do TK2000 com partida automática |
| `tools/hgr.py` | despejos de memória da hi-res como PNG |


## 13. Material de referência

- `reference/manuals/` neste repositório: `tk2000_manual_tecnico.pdf` (manual técnico, 125
  páginas), `tk2000_manual_de_operacao.pdf` (manual de operação), `tk2000_entendendo_a_rom.pdf`
  (livro sobre a ROM): imagens escaneadas sem camada de texto — lê-los exige renderizar as
  páginas (por exemplo `brew install poppler` para a ferramenta Read) ou OCR.
- `tk2000_entendendo_a_rom.pdf` é a ROM do TK2000 comentada: o ponto de partida para qualquer
  trabalho futuro na própria ROM (o dono do projeto planeja melhorá-la).
- O fonte Atari de 1985 do Pole Position: `poleposition-tk2000/reference/POLE26.S` (portado).
- Fonte do emulador: `emulador-tk2000/src` (https://github.com/ramurti/emulador-tk2000;
  `Video.cpp`, `Keyboard.cpp`, `Tape.cpp`, `Rom.cpp`, `Audio.cpp`, `Cpu6502.cpp` são a
  referência definitiva do comportamento emulado).
