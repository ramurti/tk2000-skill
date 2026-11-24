# Scripts

Copiados dos portes já terminados. As ferramentas **genéricas** rodam como estão; as
ferramentas **modelo** foram escritas para um jogo: copie-as para a pasta `tools/` (ou `src/`)
do projeto novo e adapte as partes específicas do jogo (nomes de arquivo, endereços, tabelas).
A docstring de cada arquivo diz o que ele faz e como rodá-lo.

## tk2000/ — o lado do TK2000 (todo porte)

| Arquivo | Tipo | O quê |
|---|---|---|
| `mkct2.py` | genérica | Fita `.ct2` de vários arquivos com partida automática: `mkct2.py prog.bin LOAD START NAME out.ct2 [extra.bin@ADDR ...]` |
| `ct2wav.py` | genérica | `.ct2` -> `.wav` para carregar num TK2000 de verdade com `LOADT` |
| `lz.py` | genérica | Pequeno compactador LZ (e o descompactador em Python); o descompactador 6502 é o `Unlz` em `apple/tk.s` |
| `mkdsk.py`, `boot.s` | genérica | Disco com partida automática para a interface de disco do TK2000 (`CALL 49408`): `mkdsk.py OUT.dsk PROGRAM.bin@ADDR START [HIGH.bin@ADDR]`; um carregador de ~500 bytes na trilha 0 lê o programa (a partir de `ADDR`) e a parte opcional sob a ROM (a partir de `$C200`+) das trilhas 1+, e depois salta para `START` (espera `src/boot.s`, `cfg/raw.cfg`, `build/`). Usado pelo Kung Fu Master (duas partes) e pelo Tennis (um arquivo em $4000) |
| `midi2tk.py` | modelo (Kung Fu) | Melodia MIDI de uma voz -> tabela de música para o bipe |
| `raw.cfg` | genérica | Configuração do ld65 para binários crus num `.org` |
| `harness/run.cpp` | genérica | Emulador sem janela (o harness): carrega um `.ct2` (ou dá partida num `.dsk`), teclas em tempos emulados, capturas de tela PPM, despejos e escritas de memória, WAV do áudio. Compila contra o `src/` do emulador (veja `references/ferramentas.md` §10) |
| `mkstart.py`, `start.s` | modelo (Enduro) | Tela inicial desenhada na partida a partir de uma fonte 5x7 (e uma 3x5) invertendo pares de pixels sobre o preto: título, teclas, uma opção trocada com uma tecla, créditos; ~600 bytes em vez de uma imagem compactada. O `mkstart.py` gera a fonte e os textos (`start.inc`) e um PNG de prévia; o `start.s` usa `FlipP`, `FillBlack`, `LineLo/LineHi` do porte |
| `harness/call.cpp` | genérica | Chama uma rotina de um binário no 6502 emulado e imprime registradores/memória (testes unitários do código que vai ser entregue) |

## atari/ — originais de Atari 2600 (ROM, disassembly ou fonte)

| Arquivo | Tipo | De onde | O quê |
|---|---|---|---|
| `vcs.py` | genérica | Pole Position / Tennis | Um pequeno Atari 2600 no py65 (CPU, TIA desenhando color clock a color clock, RIOT): cartuchos de 2K, 4K e 8K F8 (conferido: Tennis 2K e espelhado como 4K, Pole Position 8K), capturas de tela; ciclos do DEC abs corrigidos. Ajuste `ROM`/`SYM` no topo para o jogo novo |
| `dis2600.py` | modelo | Tennis | Disassembler que remonta idêntico (dasm); `--tk` gera a versão do TK2000 com o gancho. Escrito para uma ROM de 2K: para 4K mude as constantes de tamanho (`0x7FF`/`0x800` -> `0xFFF`/`0x1000`) |
| `coverage.py` | modelo | Tennis | Roda a ROM com entradas programadas, registra quais bytes rodam como código (alimenta o `dis2600.py`); máscara de 2K `0x7FF`, como acima |
| `tkcheck.py` | modelo | Tennis | Binário do TK2000 vs o cartucho no py65, mesmas entradas, compara as variáveis do original a cada quadro |
| `cost.py` | modelo | Tennis | Ciclos por quadro do programa do TK2000, posições dos checkpoints |
| `sndprev.py`, `soundcmp.py` | modelo | Tennis, Pole Position | Prévias em WAV do som da TIA do original e dos cliques do alto-falante do TK2000 |
| `pole2dasm.py` | modelo | Pole Position | Converte a sintaxe do montador da Atari de 1985 para a do dasm |
| `atari.py`, `scanlines.py` | modelo | River Raid | Executor de 2600 mais antigo; registro, linha a linha, do que o kernel escreve |
| `check_river.py` | modelo | River Raid | Uma rotina portada vs a original, saída por saída |
| `profile_labels.py` | modelo | Enduro | Ciclos por rotina (exclusivos e inclusivos) do programa inteiro ao longo de uma corrida, por rótulo (`.sym` do dasm + `-Ln` do ld65) |
| `sndfit.py`, `enduro_sound.s` | modelo | Enduro | Som de dois canais da TIA tocado continuamente por checkpoints temporizados (`SND`): o tocador 6502 e o ajustador que mede o tempo de cada checkpoint no py65, gera o `sndk.inc`, grava o alto-falante e imprime o erro de altura por categoria |
| `collcheck.py` | modelo | Enduro | Uma rotina reescrita contra a antiga (mantida sob `.ifdef`) em cada chamada de uma longa corrida: prova que uma otimização não muda nada |
| `calibrate.py`, `costcheck.py`, `profile.py`, `hotspots.py` | modelo | River Raid | Calibração do custo em ciclos (mínimos quadrados), custo estimado vs real, perfil |

## apple/ — discos de Apple II

Todos do Kung Fu Master; a ordem abaixo é a ordem do trabalho (`references/apple-ii.md` §9.2).

| Arquivo | Tipo | O quê |
|---|---|---|
| `dos33.py` | genérica | Catálogo DOS 3.3 e arquivos binários de um `.dsk` |
| `a2boot.py` | quase genérica | Um Apple II no py65 (64K, language card, Disk II com nibbles 6-e-2, teclado, paddles, botões) que dá partida no `.dsk`; teclas/joystick programados; registra os arquivos carregados, a E/S usada, os endereços executados por arquivo; retratos da memória |
| `sfboot.py` | quase genérica | Estudo de um disco **sem catálogo DOS 3.3** (crack ou carregador próprio): dá boot pelo `a2boot.py` e registra as trilhas lidas e quando, a E/S, a memória escrita (RAM principal, os dois bancos de `$D000` e `$E000-$FFFF` do language card), as páginas executadas, capturas das duas páginas hi-res a cada N ciclos; salva e continua de um estado (`-S`/`-L`); `-A` começa de um estado salvo do AppleWin; `-D 32` faz o disco girar na velocidade real (Sky Fox) |
| `awrun.py` | genérica | Roda um `.dsk` no AppleWin para Linux sem janela (Apple II+ de 64K) com teclas programadas; capturas das duas páginas hi-res, despejos de memória e o WAV do alto-falante ao longo do tempo. A referência de comportamento quando o Apple do py65 diverge (Sky Fox). Precisa do `applewin-key.patch` |
| `awcmp.py` | genérica | Parte de um estado salvo do AppleWin, roda o Apple do py65 até o ciclo exato de outro estado salvo e lista o que difere (registradores, RAM, language card): acha o intervalo onde o py65 se separa do AppleWin (Sky Fox) |
| `applewin-key.patch` | genérica | Acrescenta ao servidor de depuração do AppleWin para Linux `/api/key?code=HEX` (aperta uma tecla) e `/api/snapshot?file=CAMINHO&at=CICLO` (salva o estado entre quadros no ciclo pedido), e o `#include <cstdint>` que falta para o GCC 13 |
| `disa2.py` | modelo | Disassembly ca65 dos arquivos (código = o executado + rastreio estático), bytes idênticos; `--tk` realocado, `--io` E/S do TK2000 alterada |
| `ctx.py` | genérica | Disassembly em volta de um endereço |
| `taint.py`, `candidates.py` | modelo | Rodam o jogo rastreando de onde veio cada byte: quais bytes montam endereços para as áreas que se mudam |
| `immscan.py` | genérica | Padrões `LDA #hi / STA` em código que nunca rodou (confira cada um pelo uso) |
| `records.py` | modelo | Decodifica a tabela de objetos de um jogo (exemplo de leitura das estruturas de dados de um jogo) |
| `relocs.py` | modelo | Toda mudança nos bytes do original: realocação, alterações de E/S, os ganchos das melhorias |
| `lockstep.py` | modelo | Original (com partida pelo disco) vs o porte, instrução por instrução, mesmas entradas (lockstep = execução lado a lado, passo a passo) |
| `mkimage.py` | modelo | Dá partida no disco até o início do jogo, pega a memória e os registradores, coloca a camada do TK2000 por cima, compacta os overlays sob a ROM, grava a imagem da fita |
| `tk.s` | modelo | A camada de hardware no endereço do antigo carregador: tabela de saltos, carregador de arquivos (descompacta), latch de teclado do Apple a partir da matriz, paddles/botões a partir de teclas, Start |
| `sfx.s` | modelo | Efeitos sonoros e música ligados a eventos do jogo, guardados sob a ROM |
| `tkview.py` | genérica | Uma tela hi-res de um despejo de memória como o Apple a mostra e como o TK2000 mostraria os mesmos bytes, lado a lado (Sky Fox) |
| `recolor.py` | genérica | Reescreve os bytes de uma tela do Apple para o TK2000 mostrar cores parecidas (verde -> verde, azul -> azul; violeta à escolha): prévia de remapeamento de cores (Sky Fox) |
| `hgr.py` | genérica | Páginas da tela de alta resolução (hi-res) do Apple num despejo de memória, como PNG |
