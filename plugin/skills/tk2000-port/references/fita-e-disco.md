# Fitas (CT2, carregadores com partida automática, telas de carga) e discos

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. As pastas de jogo citadas (como `kungfu-tk2000`) são projetos do autor, não publicados; as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## 6. Cassete, imagens de fita e carga

### 6.1 Formato CT2 (`Tape.cpp` do emulador, `tools/mkct2.py` do River Raid)

- Arquivo: `"CTK2"`, depois blocos de `ID (2 bytes) + tamanho (16 bits LE)`:
  - `CA`: guia longa (500 ciclos de 500/500)
  - `CB`: sincronismo (464, 679, 32 × 679/679, 199, 250)
  - `DA`: bytes de dados, bit mais significativo primeiro; bit 1 = 500 + 500 ciclos, bit 0 =
    250 + 250 ciclos
- Blocos de fita do TK2000 (como a ROM os grava):
  - cada arquivo = um bloco de cabeçalho + blocos de dados de até 256 bytes
  - bloco = nome (6 caracteres, bit alto ligado) + número de blocos de dados + índice do bloco
    (0 = cabeçalho) + conteúdo + checksum
  - checksum = XOR de todos os bytes anteriores do bloco, com semente `$FF` (ou seja, invertido)
  - conteúdo do cabeçalho = endereço inicial, endereço final (little endian)
- Velocidade de carga: ~6.000 ciclos por byte em média, ~170 bytes/s. Um programa de 24K leva
  cerca de 2 minutos e 20 s de tempo emulado (o emulador o roda em velocidade máxima).
- `LOADT` (digitado no prompt do BASIC) carrega um arquivo.

### 6.2 Fita com partida automática (nada a digitar depois do LOADT)

Técnica usada pelas fitas comerciais, implementada no `mkct2.py`:
1. O **arquivo 1** é um arquivo de página zero, `$0036-$0070`:
   - aponta o CSW (`$36/$37`, o vetor de saída de caracteres) e o KSW (`$38/$39`) para um
     pequeno carregador em `$0050`
   - os seus bytes em `$3A-$43` precisam conter, no momento em que cada um é gravado, os
     valores que o carregador da ROM está usando: A1 (`$3C`) = endereço atual `$003C`, A2
     (`$3E`) = fim `$0070`, A3 (`$40`) = início `$0036`
2. Quando a ROM imprime algo depois da carga, ela chama o CSW → o carregador roda:
   - restaura o CSW para `$FDF0` (COUT)
   - `JSR $FB74`, `JSR $EC00` (variáveis da página 1 da tela de alta resolução, a hi-res),
     `JSR $F832` (as mesmas chamadas das fitas comerciais)
   - `JSR $EDAE` uma vez para cada arquivo restante (lê o próximo arquivo da fita, para o
     endereço do seu cabeçalho)
   - `JMP start`
3. **Arquivos 2..n**: o programa e áreas extras de memória. River Raid: programa principal em
   `$4000` mais dados só de leitura em `$1200` (segmento `LODATA`) quando a área principal
   encheu. O carregador tem de caber em `$50-$70`.

### 6.3 Comportamento da fita no emulador (fork)

- F6 = Play; F2 = menu (inserir fita, "Type BASIC file", pausa); F5 = reset; F7 linhas de
  varredura; F8 tela cheia; F9 moldura do monitor.
- Heurística de carga rápida: enquanto um carregador lê a porta da fita em sequência rápida
  (< 200 ciclos de intervalo, 64 vezes), a CPU roda em velocidade máxima; volta ao normal 0,5 s
  depois que a carga para. Leituras esparsas (as varreduras do teclado também tocam no `$C010`)
  não avançam a fita.
- "Type BASIC file" digita `NEW` e depois as linhas de um `.bas`, apertando teclas só enquanto a
  ROM está varrendo o teclado de forma contínua.

### 6.4 Telas de carga e sequência de introdução (River Raid)

- **Tela de carga de graça:** ponha uma imagem hi-res no início de um arquivo da fita carregado
  em `$2000`: ela aparece linha a linha enquanto o resto carrega (o Karateka faz isso). Faça o
  carregador passar para cor antes (`STA $C050`; a ROM deixa o vídeo em mono depois do
  `LOADT`). No disco é igual: depois do `CALL 49408` o vídeo está em mono; ligue as cores no começo
  do carregador de boot, não no fim (o Sky Fox mostrava o logotipo listrado em mono por ~5 s
  enquanto a memória do jogo carregava). Apagar a página 1 antes tira a tela da ROM.
- **A ROM escreve a sua linha de status da fita** ("RIVER 0C 08 WAIT: OK") nas linhas 184-191 da
  página 1 durante o `LOADT`: mantenha o conteúdo da tela de carga acima da linha 184 e limpe
  essas linhas quando o programa começar.
- **Limite de tamanho do carregador:** o carregador de página zero (`$50-$70`) só comporta três
  `JSR $EDAE` (três arquivos depois do arquivo de página zero). Para acrescentar uma tela sem
  outro arquivo, deixe-a contígua a outro arquivo: o River Raid guarda a tela de créditos
  (`$2000-$3FFF`) e o programa (`$4000-...`) como **um só arquivo a partir de `$2000`**, e
  carrega uma segunda imagem na página 2 da hi-res (`$A000`) como arquivo próprio.
- **RAM usada só antes do jogo:** áreas que o jogo inicializa depois (as tabelas de anel e de
  "mostrado" do River Raid em `$0800-$11FF`) podem guardar dados só da introdução (o texto da
  missão e a sua fonte), carregados no mesmo arquivo que outros dados baixos (um arquivo
  `$0800-$1D94`). A página zero usada pelo jogo pode guardar variáveis da introdução.
- **Sequência usada:** créditos (mostrados durante a carga; espaço) → texto da missão rolando
  para cima (qualquer tecla pula; 2 s depois da última linha) → título com a arte da caixa e as
  opções (←/→ escolhem, caixa invertida; espaço) → jogo. Só o primeiro jogo passa por elas.
- **Convertendo uma imagem** (`tools/mkintro.py`): redimensione para 140 pares de cor por linha
  (proporção do pixel 0,914), para cada segmento de byte tente as duas paletas com difusão de
  erro e fique com a melhor, depois Floyd-Steinberg para os pixels seguintes. O pontilhado
  completo fica granulado, mas o dono do projeto preferiu assim para a arte da caixa; arte
  chapada, de desenho animado, converte muito melhor com pouco ou nenhum pontilhado. Um reforço
  de saturação/contraste muda muito o resultado: faça dele uma opção.
- **Desenhar telas com os próprios gráficos do jogo** (`tools/mktitle.py`) dá resultados nítidos
  na paleta do jogo (uma alternativa de que o dono do projeto gostou, mas não escolheu).
- **Fontes na resolução de pares:** no modo cor cada pixel da fonte tem de ser um par de pixels
  (branco = os dois pixels, verde = o pixel da esquerda), então uma fonte 5×7 dá ~22-23
  caracteres por linha (6 pares por célula), ou exatamente 20 com células de 7 pares alinhadas
  ao byte (2 bytes por caractere, uma tabela de 32 entradas transforma 5 bits da fonte nos 2
  bytes: nenhum deslocamento em tempo de execução). Minúsculas e acentos do português precisam
  de células de 9-10 linhas (acentos em cima, cedilha/descendente embaixo).
- **Rolagem vertical suave de texto** (no estilo do Karateka): copie a página uma linha de pixel
  para cima a cada passo e desenhe a nova linha de baixo a partir da fonte; mantenha um
  indicador de "vazia" por linha e pule a cópia das linhas vazias (≈2x mais rápido: 16
  linhas/s com uma cópia de 40 bytes desenrolada). Uma cópia da tela inteira custa ~110 ms.
- **O tempo de fita** cresce ~48 s por tela de 8 KB no hardware real (River Raid: 4 min 10 s no
  total); o emulador carrega em velocidade máxima, então ali são só alguns segundos reais.

### 6.4b Gravando e carregando arquivos a partir de um programa (VI65, nov/2026, `vi65-tk2000/vi65/tk.asm`)

As rotinas de fita da ROM podem ser chamadas de código de máquina (encontradas fazendo o
disassembly dos tratadores de `LOAD`/`SAVE` do BASIC, tokens 182/183, tabela de comandos em
`$C2D6`):
- **Nome**: `$0460-$0465`, 6 caracteres com o bit alto ligado, completados com `$A0` (o
  analisador do BASIC em `$EEEF` não converte nada para maiúsculas: use maiúsculas para que o
  `LOADT NOME` encontre o arquivo).
- **Gravar**: A1 (`$3C`) = início, A2 (`$3E`) = fim (inclusive), `JSR $EC9A`. Sem aviso: o REC
  já precisa estar apertado. Cabeçalho = início, fim; blocos de até 256 bytes.
- **Carregar**: nome em `$0460`, `JSR $EDAE` carrega no endereço do cabeçalho; o cabeçalho
  termina em `$0468-$046B` (início, fim). **Ponha `$FF` em `$0467` (índice do bloco) antes**: o
  `$EDAE` compara o nome antes de ler qualquer bloco, e um 0 velho ali bate na hora.
- Tudo o que a ROM imprime (nome, números de bloco, "WAIT", " OK", "ERR", o sino `$87`) passa
  pelo CSW (`$36/$37`, normalmente `$FDF0`). Um gancho no CSW mantém isso fora da tela, informa
  o resultado (sino depois de "R" = erro de checksum; depois de "K" = OK; `JSR $FBD9` com
  A=`$87` apita) e pode **mudar o lugar da carga**: quando ele é chamado com `$0467` = 0 e
  `$0460-$0465` = `$0474-$0479` (o nome desejado), o cabeçalho recém-lido está em
  `$0468-$046B` e a ROM só o copia para os seus ponteiros depois de imprimir, então novos
  valores de início/fim ali carregam o arquivo em outro lugar. Grande demais: restaure a pilha
  salva antes do `JSR $EDAE` e retorne (a fita continua tocando).
- Não há como cancelar uma carga que está esperando a fita (só com RESET).
- Velocidade: cerca de 7 s por 1K (texto; bits de 250/500 µs por metade), 10K cerca de 70 s;
  vários arquivos numa mesma fita são encontrados pelo nome, os outros são pulados.
- **Voltando ao BASIC a partir de um programa** (o `:q` do vi65): `BIT $C051`, `JSR $FE84`,
  `JSR $FE93`, `JSR $FE89`, `JSR $FC58` (HOME), `JMP ($03F2)` (a partida a quente do BASIC,
  como faz o tratador de reset em `$FA62`). `JMP ($FFFC)` também funciona, mas deixa a tela
  antiga e põe o prompt embaixo (a inicialização `$FB3B` do reset).
- O emulador (`emulador-tk2000`, commit fa64a15) grava o que os programas escrevem (as
  alternâncias de `$C020` decodificadas em blocos CT2) em `recorded.ct2`, ao lado da fita
  inserida; o harness do vi65 tem `-r FILE.ct2` e `-i TIME:FILE.ct2`.

### 6.5 Disco (a interface de disco do TK2000; Kung Fu Master, nov/2026)

- A interface de disco do TK2000 é um cartucho que copia o controlador Disk II da Apple: os
  mesmos registradores de uma Disk II no slot 1 (`$C090-$C09F`: `$C08x + $10`) e uma ROM de
  partida de 256 bytes em `$C100-$C1FF` (a PROM P5, de `apple-II/tk2000-emulator`,
  `Outros/Firmware_Disco.rom`). Dê a partida com `CALL 49408` (= `$C100`) no prompt do BASIC.
  Os mesmos disquetes de 5 1/4", 35 trilhas, 16 setores, nibbles 6-e-2, então imagens `.dsk`
  (ordem DOS), `.po` e `.nib` do Apple funcionam como imagens; o que está nelas tem de ser
  software do TK2000.
- A ROM de partida lê a trilha 0, setor físico 0, para `$0800`; o byte `$0800` = quantos setores
  ler (físicos 0..n-1 para `$0800+`), depois ela salta para `$0801` (como a do Apple).
- **Um disco DOS 3.3 do Apple não dá partida**: o seu código de partida chama o monitor do
  Apple (`$FB2F`, ...), que na ROM do TK é o meio de outro código. O TKDOS 3.3
  (`TKDOS2000.dsk`, no `data/` do emulador) é o DOS do TK2000.
- **Um disco de jogo com partida automática** (`kungfu-tk2000/src/boot.s`, `tools/mkdsk.py`):
  byte 0 = 4 (setores 0-3 = um carregador de 499 bytes); em `$0801` ele se copia para `$0400` e
  lê as trilhas 1+ com o seu próprio código no estilo da RWTS (busca uma fase de cada vez, ~13
  ms por meia trilha; campo de endereço 4-e-4 conferido contra a trilha; campo de dados com
  cadeia de XOR, checksum, os 86 valores de bits baixos pós-processados), uma página por setor:
  índice da página = (trilha - 1) × 16 + setor físico, então o arquivo só precisa do mapa P2D
  `[0,7,14,6,13,5,12,4,11,3,10,2,9,1,8,15]` (físico -> setor DOS). Depois desliga o motor
  (`$C098`) e salta para o jogo. 207 páginas (52 KB) carregam em ~2 s.
- **Qualquer jogo em fita ganha uma versão em disco de forma barata**: os mesmos binários,
  `scripts/tk2000/mkdsk.py` com os endereços de carga e de início da fita (Tennis, nov/2026: um
  arquivo em `$4000`, início em `$4800`, 40 páginas, dá partida até a tela inicial em poucos
  segundos; nada no jogo mudou). Sem uma parte sob a ROM, o carregador deixa a ROM selecionada,
  como depois de uma carga de fita.
- **Deixe `$C100-$C1FF` livre** no plano da RAM sob a ROM: com o cartucho encaixado, ele mostra
  ali a ROM de partida (o Kung Fu mudou os seus dados compactados de `$C100` para `$C200`).
  Ler `$C090-$C09F` com o motor desligado retorna 0 nos dois emuladores; escritas em `$C100+`
  no modo ROM são descartadas.
- O emulador do fork (`emulador-tk2000`, commits 5d9e25e, 5143a26) ganhou o drive em
  `src/Disk.cpp`: menu Inserir / Ejetar disco, um caminho de disco na linha de comando o
  insere, as trilhas gravadas são decodificadas de volta para o arquivo de imagem ao desligar o
  motor / mover a cabeça / ejetar, arquivos só de leitura ficam protegidos contra gravação. O
  emulador antigo para Windows (`apple-II/tk2000-emulator`) também tem o drive (mesmos
  registradores e ROM de partida); se o `kungfu.dsk` dá partida nele fica para o dono do
  projeto testar.
- A CPU do emulador teve de implementar os **opcodes não documentados do NMOS** com os seus
  tamanhos reais (o TKDOS os usa; tratá-los como NOPs de 1 byte o derrubava num BRK).
- Temporização do drive no emulador (commit 8979e29): o DOS confere se o disco ainda gira (8
  leituras de `$C08C` que diferem) antes de cada acesso; senão espera até 1 s pelo motor. O
  drive agora gira por 1 s depois do `$C088`, e um nibble repetido (sequências de `$FF` de
  autossincronismo) é lido uma vez como não pronto (bit 7 desligado). Antes disso, gravar um
  arquivo pequeno levava 40 s; agora cerca de 6 s.

### 6.6 TKDOS 3.3 a partir de código de máquina (VI65, nov/2026, `vi65-tk2000/vi65/tk.asm`)

- O TKDOS 3.3 é o DOS 3.3 do Apple nos mesmos endereços (48K: `$9600-$BFFF`, `$3D0` partida a
  quente, `$3D6` gerenciador de arquivos, `$3D9` RWTS, `$3EA` conectar ganchos = `JMP $A851`,
  `$3F2` reset -> `$9DBF`), com mensagens em português ("COMANDO ILEGAL" = NOT DIRECT COMMAND,
  "NAO HA ARQUIVO"). Detecte-o pelos JMPs em `$3D0`, `$3D3`, `$3D6`. HIMEM `$9600`; MAXFILES 1
  -> `$9AA6`.
- Os comandos são impressos pelo COUT (`$FDED`) depois de um CTRL-D (`$84`), com CR no fim,
  como `PRINT CHR$(4)"OPEN F"`. A partir de um programa, prepare antes: `JSR $FE93`,
  `JSR $FE89`, `JSR $3EA` (as rotinas de fita da ROM podem deixar o KSW alterado; o TKDOS
  guarda os ganchos que encontra como os verdadeiros); `$AA52` = 0 (estado de saída "início de
  linha", senão o CTRL-D é impresso, não interpretado); `$76` != `$FF` e `$33` != `$BE` (`>`, o
  prompt do BASIC do TK; qualquer um dos dois faz o TKDOS achar que está em modo direto:
  OPEN/READ/WRITE recusados, os outros comandos terminam no prompt do BASIC); `$D8` = `$FF`
  (ONERR) e `$9D5A` = o seu tratador de erro: o TKDOS salta para lá com o código do erro em X
  (5 END OF DATA, 6 FILE NOT FOUND...). Restaure a pilha ali. Devolva todos eles ao normal
  depois.
- Arquivos de texto: o READ faz o KSW (`$FD0C` = `JMP ($38)`) devolver os bytes do arquivo; o
  WRITE guarda o que o COUT recebe. A convenção do BASIC é bit 7 ligado, `$8D` depois de cada
  linha, `$00` termina o arquivo. O OPEN cria um arquivo que não existe (use VERIFY para testar
  se um arquivo existe); o WRITE por cima de um arquivo antigo deixa o fim antigo: OPEN, DELETE,
  OPEN antes de gravar.
