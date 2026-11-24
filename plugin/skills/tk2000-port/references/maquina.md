# A máquina TK2000: memória, E/S, vídeo, teclado, som

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. Pastas com nome de projeto (como `vi65-tk2000` ou `enduro-tk2000`) são projetos do autor (os de jogos não são publicados; podem não existir em outra máquina); as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## 1. Visão geral da máquina

| Item | Valor |
|---|---|
| CPU | 6502 (NMOS), 1.022.727 Hz (o mesmo clock do Apple II NTSC) |
| RAM | 48K em `$0000-$BFFF`; no modelo de 64K, mais 16K sob a ROM em `$C100-$FFFF` |
| ROM | imagem de 16K para `$C000-$FFFF` (`$C000-$C0FF` é E/S): Monitor + BASIC derivado do da Microsoft, com mensagens em português ("NAO HA 64K DE MEMORIA", "ERRO", "SINTAXE") |
| Vídeo | só alta resolução (hi-res) (não há modo texto; a ROM desenha o texto em hi-res): 280 × 192, duas páginas em `$2000` e `$A000` |
| Som | alto-falante de 1 bit, invertido por qualquer acesso a `$C030-$C03F` |
| Entrada | matriz de teclado (8 linhas × 6 colunas) varrida por software; sem latch ASCII |
| Armazenamento | fita cassete (imagens CT2 no emulador) |
| Timers / interrupções | **nenhum utilizável**: sem timer, sem sinal de retraço vertical, sem interrupção de varredura |

Consequências que moldam todo porte:

- Não há como saber onde está o feixe: o tearing (imagem rasgada) não pode ser evitado por
  temporização. Use troca de páginas (as duas páginas hi-res) para movimento suave.
- Não há timer: a velocidade do jogo tem de ser controlada contando os ciclos de CPU que o
  programa gasta (veja §7, "Ritmo de quadros").
- Não há hardware de graça: sprites, colisões, rolagem, timbres de som... tudo em software.

## 2. Mapa de memória e E/S

### 2.1 Memória

| Faixa | Uso |
|---|---|
| `$0000-$00FF` | página zero (a ROM usa boa parte dela; um jogo que assume a máquina pode usar toda) |
| `$0100-$01FF` | pilha |
| `$0200-$03FF` | buffer de entrada e variáveis da ROM (livres quando o jogo assume a máquina) |
| `$0400-$07FF` | usada pela ROM/BASIC (a ROM acessa `$0435`); livre quando o jogo assume a máquina (não usada pelo River Raid) |
| `$0800-$1FFF` | RAM livre (River Raid: tabelas em `$0800-$11FF`, dados só de leitura em `$1200-$1FFF`) |
| `$2000-$3FFF` | página 1 de hi-res |
| `$4000-$9FFF` | RAM livre, 24K (o código e os dados do River Raid são carregados aqui) |
| `$A000-$BFFF` | página 2 de hi-res |
| `$C000-$C0FF` | E/S (veja abaixo) |
| `$C100-$FFFF` | ROM, ou RAM no modelo de 64K (`$C05B` seleciona a RAM, `$C05A` a ROM); `$C100-$C1FF` é a ROM de boot da interface de disco enquanto esse cartucho está encaixado (§6.5) |

Notas:
- A página 2 de hi-res fica em `$A000` (Apple II: `$4000`). Um programa que usa as duas páginas
  tem a faixa contínua `$4000-$9FFF` (24K) mais `$0400-$1FFF` abaixo da página 1.
- Bancos de 64K (`$C05A`/`$C05B`), como emulado (`Rom.cpp`):
  - leituras de `$C100-$FFFF` vêm da ROM ou da RAM, conforme o último acesso a `$C05A`/`$C05B`
  - **escritas sempre vão para a RAM** (então dá para copiar código para baixo da ROM com a ROM
    ativa)
  - o reset seleciona a ROM
  - se um jogo roda com a RAM selecionada, os vetores de IRQ/NMI/RESET em `$FFFA-$FFFF` vêm da
    RAM
  - o Karateka verifica essa RAM ("NAO HA 64K DE MEMORIA" se ela faltar); o fork do emulador a
    implementa
- Um jogo pode passar para a RAM depois de carregar, para ganhar 16K, mas aí não pode chamar
  rotinas da ROM sem voltar para ela.

### 2.2 Endereços de E/S (dos registros no barramento do emulador)

| Endereço | Leitura / escrita | Função |
|---|---|---|
| `$C000-$C00F` | escrita | KBOUT: seleção de linha do teclado (bit n = linha n) |
| `$C010-$C01F` | leitura | KBIN: colunas do teclado (bits 0-5) **combinadas por OR** com a entrada do cassete (bit 7) |
| `$C020-$C02F` | leitura | entrada do cassete (bit 7) |
| `$C030-$C03F` | leitura ou escrita | inverte o alto-falante |
| `$C050` / `$C051` | acesso | vídeo colorido / vídeo monocromático |
| `$C052`/`$C053`, `$C056`/`$C057` | acesso | registrados no dispositivo de fita no emulador (provavelmente motor/relé do cassete; não verificado) |
| `$C054` / `$C055` | acesso | mostra a página 1 de hi-res (`$2000`) / a página 2 (`$A000`) |
| `$C05A` / `$C05B` | acesso | ROM / RAM em `$C100-$FFFF` (modelo de 64K) |
| `$C05E` / `$C05F` | acesso | linha da tecla CTRL desligada / ligada na leitura do teclado |
| `$C090-$C09F` | acesso | interface de disco (uma cópia da controladora Disk II, §6.5): fases `$C090-$C097`, motor `$C098/$C099`, drive `$C09A/$C09B`, Q6 `$C09C/$C09D`, Q7 `$C09E/$C09F` |

O barramento do emulador combina por OR os resultados dos dois dispositivos registrados num
endereço (teclado e fita dividem `$C010-$C01F`). Os soft switches reagem a leituras e escritas
(`sta $C054` funciona; `lda`/`bit` também).

## 3. Vídeo

### 3.1 Organização (idêntica à hi-res do Apple II)

- 192 linhas × 40 bytes. Cada byte guarda 7 pixels: o bit 0 é o mais à esquerda, o bit 6 o mais
  à direita; **o bit 7 é o bit de paleta** (não é pixel).
- Endereço da linha (deslocamento a partir da base da página, `$2000` ou `$A000`):
  `((y & 7) << 10) | (((y >> 3) & 7) << 7) | ((y >> 6) * 40)`.
  Mantenha tabelas `LineLo`/`LineHi` de 192 entradas para a página 1 e faça OR do byte alto com
  `$80` para a página 2 (`$20xx | $80 = $A0xx` — funciona porque a página 1 é `$2000-$3FFF` e a
  página 2 `$A000-$BFFF`).
- O byte baixo da base de uma linha é no máximo `$D0`, então somar uma coluna (0..39) a ele nunca
  gera vai-um: indexe ponteiros como `(ptr),y` com `ptr = linha + primeira coluna`.
- 40 × 192 = 7.680 bytes por página. Reescrever uma página inteira custa da ordem de 80.000
  ciclos (≈ 80 ms): **redesenhar tudo a cada quadro é impossível nas taxas de quadros de um
  jogo**. Redesenhe só o que mudou (renderização por diferença).

### 3.2 Cores (como emuladas em `Video.cpp`; hardware real não conferido)

O emulador desenha os pixels **em pares a partir de x = 0**: pixels (0,1), (2,3), ..., (278,279).
A cor do par depende dos seus dois bits e do bit de paleta (bit 7) do **byte que contém o pixel
esquerdo** do par:

| par (esquerdo, direito) | paleta 0 (bit 7 = 0) | paleta 1 (bit 7 = 1) |
|---|---|---|
| 0 0 | preto | preto |
| 1 1 | branco | branco |
| 1 0 | verde | ciano |
| 0 1 | azul | vermelho |

Consequências:
- A resolução efetiva de cor é 140 × 192. Um par pode ficar entre dois bytes (pixels 6 e 7 de
  um grupo de 14 pixels: bit 6 do byte n e bit 0 do byte n+1); a paleta dele vem do byte da
  esquerda.
- **Isso é diferente do Apple II** (violeta/verde, azul/laranja, cores de artefato que dependem
  da paridade absoluta da coluna, deslocamento de meio pixel da paleta 1). Os gráficos do Apple
  II não aparecem com as mesmas cores no TK2000: as cores precisam ser remapeadas. O verde do
  Apple sai azul, e o azul sai ciano; para ter verde e azul no TK use os bytes do violeta e do
  verde do Apple, respectivamente (`apple-ii.md` §9.1). Verde e azul ficam na mesma paleta
  (0), então podem se encostar no mesmo byte sem franja.
- Conflito de cor: o bit de paleta vale por byte (7 pixels). Vermelho e ciano precisam da paleta
  1, verde e azul da paleta 0: um pixel vermelho de sprite deixa vermelha a água azul em volta
  (no mesmo byte), e ciano a terra verde. Branco e preto independem da paleta. No River Raid
  usamos só a paleta 0 na área de jogo (branco, preto, verde, azul) e só a paleta 1 na barra de
  status, onde tudo em volta é branco ou preto (o ponteiro vermelho do combustível). Mostre as
  opções ao dono do projeto (o `tools/colortest.py` do River Raid desenha esquemas lado a lado)
  antes de escolher.
- Pixels isolados aparecem como cores, não como branco: para desenhar branco, ligue **os dois**
  pixels de um par; sprites e fontes devem ser desenhados com pares de pixels em posições x pares.
- Franjas: um padrão cujos pares estão desalinhados em um pixel (x ímpar) mostra franjas de cor.
  Mantenha sprites, dígitos e caixas em x de pixel par; ponha glifos alinhados por byte em
  **colunas de byte pares** (o byte n começa no pixel 7n, que só é par quando n é par). River
  Raid: o dígito dos jatos de reserva no byte 11 mostrava franjas azuis/verdes; passou para o
  byte 10.
- Bordas preto/branco entre uma área de cor preenchida e o fundo: o par da borda pode pegar uma
  cor inesperada; o River Raid corrige as margens do rio ligando o bit do pixel esquerdo de uma
  coluna ímpar a partir do vizinho da esquerda ("edge fix").
- O modo mono (`$C051`) mostra os pixels individualmente, em branco.
- O emulador desenha a tela a partir da memória uma vez por bloco emulado (sem temporização de
  varredura), então o tearing no emulador não parece exatamente com o do hardware.

### 3.3 Técnicas de desenho que funcionaram

- **Tabelas de consulta por byte**: um pixel do playfield do 2600 → um byte do TK2000 (7
  pixels); os 40 pixels de playfield de uma linha correspondem exatamente aos 40 bytes (280
  pixels). A posição x do 2600 (0..159) corresponde a pixels do TK2000 × 7/4.
- **Renderizador por diferença**: guarde, por página, o que cada linha mostra no momento (River
  Raid: byte PF1/PF2 e marca da estrada por linha, por página) e só reescreva os bytes que
  diferem. Pré-calcule, para cada valor de byte do playfield, os bytes de saída (8 por lado).
- **Sprites pré-deslocados**: 7 cópias por sprite (deslocamento 0..6 dentro do primeiro byte),
  geradas por uma ferramenta em Python a partir dos gráficos originais; linhas aparadas; cor por
  linha (branco = ORA, preto = AND NOT, verde = limpar e depois ligar o pixel esquerdo de cada
  par com uma máscara de paridade).
- **Restauração do fundo**: para apagar um sprite, recalcule os bytes do fundo a partir do
  estado "mostrado" (cache de linhas: linhas consecutivas com o mesmo fundo reaproveitam os
  bytes calculados).
- **Compor numa passada só**: objeto em movimento = uma passada sobre a união dos retângulos
  antigo e novo (fundo + sprite juntos), em vez de apagar + desenhar (menos cintilação, menos
  escritas).
- **Buffer duplo**: desenhe na página de trás e depois troque com `$C054`/`$C055`. Todo estado
  por página (linhas mostradas, retângulos dos sprites, conteúdo da barra de status) tem de ser
  guardado **por página**.
- Laços internos desenrolados com pontos de entrada calculados (`jmp (vector)`) para larguras
  variáveis.
- Recorte os sprites nas linhas da área de jogo; as linhas da barra de status nunca são tocadas
  por sprites.

## 4. Teclado

Matriz (de `Keyboard.cpp`): escreva uma máscara de linha em KBOUT (`$C000`), leia KBIN
(`$C010`), teste o bit da coluna. Linha n = bit n de KBOUT; coluna n = bit n de KBIN.

```
                 KBIN bit:  0     1   2   3   4   5
KBOUT bit 0 ($01):          SHIFT B   V   C   X   Z
KBOUT bit 1 ($02):          (*)   G   F   D   S   A
KBOUT bit 2 ($04):          SPACE T   R   E   W   Q
KBOUT bit 3 ($08):          LEFT  5   4   3   2   1
KBOUT bit 4 ($10):          RIGHT 6   7   8   9   0
KBOUT bit 5 ($20):          DOWN  Y   U   I   O   P
KBOUT bit 6 ($40):          UP    H   J   K   L   :
KBOUT bit 7 ($80):          RETURN N  M   ,   .   ?
```
(*) A tabela do emulador mostra SHIFT na linha 1, coluna 0, mas o código dele só devolve SHIFT
quando KBOUT é exatamente `$01` (linha 0). CTRL: habilite com `$C05F` (desabilite com `$C05E`);
então o bit 0 de KBIN lê a tecla CTRL.

Ler várias teclas ao mesmo tempo funciona (cada tecla é um teste separado de linha/coluna); o
River Raid lê as setas, o espaço e o '.' a cada quadro:

```
KeyRow:  .byte $80, $04, $10, $08, $20, $40     ; '.', SPACE, RIGHT, LEFT, DOWN, UP
KeyMask: .byte $10, $01, $01, $01, $01, $01
        ldx #5
@key:   lda KeyRow,x
        sta $C000
        lda $C010
        and KeyMask,x
        cmp #1          ; C = apertada
        rol keys
        dex
        bpl @key
        lda #0
        sta $C000
```

Notas:
- Sem latch de tecla apertada, sem código ASCII: programas de Apple II que leem `$C000` / limpam
  com `$C010` precisam ser reescritos.
- O bit 7 de `$C010` é a entrada do cassete: mascare-o.
- Mapeando joysticks: setas = direções. O dono do projeto prefere o **espaço** como botão de tiro
  (a tecla '.', indicada como FIRE no nosso README, também funciona).
- O efeito fantasma (ghosting) do hardware real com 3 ou mais teclas não foi verificado.
- **Digitar texto** (editor VI65, `vi65-tk2000/vi65/tk.asm`): o SHIFT é lido com KBOUT = `$01`
  sozinho, coluna 0; o CTRL com `$C05F` ligado e KBOUT = 0. Os símbolos das teclas, como o
  emulador os mapeia: SHIFT + 1..0 = `! " # $ % & ' ( ) *`, SHIFT + I O P = `- = +`, K L =
  `^ @`, `:` = `;`, `,` `.` `?` = `< > /`. Não há ESC, nem `[ ] { } \ | ~ _` e crase; não há
  tecla de minúsculas (mapeie as letras simples para minúsculas se o programa precisar das duas).
  A repetição automática tem de ser feita em software (conte chamadas; o laço ocioso do VI65
  roda ~2.900 vezes por segundo).
- **O SHIFT esconde a linha 0 no emulador**: com KBOUT = `$01` e SHIFT apertado ele responde só
  `1`, então SHIFT + B V C X Z são lidos como SHIFT sozinho. Leia a linha 0 com KBOUT = `$03`
  (linhas 0 e 1 combinadas por OR) depois de ver que a linha 1 está vazia; o VI65 varre as
  linhas de 7 a 0 por isso.
- **CTRL sozinho como tecla extra** (o ESC do VI65): leia o CTRL a cada consulta; apertado sem
  outra tecla = armado, outra tecla enquanto apertado = desarmado, solto enquanto armado = a
  tecla. As combinações com CTRL continuam funcionando.
- **Sem latch: teclas apertadas durante um redesenho longo se perdem.** Consulte o teclado entre
  as linhas desenhadas e guarde os novos toques num buffer pequeno (o VI65 perdia teclas a
  150 ms por tecla antes disso).

## 5. Som

- Qualquer acesso a `$C030` inverte o cone do alto-falante (1 bit, sem volume, sem timer). O
  mesmo endereço do Apple II.
- O emulador silencia a saída quando o alto-falante não é invertido por um tempo (não mantém
  nível DC) e não produz som enquanto roda em velocidade máxima (carga de fita).
- Sem timer, o som é gerado pela CPU em laços com ciclos contados; enquanto a CPU desenha, o
  alto-falante fica mudo. Abordagens testadas no River Raid (passo 6):
  - **Fatia por quadro**: no fim de cada quadro desenhado, rode por alguns ms um laço
    sintetizador com ciclos contados. O laço do River Raid (`src/sound.s`, `PlaySound`) roda a
    40 ciclos por iteração (25,6 kHz), faz a contagem regressiva de dois canais (inversões de
    tom, ou ruído de um LFSR de Galois de 8 bits com `$B8`), mistura-os por XOR e inverte o
    alto-falante nas mudanças. Mantenha o estado dele na página zero (RAM absoluta deixou o laço
    com 62 ciclos em vez de 40). Zere os contadores a cada fatia (contadores velhos perto de 255
    deixam a fatia muda).
  - **Volume = duração da fatia** (não há amplitude): sons mais altos ganham fatias mais longas.
  - **Altura**: os tons do 2600 (180-1000 Hz) são graves demais para serem reconhecidos em
    fatias de 2-5 ms (uma ou duas bordas = um clique). Tocá-los duas oitavas acima dá o "zumbido"
    típico de beeper; quando o jogo está parado (jato perdido), toque continuamente na altura
    original.
  - **Use o tempo ocioso**: quando um quadro tem de esperar o resto do seu tique (ritmo de
    quadros), toque som em vez do laço de espera.
  - **Compromisso**: cada ms de som por quadro custa taxa de quadros (≈ 2% de fps por ms a
    ~20 fps). Som contínuo com o jogo rodando não é possível sem parar o jogo.
  - Conte a fatia no custo em ciclos do quadro para que a velocidade do jogo continue correta.
  - **Resultado: as fatias soaram picotadas** (som a cada ~45 ms = um tremor de "helicóptero" de
    20 Hz) e o dono do projeto as rejeitou, também para o ronco do motor.
  - **O que funcionou: uma rajada contínua por efeito.** Quando o original começa um efeito,
    toque-o no fim daquele quadro como uma única rajada curta (`PlayBurst` do River Raid, 39
    ciclos por iteração, medido): explosão 80 ms de ruído cujo período cresce (fica mais escuro,
    imitando o decaimento), batida 350 ms (o jogo está parado mesmo), reabastecimento bipe de
    25 ms na altura e no ritmo originais, míssil 30 ms de tom deslizante, combustível baixo
    sirene ascendente de 60 ms. O jogo para durante a rajada; contá-la no custo do quadro mantém
    a velocidade do jogo certa. Prioridades quando vários começam no mesmo quadro: batida >
    explosão > outros.
  - Sons longos e sustentados do 2600 (motor, bipes de 133 ms com decaimento) não podem ser
    reproduzidos; rajadas curtas na altura original ficaram "boas o bastante" para o dono do
    projeto. Estreitar a largura do pulso pode imitar um decaimento em 1 bit (preparado como
    opção, não foi necessário).
  - O tocador de fatias foi removido quando todos os efeitos viraram rajadas (custava ~650
    bytes).
  - Processo que funcionou com o dono do projeto: um efeito de cada vez, cada um com um WAV do
    TK2000 e um WAV de referência do original, ou opções sintetizadas offline para escolher.
- **Cliques a partir de checkpoints** (Tennis, §15): sons feitos de cliques esparsos do
  alto-falante (o ruído do 2600 numa taxa baixa: uma pancada = 11-17 cliques em 33-50 ms) podem
  tocar *durante* o desenho: chamadas a `Poll` colocadas entre as etapas do desenho (10 por
  quadro) invertem o alto-falante para os cliques que já estão na hora. A posição de cada
  checkpoint no quadro é uma constante medida no py65 (mediana dos ciclos desde o início do
  quadro); os cliques caem a ~1 ms do seu momento, sem congelar, sem deixar o jogo lento.
- **Tons enquanto o original está parado** (bipes de ponto/game do Tennis, músicas do Pole
  Position): quando o original para o jogo (depois de um ponto, antes de uma corrida), toque o
  tom durante o tique inteiro em vez de desenhar; a contagem de tempo (§7) mantém a velocidade do
  jogo. Bipes em volume máximo são mais ásperos que os do 2600, que vão sumindo: o dono do
  projeto pediu que fossem mais curtos (tocar só os tiques cujo AUDV é >= 9).
- Porte a lógica de som original literalmente (River Raid: `DoSound` → valores dos registradores
  da TIA por tique), depois converta os valores dos registradores para o tocador de 1 bit:
  AUDC 4 = tom puro invertendo a cada AUDF+1 pulsos de 31,4 kHz, AUDC $C = /3, AUDC 8 = ruído
  (poly de 9 bits), AUDV = volume.
- Verifique o som offline: registre no py65 os instantes, em ciclos, dos acessos a `$C030`, gere
  um WAV (níveis de 1 bit a 22.050 Hz) e gere os canais da TIA originais, a partir dos valores
  dos registradores por tique, como WAV de referência para comparar; conte as bordas e as
  "janelas de 10 ms ativas". Entregue ao dono do projeto WAVs curtos, de um efeito só (ponha-os
  no `build/` do projeto, não em /tmp), um efeito de cada vez.
- **Som contínuo de dois canais durante o jogo inteiro** (Enduro, `enduro-tk2000/src/sound.s`):
  cada canal da TIA é tocado como a TIA tocaria (a saída dos contadores poly muda nos seus
  próprios momentos: tabelas `Gap3`, `Gap5`, `Gap9` com os intervalos entre as mudanças, em
  ciclos de CPU), e o alto-falante é invertido quando qualquer uma das saídas muda (o XOR
  delas). Sem timer, **checkpoints** (`SND name`, uma macro de ~12 ciclos) espalhados por todo o
  código do TK2000, cerca de 2 por ms, subtraem o tempo medido desde o anterior (`sndk.inc`,
  ajustado no py65 por `sndfit.py --write`) do tempo até a próxima mudança; ao chegar a 0, a
  mudança acontece. Oito ganchos dentro da lógica de jogo do original fazem o mesmo ali (sem
  eles o som para ~5 ms a cada tique). Altura a ~1-2% da original (o `sndfit.py` a imprime por
  categoria: motor, freios, batida, com neve ou com um carro). Custo: o jogo desenhava ~11 em
  vez de ~16 imagens por segundo; o dono do projeto achou que o som valia a pena ("a alma do
  jogo"). Código novo precisa dos seus próprios checkpoints (corpo de laço = um checkpoint por
  volta) e de rodar o `sndfit` de novo, senão a altura se desvia.
- **Tons agudos não sobrevivem aos checkpoints**: um bipe de 1,2 kHz precisa de uma inversão a
  cada ~0,4 ms; com checkpoints a 0,1-1 ms de distância ele saiu áspero e falhado (medido: meios
  períodos de 0,2-0,8 ms, buracos de até 7 ms). Toque um tom curto assim de uma vez, num laço
  com ciclos contados (`BeepTone` do Enduro, 66 ms), lance os ciclos dele no saldo do ritmo (§7:
  o jogo recupera pulando imagens) e mantenha os canais mudos alguns tiques depois dele. Confira
  gravando os cliques no py65 e medindo os meios períodos, não de ouvido.
- **Um WAV do programa do TK2000 tem de ser cortado pelos tiques do jogo**, não por uma taxa de
  tiques suposta: cortar "tiques 360-600" a 60,9 tiques/s desde o início pegou outra parte da
  corrida e deu uma comparação confusa. Registre o ciclo de cada tique e corte entre eles.
