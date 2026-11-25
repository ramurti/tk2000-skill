# Portando um jogo de Apple II (a partir de uma imagem .dsk)

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. As pastas de jogo citadas (como `kungfu-tk2000`) são projetos do autor, não publicados; as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## 9. Portando um jogo de Apple II

Feito uma vez: Kung Fu Master (Data East 1985, Apple II pela Berkeley Softworks), a partir de
um `.dsk` DOS 3.3 crackeado, em um dia (09/11/2026), em `kungfu-tk2000` (o README dele
documenta o projeto; lições na §16). Abordagem: **rodar o código do original sem mudanças,
remontado para o mapa de memória do TK2000, com o hardware da Apple trocado por uma pequena
camada** (como a §8.3 para o 2600).

### 9.1 Diferenças que importam

- CPU, clock e a organização dos bytes da tela de alta resolução (hi-res) são os mesmos; a
  página 2 da hi-res fica em `$A000` em vez de `$4000` (realoque os endereços da página 2 e
  qualquer código/dado que more em `$A000-$BFFF` no Apple).
- As cores são diferentes (§3.2): os mesmos bytes mostram o laranja do Apple como vermelho no
  TK, o azul como ciano, o violeta como verde, o verde como azul. O dono do projeto aceitou a
  arte do jogo do jeito que sai (sem remapear).
  - **Remapear costuma ser barato** (Sky Fox, nov/2026): o verde do Apple (pixel em
    coluna ímpar, paleta 0) vira azul no TK2000 porque os pares do TK começam em x par; o azul do
    Apple (coluna par, paleta 1) vira ciano. Para o TK2000 mostrar a cor certa, troque os bytes
    de preenchimento: **verde no TK = os bytes do violeta do Apple** (`$55,$2A` na coluna par,
    ímpar), **azul no TK = os bytes do verde do Apple** (`$2A,$55`), ambos com bit 7 = 0. Como
    verde e azul estão **na mesma paleta** do TK2000, um chão verde sob um céu azul não tem
    conflito de cor no horizonte (no Apple eles estão em paletas diferentes). Laranja -> vermelho
    não precisa de troca (mesma posição, paleta 1). Violeta não existe no TK2000: é uma escolha
    (vermelho, ciano, azul...). Na prática: ache as constantes/tabelas de preenchimento do jogo
    (chão, céu, painéis) e troque-as; mostre ao dono do projeto o original, "mesmos bytes" e
    "bytes trocados" lado a lado antes de escolher. `scripts/apple/recolor.py` refaz uma tela
    inteira assim (pixel a pixel, paleta de cada byte por maioria) e `tkview.py` desenha as
    versões lado a lado: servem de prévia, não de implementação.
- Não há modo texto: as chaves de modo do Apple em `$C050-$C057` (texto/gráfico/misto/página)
  significam outras coisas aqui (`$C050/$C051` = cor/mono, `$C052/$C053/$C056/$C057` = fita).
  Troque-as por NOP e ligue cor ou mono você mesmo; uma tela de texto que o jogo desenha em
  hi-res fica melhor em mono (branco, sem franjas de cor).
- Não há o latch de teclado em `$C000`: monte um a partir da matriz (§4). Não há paddles nem
  porta de jogos: gere os valores dos paddles e os botões a partir de teclas.
- O alto-falante em `$C030` é o mesmo: código de bipe do Apple funciona como está (as
  temporizações em ciclos são as mesmas).
- Os pontos de entrada da ROM são completamente diferentes: qualquer chamada ao monitor ou ao
  Applesoft do Apple precisa ser trocada.
- Jogos de 64K podem usar a RAM sob a ROM (`$C05A/$C05B` aqui, não o `$C080-$C08F` da language
  card do Apple).
- Disco: o TK2000 tem uma interface compatível com a Disk II (§6.5), mas o DOS/RWTS e o
  carregador do jogo têm de ser código do TK2000; fita também funciona (§6.2).

### 9.2 Passos que funcionaram (Kung Fu Master)

1. **Ler o disco.** `tools/dos33.py`: o catálogo DOS 3.3 e os arquivos binários (cabeçalho de
   4 bytes: endereço, tamanho). Kung Fu: arquivos A..O, carregados pelo nome pelo próprio
   carregador do crack em `$BB00` (A = letra do arquivo). Mapeie qual arquivo carrega onde e
   quando (uma tabela no README).
2. **Dar partida nele num pequeno Apple II.** `tools/a2boot.py`: py65 + 64K + language card +
   uma Disk II alimentada com nibbles 6-e-2 do `.dsk` + latch de teclado, paddles, botões; sem a
   ROM do monitor (`$D000+` lê como RTS). Teclas programadas e um joystick que anda e atira.
   Ele registra os setores e arquivos carregados, a E/S usada, e salva a memória no início do
   jogo (`*-start.bin`) e os endereços executados por arquivo (`*-code.txt`). Rode uma
   demonstração, um jogo e cada andar (`-p PC:ADDR:VALUE` altera o número do andar quando o
   código de preparação é alcançado), para ter cobertura.
3. **Fazer o disassembly.** `tools/disa2.py`: código = o executado + rastreio estático a partir
   dele, o resto `.byte`; E/S do Apple pelo nome; rótulos. `make check`: cada arquivo remonta
   em bytes idênticos.
4. **Realocar.** Troque as áreas de 8K: a página 2 do Apple (`$4000-$5FFF`) vai para
   `$A000-$BFFF`, o que o Apple tem em `$A000-$BFFF` (fim do código principal, os overlays, o
   carregador) vai para `$4000-$5FFF`. Os rótulos se mudam sozinhos; endereços **montados em
   tempo de execução** não, então encontre-os (todos em `tools/relocs.py`, cada um com um
   comentário):
   - deslocamentos de página: o jogo desenha na página 1 + `$20` para a página 2 (`$F4`): vira
     `$80`;
   - bytes altos em imediatos e tabelas: `tools/taint.py` roda o jogo rastreando de onde veio
     cada byte e informa as origens de cada acesso indireto às áreas trocadas;
     `tools/records.py` decodifica os registros de objetos do jogo (gráficos dos quadros,
     tratadores); `tools/immscan.py` lista os padrões `LDA #hi / STA` em código que nunca rodou:
     confira cada um pelo uso (vários "ponteiros" eram coordenadas ou padrões);
   - o gerador de números aleatórios lia bytes do próprio código do jogo, que a realocação
     muda: dê a ele uma cópia dos bytes originais.
5. **Conferir em lockstep** (execução lado a lado, passo a passo). `tools/lockstep.py` roda o
   original (com partida pelo disco) e o porte realocado instrução por instrução com a mesma
   entrada; ele para no primeiro PC ou byte de memória diferente. 0 diferenças na
   demonstração, no jogo e em todos os andares. Ele só prova os caminhos que percorreu: o SPACE
   do menu de opções nunca foi apertado ali e escondia ponteiros de texto não realocados (um
   travamento que o dono do projeto encontrou).
6. **Trocar o hardware** (`src/tk.s` em `$5B00`, onde ficava o carregador do Apple, para que os
   próprios `JSR $BB00` de carga de arquivo do jogo caiam nele depois da realocação): uma tabela
   de saltos para a qual as instruções de E/S do original são desviadas por padrão de bytes
   (`LDA $C000` -> `JSR KbdRead`, `LDA $C010` / `STA $C010` -> `JSR KbdStrobe`, `LDA $C061` ->
   `LDA btn0`, a rotina dos paddles -> `JMP Paddles`, chaves de modo -> NOPs):
   - **LoadFile**: os overlays e as imagens que o jogo carrega durante a partida ficam
     compactados com LZ (`tools/lz.py`) na RAM sob a ROM (`$C200-$FFFF`) e são descompactados
     quando pedidos;
   - **KbdRead**: um latch no estilo do Apple (código | `$80` até o strobe, uma tecla segura
     uma vez só) a partir de uma tabela de teclas da matriz; CTRL via `$C05F`;
   - **Paddles**: setas -> valores dos paddles, demorando tanto quanto o laço de temporização
     do original, para que a velocidade do jogo não mude; SPACE / Z = botões.
7. **Montar a imagem a partir do próprio início do original.** `tools/mkimage.py` dá partida no
   disco até o momento em que o jogo começa, pega aquela memória e os registradores, realoca,
   coloca o código do TK2000 por cima, compacta os overlays e a memória baixa (`$0000-$07FF`,
   usada pelo carregador da fita) e grava a fita (programa em `$0800-$9FFF` com a imagem de
   título em `$2000` aparecendo enquanto carrega, dados compactados em `$C200+`). `Start`
   descompacta a memória baixa, restaura os registradores e entra no jogo onde o carregador do
   Apple entrava.
8. **Testar no emulador de verdade, sem janela** (harness da §10): capturas de tela da
   demonstração, do menu, do jogo, e despejos de memória para o estado (vidas, energia, tempo,
   bits de direção).
9. **Melhorar, em pequenos passos que o dono do projeto aprova** (§16): menu, controles, sons,
   música, nunca morrer, uma versão em disco (§6.5).


### 9.3 O AppleWin como referência (Sky Fox, nov/2026)

O Apple II do py65 (`a2boot.py`) é o que permite o lockstep, mas pode errar (disco, temporização,
latch de teclado). Quando o original fizer algo estranho no py65 (travar, desenhar lixo), rode-o no
**AppleWin para Linux** antes de depurar o jogo: no Sky Fox o py65 travava 16 s depois da decolagem
e o AppleWin voou normalmente, o que provou que o defeito era do simulador.

- Fonte: https://github.com/onionmixer/AppleWin (versão do audetto com um servidor de depuração
  HTTP: `/api/info` nas portas 64501, `/api/registers` 64503, `/api/read?addr=HEX&len=256` 64504).
  Pacotes (Debian/Ubuntu/Mint): `ninja-build libncurses-dev libevdev-dev libsdl2-image-dev
  libslirp-dev libboost-program-options-dev libyaml-dev libminizip-dev libpcap-dev` (+ `libsdl2-dev`,
  `libgles-dev`, `cmake`, `xxd`). Compilar só o `sa2`:
  `git submodule update --init --recursive; git apply .../scripts/apple/applewin-key.patch;
  mkdir build; cd build; cmake -G Ninja -DBUILD_SA2=ON -DCMAKE_BUILD_TYPE=RELEASE ..; ninja sa2`
  (o alvo completo falha num teste; o patch põe o `<cstdint>` que falta no GCC 13).
- **Teclas**: no Linux o `KeybQueueKeypress` é um stub vazio; o teclado real é o
  `addKeyToBuffer` (`linux/keyboardbuffer.h`). O patch expõe `/api/key?code=HEX`.
  O crack do Sky Fox espera uma tecla no logotipo (`LDA $C000 / BPL`): o py65 passava direto
  porque o latch começa com uma tecla.
- `scripts/apple/awrun.py DISK.dsk OUT -t 200 -s 5 -k 8:sp --wav`: Apple II+ (`-r "Configuration.Apple2
  Type=1"`), `--headless --fixed-speed` (sem `--fixed-speed` ele corre à frente das capturas, e as
  consultas HTTP às vezes caem: repita-as), config própria (`-c`), capturas, despejos e o WAV
  do alto-falante (`--wav-speaker`: os sons originais para comparar com as opções do TK2000).
- **Estados salvos como ponto de partida** (`awrun.py --snap SEGUNDOS`, `sfboot.py -A`,
  `awcmp.py A.yaml B.yaml`): o py65 partindo de um estado do AppleWin fica **idêntico ciclo a
  ciclo** a ele (registradores, RAM, language card) em todo trecho sem leitura de disco. Nos trechos
  com leitura de disco os dois se separam, porque o disco do `a2boot.py` não tem a temporização do
  Disk II real (fase de rotação, tempo de passo da cabeça). No Sky Fox o jogo é determinístico, mas
  as cargas durante o voo dependem do tempo: do boot no py65 ele travava 16 s depois da decolagem;
  partindo do estado do AppleWin em 155 s ele voou normalmente. Lição: **para comparar com o
  original, comece do estado do AppleWin logo depois da última carga de disco**, não de um boot no
  py65. Um estado só pode ser carregado com o motor do disco desligado (escolha outro segundo).
  Atenção: uma janela do AppleWin aberta ocupa as portas 64501-64505 e as consultas vão para ela
  (o `awrun.py` recusa rodar nesse caso).
- **Joystick**: sem controle conectado, o `sa2` não tem `Paddle::instance` e lê os dois paddles
  como 255 (joystick no canto): menus guiados pelo joystick andam sozinhos (no Sky Fox o menu de
  cenários trocava sem parar). O patch põe um joystick virtual centrado, controlado por `/api/joy`
  (`awrun.py -j 30:x=255 -j 31:x=128 -j 40:b0=1 -j 41:b0=0`; o `awrun.py` espaça eventos seguidos
  em 0,3 s emulados, senão apertar e soltar caem no mesmo instante).
- Não substitui o py65: não há passo a passo controlado de fora, então o lockstep continua no py65.
  Use-o para saber o comportamento certo e para comparar a memória (código que o jogo reescreve
  difere por momento: compare páginas que ficam estáveis entre três despejos seguidos).

### 9.4 Lockstep a partir de estados do AppleWin (Sky Fox, nov/2026)

`scripts/apple/sflockstep.py` roda o original e o porte relocado lado a lado a partir de um estado
salvo do AppleWin (não do boot), com `sfrelocs.py` (a tabela de correções) e `dispkg.py --tk` (as
unidades na versão TK2000). Aprendido:
- **Traduza o estado, não só o código**: endereços de retorno na pilha (reconheça pelo JSR antes do
  endereço apontado), operandos que o jogo já reescreveu, e código que o jogo instalou em tempo de
  execução (os buracos da tela) também precisam do XOR `$E0`.
- **Confira o ponteiro da pilha a cada instrução**: um byte de código sobrescrito por um desenho com
  endereço não relocado aparece primeiro como pilha diferente, não como PC diferente.
- **A variável de página não é só somada**: o mesmo `$00/$20` serve de índice (`asl a` → `$00/$40`);
  com `$80` no TK2000, `lsr a` dá o mesmo; dois `adc $20` viram `nop / adc tabela,x`.
- **Nas áreas de tela, código só nos buracos**: o rastreio estático do desmontador toma bytes de
  imagem por código e "reloca" figuras (`disa2.disassemble(..., allow=)`).
- **Figuras podem apontar para dentro de tabelas** (uma "figura" desenhava os bytes da própria tabela de
  ponteiros): ao relocar a tabela, aponte essa figura para uma cópia dos bytes originais.
- **Varra o disco pelo padrão, não espere o lockstep**: `lda #hi / sta $31`, `lda #hi / sta operando`,
  `adc #$20` depois da tabela de linhas: cada padrão achado uma vez costuma ter vários irmãos.
- Código que não rodou nas medições fica como dado e não é relocado: o lockstep o encontra quando
  roda; acrescente o endereço como ponto de entrada (`dispkg.SEEDS`).

### 9.5 Do lockstep ao disco que roda no TK2000 (Sky Fox, nov/2026)

- **Cobertura por fase**: código que só roda numa fase não medida fica como dado e não é relocado.
  `scripts/apple/execpcs.py` registra as instruções executadas por unidade a partir de estados do
  AppleWin, reconhecendo o pacote de cada área depois de cada carga; use como pontos de entrada.
  O desmontador aceita o trecho reto de um ponto de entrada dado, mesmo se um desvio dele for ruim.
- **Parâmetros embutidos depois do JSR** (a sub-rotina tira o retorno da pilha): ensine o tamanho ao
  desmontador (fixo ou lido dos próprios bytes, ex.: um texto com o tamanho na frente).
- **Código guardado como dado**: trechos copiados para outro endereço antes de rodar, e código de
  buraco embutido em imagens (a rotina de figuras copia linhas inteiras, buracos inclusive): varra os
  dados atrás de trechos que decodificam limpo até um JMP para um buraco e reloque-os.
- **O carregador do jogo grava as páginas onde o Apple as quer**: no TK2000 o destino das páginas
  `$40-$5F`/`$A0-$BF` também troca; desvie o `sta` do ponteiro de destino para a camada.
- **Leitura de E/S sem dispositivo dá `$FF` no emulador**: botões do Apple "sempre apertados" e o
  temporizador do joystick que não termina travam o jogo; dê ao porte uma entrada neutra na camada
  antes de escolher os controles.
- **Controles pelo teclado do TK2000** (Sky Fox): troque cada leitura de `$C000`/`$C061`/`$C062`
  por `jsr` para a camada (mesmo tamanho; a rotina varre a matriz e devolve A ou os flags do BIT).
  Faça primeiro um teste rápido com todas as linhas (KBOUT = `$FF`): os laços de espera do jogo
  leem o teclado milhares de vezes e uma varredura completa a cada leitura os deixaria lentos.
  Joystick analógico pelas setas em rampa (o dono do projeto escolheu entre tudo-ou-nada, rampa e
  meio/inteiro com SHIFT); o menu precisa da seta segurada ~1 s.
- O lockstep não roda as cargas no porte: um erro no destino das páginas ou no carregador só aparece
  no emulador do TK2000 (harness com ponto de parada por PC e vigia de byte).

## 16. Lições do porte do Kung Fu Master (`kungfu-tk2000`, nov/2026)

O primeiro porte de Apple II (§9): um disco DOS 3.3 crackeado, o código original rodando sem
mudanças.

- **Prefira uma cópia crackeada**: seus arquivos são binários DOS 3.3 simples e seu carregador
  é simples; senão a proteção contra cópia seria o primeiro problema.
- **O lockstep só prova o que percorreu**: dois bugs chegaram ao dono do projeto em caminhos
  que ele nunca tomou (os textos das opções do menu: tabelas de ponteiros só em parte
  realocadas; setas mortas durante o jogo). Depois do lockstep, passe por cada opção de menu e
  cada tecla no emulador de verdade.
- **Calibração pulada**: a tela de calibração do joystick do jogo, pulada com uma tecla,
  deixava os limites dos paddles em 0, e assim nenhuma direção era registrada; pré-defina-os na
  imagem (centro 45; limites 22, 45, 86, `$FF`). Confira os controles pela **memória** (os bits
  de direção do jogo), não por capturas de tela: um andar que rola faz o jogador parecer parado.
- **Também não confie numa captura de tela para o som**: a "música da demonstração" que o dono
  do projeto ouviu era o bipe da ROM. O original do Apple não tem efeito sonoro nenhum, só duas
  músicas (o tocador em L875C).
- **Alterando código**: um disassembler que gera `.byte` para dados ainda precisa gerar os
  bytes de opcode alterados quando uma alteração cai numa instrução com imediato (bug do
  `disa2.py`, corrigido).
- **Espaço**: a camada do TK no antigo lugar do carregador (`$5B00-$5DFF`) encheu rápido; o
  código extra (efeitos sonoros, música) foi para a RAM sob a ROM depois dos dados compactados
  (`SFX_AT`, passado ao montador pelo build), alcançado pela tabela de saltos.
- **Ganchos para melhorias** (`relocs.improvements`): troque uma instrução de 3 bytes num
  evento conhecido do jogo por um `JSR` para a tabela de saltos; a rotina faz o seu trabalho
  extra e depois a instrução trocada (ou `JMP` para o destino do `JSR` trocado). Eventos usados:
  um golpe acerta (ruído de acerto, ~5 ms), o jogador é atingido (baque), o jogador morre (tom
  descendente, o jogo está parado de qualquer jeito), um chefe é derrotado (fanfarra), o tempo
  acaba, o fim do andar (a callback que a contagem de pontos chama, `$851F` -> próximo andar), o
  topo do laço principal (a cada quadro).
- **Efeitos sonoros que o original não tem**: rajadas curtas (5-6 ms) durante o jogo não são
  percebidas como atraso; sons mais longos só onde o jogo para de qualquer jeito (morte, chefe
  derrotado). O dono do projeto gostou de todos. Prévias: WAVs renderizados a partir dos
  cliques do alto-falante registrados.
- **Música a partir de um MIDI** (`tools/midi2tk.py`): uma melodia de semicolcheias -> passos
  (número da nota ou pausa), por nota um atraso e uma contagem de meios períodos para um laço de
  7 ciclos, transposta uma oitava acima (tons de bipe soam melhor mais agudos). Tocada na
  primeira tela da demonstração até o SPACE, e a cada novo andar até uma tecla de movimento; o
  jogo espera enquanto isso. O dono do projeto escolheu 10% mais rápido que o andamento do MIDI
  (passos de 136 ms).
- **Teclas do menu**: as setas do TK2000 servem também de teclas do menu enquanto o overlay do
  menu está carregado (DOWN = RETURN = próxima opção, LEFT/RIGHT = SPACE = mudar); RETURN
  sozinho mantém o último nível. O modo KEYBOARD foi feito para se comportar como o JOYSTICK
  (os dois são as setas no TK2000). Dois jogadores mantidos (eles se revezam; um joystick
  basta).
- **Nunca morrer** (CTRL-N, ideia do dono do projeto, para explorar todos os andares): pula a
  perda de energia e a morte por fim de tempo; um bipe de duas notas, subindo/descendo,
  confirma; a linha de ajuda do menu, liberada ao remover o CTRL-S (som sempre ligado: "as
  pessoas querem nostalgia"), mostra isso. Texto nos próprios códigos de caractere do jogo
  (dígitos 0-9, letras a partir de 10).
- **Distribuição**: `dist/kungfu.ct2` e `dist/kungfu.dsk` no repositório do projeto (privado);
  um `.wav` da fita para o hardware real fica só local (escolha do dono do projeto).
  `INSTRUCTIONS.txt` explica a carga, as teclas e os golpes.
- **A tela de calibração do joystick removida** (nov/2026): inútil no TK2000 (valores fixos dos
  paddles a partir das setas, limites pré-definidos na imagem), então a entrada do G salta
  direto para a demonstração; o espaço dela no overlay guarda a carta do arcade (Silvia
  sequestrada) desenhada com a própria fonte do jogo (duas marcas que faltavam emprestadas a
  códigos de fonte não usados durante o desenho), mostrada depois do menu de opções cada vez que
  um jogo começa (gancho no `LDA #'G' / JSR load` do menu). Mantenha a tela do menu em mono
  enquanto o overlay carrega, senão ela pisca franjas de cor.
- Em aberto: um lampejo embaralhado na página 2 enquanto o painel de placar recarrega depois de
  uma vida perdida; a imagem dos créditos (O) não cabe sob a ROM; uma versão em disco baseada
  no TKDOS (não agora).
