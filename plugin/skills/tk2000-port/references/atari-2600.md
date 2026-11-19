# Portando um jogo de Atari 2600 (a partir de uma ROM, de um disassembly ou do fonte)

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. As pastas de jogo citadas (como `tennis-tk2000`) são projetos do autor, não publicados; as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## 8. Portando um jogo de Atari 2600

### 8.1 Obtendo o original

- Encontre um disassembly comentado (River Raid: o de Thomas Jentzsch). Remonte-o com `dasm`
  (`-f3`, com o `vcs.h` da pasta de máquinas do dasm) e compare o MD5 com o cartucho real
  antes de confiar nele. O River Raid precisou de `-DTIA_BASE_READ_ADDRESS=48` para que as
  leituras de colisão caíssem nos registradores de leitura da TIA (senão, na simulação, liam a
  ROM e o avião morria na hora).
- Guarde a imagem da ROM no projeto (`reference/`) e use `.incbin` para pegar as tabelas
  originais direto dela (padrões de playfield, formas, cores, tabelas de placar), com seus
  endereços na ROM.
- **Um fonte original:** o fonte Atari de 1985 do Pole Position (`ATARI_POLE26.S`), convertido
  para a sintaxe do dasm (`tools/pole2dasm.py`), monta exatamente o cartucho vendido (só os
  trechos de troca de banco diferem): confira isso antes de confiar em comentários sobre versões
  "inacabadas".
- **Sem fonte nenhum** (Tennis): faça você mesmo o disassembly. Rode o cartucho no simulador
  com entradas programadas (SELECT, RESET, os dois joysticks, as chaves) por alguns milhares de
  quadros e registre quais bytes da ROM rodam como código (`tools/reference/coverage.py`),
  acrescente um rastreio estático a partir dos vetores e de cada instrução executada, e gere
  fonte dasm com rótulos, nomes de TIA/RIOT conforme o tipo de acesso (nomes de leitura para
  loads, de escrita para stores) e `.w` nos endereços de página zero usados com modos absolutos
  (`tools/dis2600.py`). `make ref` confere se ele monta os mesmos 2048 bytes. Depois dê nomes às
  variáveis e rotinas na ferramenta (observando-as no simulador contra a imagem) e continue
  conferindo que ele ainda monta idêntico.

### 8.2 Portando a lógica

- **Mantenha as variáveis de página zero do original nos seus endereços do 2600 (`$80-$FF`)**:
  assim o código da lógica pode ser portado instrução por instrução. O motor usa o resto da
  página zero.
- Porte as rotinas uma a uma, com os rótulos e comentários originais; troque só o acesso ao
  hardware.
- **Verifique os portes contra o original** rodando os dois no py65: `atari.py` roda o
  cartucho com a TIA/RIOT reduzidas a registradores; `check_river.py` roda o original e o porte
  lado a lado e compara os blocos gerados (316 blocos nas fases 1-9, 0 diferenças).
- `scanlines.py`: registro, linha a linha e por ciclos, do que o kernel do 2600 escreve (PF,
  GRP, cores; 76 ciclos por linha, WSYNC alinha). Use-o para saber exatamente qual entrada de
  forma/cor aparece em qual linha, em vez de adivinhar pelo código do kernel (o índice de cor do
  River Raid estava errado por um até ser medido).
- Coisas que a TIA fazia em hardware e que precisam virar software:
  - **posições**: o 2600 guarda os valores grosso/fino da TIA; guarde o x simples (0..159)
  - **playfield**: a ordem dos bits de PF0/PF1/PF2 (PF0 e PF2 invertidos, metades espelhadas
    ou repetidas)
  - **tamanhos e cópias de objetos** (NUSIZ: dobro, quádruplo, duas cópias próximas...)
  - **reflexão** (REFP)
  - **colisões**: compare os bytes dos sprites (AND dos dados pré-deslocados dos dois sprites
    nas mesmas colunas) e teste os bits do playfield sob os pixels do sprite
- Semântica das colisões: a TIA trava as colisões enquanto o quadro é exibido e o jogo as lê
  durante o quadro seguinte. Num porte que desenha uma vez a cada 2-3 tiques, uma colisão
  detectada ao desenhar vale para todos os tiques do quadro seguinte. **Índices de objeto
  guardados precisam acompanhar os deslocamentos da lista**: quando o original rola a sua lista
  de objetos (o `NewBlock` do River Raid desce cada objeto uma posição), qualquer índice
  guardado (collidedEnemy) tem de ser decrementado, senão a colisão é aplicada ao vizinho (bug:
  voar sobre o combustível explodia o helicóptero acima dele).
- Objetos rápidos (mísseis, 6 linhas por tique) precisam ser testados **a cada tique** na
  lógica, não a cada quadro desenhado, senão passam por cima dos alvos.
- Disposição da tela: o 2600 mostra ~160-192 linhas; o River Raid usa as linhas 0-159 para o
  playfield e 160-191 para a barra de status (placar, medidor de combustível, vidas).
- Conversão dos gráficos do 2600 (ferramentas em Python que geram arquivos `.inc`):
  - **tamanho do pixel**: 1 pixel do 2600 = 2 pixels do TK2000 (um par, para que o branco
    funcione sobre qualquer fundo); na horizontal o TK2000 tem 280/160 = 1,75 pixel por pixel
    do 2600, então os sprites ficam um pouco mais largos que os originais
  - **cores**: mapeie matiz/luminância NTSC do 2600 para a paleta com uma tabela explícita e
    documentada, e exceções por objeto decididas com o dono do projeto (River Raid: helicóptero
    preto, avião branco, árvore da casa preta com metade da largura)
  - **dígitos**: os dígitos do placar do 2600 usam 6 de 8 pixels → 6 pares de pixels + 1 par
    vazio = 14 pixels = exatamente 2 bytes, alinhados ao byte (rápidos de desenhar)

### 8.3 Rodando o original sem mudanças (Pole Position, Tennis)

Em vez de portar rotina por rotina (River Raid), monte o próprio código do original para o
TK2000 e troque só o seu kernel de vídeo:

- Monte o disassembly/fonte num endereço do TK2000 (Tennis: `dis2600.py --tk`, ORG $4000;
  Pole Position: bancos realocados para $8000-$9FFF). Troque o salto para o kernel (Tennis: a
  espera do timer, `LDA INTIM / BNE`) por um `JMP` para a rotina de quadro do TK2000, que
  desenha a imagem a partir das variáveis do original e volta para onde o kernel teria
  terminado (`Overscan`). Ponteiros montados a partir de tabelas da ROM só importam para o
  kernel, então a realocação é segura quando a lógica lê os dados pelos rótulos.
- A E/S do 2600 cai na RAM do TK2000: as escritas na TIA na página zero $00-$3F (inofensivas;
  leia ali de volta os registradores de som $15-$1A), as leituras da TIA também (botões: INPT4
  $0C / INPT5 $0D, preenchidos pela rotina de quadro a partir das teclas), a RIOT na página 2
  (SWCHA $0280, SWCHB $0282; INTIM $0284 tem de ler 0). O original mantém sua RAM em $80-$FF; a
  página zero do código do TK2000 fica abaixo ($40-$7F) e o seu estado por página fica fora da
  página zero: a inicialização do original zera toda a página zero.
- **Deixe os registradores como o kernel deixava**: o overscan do Tennis usa Y = 0, que o
  kernel por acaso deixava (um bug quando a rotina de quadro voltava com outro Y).
- **Confira a lógica contra o original a cada quadro**: rode o binário do TK2000 no py65 e o
  cartucho no simulador de 2600 com as mesmas entradas programadas, aplicadas no mesmo ponto (o
  gancho), e compare as variáveis do original, exceto as que só o kernel usa
  (`tools/reference/tkcheck.py`, `make check`: 3000 quadros, 0 diferenças).
- **Meça o que o kernel mostra**, não adivinhe: renderize quadros no simulador e ajuste o
  modelo (Tennis: jogador = duas colunas de 8 pixels, GRP1 à esquerda / GRP0 à direita, 24
  linhas; linha da bola -> linha da tela `185 - line`, `186 - line` abaixo da rede; x =
  `ballX - 5`). Silenciar GRP0/GRP1 num segundo simulador dá um fundo limpo (a quadra) e uma
  diferença em pixels dos jogadores.
- Cenário estático (uma quadra) é descompactado uma vez nas duas páginas e numa terceira cópia
  ($8000), de onde o apagamento restaura; os objetos que se movem são apagados e redesenhados
  na página de trás a cada imagem.

### 8.4 Desempenho esperado (números do River Raid)

- ~42 mil ciclos de trabalho por quadro → ~24 fps normal, ~17 fps na rolagem rápida; ~20 fps
  atirando, com som.
- Maiores custos: composição dos objetos (~63%), renderizador delta do rio (~25%).
- Otimizações que valeram: renderização delta, cache de linhas, composição por união, junções
  desenroladas, atualizações parciais de grupos do playfield, pular objetos longe do míssil
  antes de montar o sprite inteiro, teste de terra embutido com um ponteiro para a tabela de
  anel, página zero para o estado dos laços internos.
- Otimizações que valeram pouco: desenrolar mais quando os custos principais já eram tabelas.
  Sempre faça o perfil antes (`profile.py`, `hotspots.py`).
- Variante com um só buffer (desenhar na página visível): menos trabalho, mas o dono do
  projeto achou o movimento menos suave → mantenha a troca de páginas.


## 15. Lições do porte do Tennis (`tennis-tk2000`, nov/2026)

O Tennis da Activision (cartucho de 2K, sem fonte), portado em um dia rodando o original sem
mudanças (§8.3) e desenhando a sua imagem. A ordem que funcionou: disassembly idêntico ao
cartucho (§8.1), capturas de tela do simulador, protótipos de cor, disassembly com nomes, fita
com a quadra estática, lógica com a bola, jogadores, placares, sons um de cada vez, tela
inicial.

- **Cores:** sobre um fundo verde (paleta 0) só objetos pretos, brancos e azuis ficam limpos.
  Um objeto vermelho deixa ciano a quadra em volta dele (mesmo byte = paleta 1); um objeto
  ciano some dentro de uma caixa ciano (ciano = o padrão de bits do verde na paleta 1). O
  esquema do dono do projeto: quadra verde, linhas/rede/bola brancas, sombra preta, jogadores
  preto e azul (a cor de cada jogador também no seu placar e nas linhas laterais da sua metade).
- **Escala:** objetos com um par de pixels por pixel do 2600 (mantém as formas; 16 pares para
  um jogador), posições escaladas por 7/8 (160 -> 140 pares); ancore os objetos no seu centro
  escalado, para que o que precisa se tocar (raquete e bola) continue se tocando.
- **Defeitos do Atari corrigidos (dono do projeto: "corrija qualquer falha que você
  detectar"):** o playfield (linhas de fundo, rede) ficava 3 pixels à direita dos mísseis
  (linhas laterais): movemos o playfield, não os objetos contra os quais a lógica compara; uma
  bola fora de jogo estacionada em x = 2 dava a volta até a borda direita: não é desenhada; a
  bola escondida atrás das linhas da rede: mostrada.
- **Melhorias são bem-vindas:** o TK2000 desenha o cenário uma vez só, então detalhes que o
  2600 não podia pagar saem de graça: a rede como faixa + malha preta + postes (o que também
  mantém a bola branca visível sobre ela). Recusadas: linhas de saque e linhas laterais brancas
  (decoração que as regras não usam, e as linhas laterais perderiam as cores dos jogadores).
- **Velocidade:** um primeiro desenho dos jogadores custava 24 mil ciclos por imagem (o jogo
  rodava a 40%); laços de apagar/desenhar desenrolados, tabelas de endereço de linha por página
  (`lda (hiDst),y`) e a escrita com máscara `dst ^ ((dst ^ color) & image)` levaram a imagem
  inteira a ~15,5 mil ciclos: 60 imagens e 60 tiques por segundo com ritmo por dívida de tempo
  (§7).
- **Tamanho da fita:** 5,6 KB de imagens pré-deslocadas deixavam a carga em 74 s; guardar as 8
  imagens base (~200 bytes) e deslocá-las ao ligar (~2 s, em $0400-$1FFF) baixou para ~48 s.
- **Placares:** reproduza as regras de disposição do kernel (dois glifos por placar, a 64
  pixels um do outro; DEUCE / AD IN / AD OUT como quatro glifos lado a lado numa cor só),
  medidas forçando as variáveis de placar no simulador. Redesenhe só quando mudam (por página).
- **Um joystick:** o TK2000 tem uma única entrada de joystick, então o dono do projeto
  descartou os jogos de dois jogadores. Em vez disso, uma tela inicial com três níveis montados
  com as próprias opções do original (jogo 3 em meia velocidade, a chave de dificuldade do
  computador); RETURN volta para ela. O dono do projeto não quis imagem de carga desta vez.


## 17. Lições do porte do Enduro (`enduro-tk2000`, nov/2026)

O Enduro da Activision (4K, disassembly comentado `enduro_nomeado.asm` que remonta idêntico com
o dasm). Feito em três dias, cada passo conferido contra o cartucho. A imagem de 2600 mais
pesada até agora (uma estrada de 100 linhas com curvas e morros, 7 outros carros, montanhas,
faixas do pôr do sol, neblina, painel): ~9 imagens por segundo com todos os sons, lógica do
jogo em velocidade total.

**Rode o original sem mudanças, no seu próprio endereço.** A ROM de 4K roda em `$F000-$FFFF`
na RAM sob a ROM do TK2000 (modelo de 64K): nenhuma realocação. Uma instrução mudou (o `jmp`
para o kernel, agora para `TkFrame` em `$4003`), mais 8 ganchos de som (§5 de `maquina.md`)
colocados com um script que escolhe pontos com no máximo ~650 ciclos entre dois.
`tools/liveness.py` provou que nada do que o kernel pulado e a exibição do placar escrevem é
lido pela lógica antes de ser reescrito (40.000 quadros, entradas aleatórias). `make check` = o
programa inteiro do TK2000 no py65 contra o cartucho, a cada tique, 6.000 tiques, 0 diferenças;
foi rodado depois de cada mudança.

- **O original escreve toda a página zero `$00-$7F`** (registradores da TIA, e stores indexados
  que passam do fim das suas tabelas): nenhum estado do TK2000 pode morar na página zero entre
  quadros; use a página zero só como rascunho dentro de um quadro. Não altere `$F200-$F2FF`: o
  jogo lê o próprio código ali como números aleatórios.
- **Lockstep sem as colisões do simulador** (lockstep = execução lado a lado, passo a passo): o
  simulador de 2600 não trava as colisões no mesmo momento, então a conferência as zera dos dois
  lados; as colisões têm as suas próprias conferências (um modelo ajustado no simulador, depois
  o código do TK2000 contra o modelo).
- **Meça cada elemento visual no simulador, depois confira o desenho do TK2000 contra o
  modelo**, pixel a pixel, em cada quadro de uma longa corrida com o estado forçado ao acaso de
  vez em quando (`hudfit.py` -> `hudmodel.py` -> `hudcheck.py` (modelo vs simulador) e
  `dashcheck.py` (TK2000 vs modelo); o mesmo para os morros, os carros, as faixas, a neblina).
  Leia o estado no ponto em que a exibição começa (`$F1AE` aqui), não no fim do quadro: algumas
  variáveis mudam depois da exibição. O estado da TIA por linha no início de cada linha
  (`states` do `vcs.py`) dá diretamente as cores de cada linha.
- **As manias do kernel importam**: o Enduro define a cor das bordas da estrada (`COLUPF`) só
  onde começa uma faixa dos outros carros (`B[k] - 4`), então na neblina as bordas distantes
  ficam da cor do chão e somem (o corte se move com os carros); as faixas do pôr do sol são a
  `SunsetTab` avançando a cada duas linhas atrás dos morros. As duas coisas foram descobertas
  imprimindo as cores por linha, não lendo o kernel.
- **Forçar estados** (mexer na hora do dia, no hodômetro, no dia) é como se chega a telas raras
  nos testes, mas o original pode então mostrar coisas que nunca mostra jogando (carros fora da
  estrada depois de um salto para a noite): compare com o simulador no mesmo estado forçado
  antes de chamar de bug.
- **Cores por misturas 2x2** de cores do TK2000 (`mkcolors.py`: linhas alternando duas cores
  quaisquer, pares alternando dentro de um mesmo grupo de paleta; cinzas só de preto e branco),
  escolhidas com o dono do projeto a partir de folhas lado a lado das 16 horas do dia do
  original.
- **Truques de velocidade que valeram** (de ~11 para ~25 imagens/s antes do som): redesenhar só
  as linhas cujas bordas se moveram desde que aquela página foi desenhada; bytes de borda
  pré-feitos com o chão dentro (escrever, sem ler-modificar-escrever); a estrada em faixas de 4
  linhas a partir de tabelas (conferidas contra o jeito linha a linha para cada entrada no
  gerador de tabelas); o carro do jogador redesenhado só onde algo encostou nele; morros
  desenhados invertendo com XOR só os pixels entre o fim antigo e o novo de cada trecho; uma
  célula do painel desenhada numa página só quando mudou ali; a estrada distante pulada na
  neblina; testes de colisão só quando uma borda está perto do carro, e por borda só quando o
  seu alcance pode chegar ao carro (resultados provados idênticos aos da rotina antiga em cada
  chamada).
- **Faça o perfil por rótulo** antes de otimizar (`scripts/atari/profile_labels.py`): ciclos
  por rotina (exclusivos e inclusivos) ao longo de uma corrida inteira. No fim: lógica original
  32% (só o laço de curva da estrada dela, 11%), bordas da estrada 25%, som 11%, carros 12%,
  colisões 7%. Reescrever os laços do próprio original foi recusado: abre mão de "o original
  roda sem mudanças" por alguns por cento.
- **Tela inicial sem arquivo de imagem** (`scripts/tk2000/mkstart.py`, `start.s`): uma fonte 5x7
  (e uma 3x5 onde uma linha não cabia) desenhada na partida invertendo pares de pixels sobre o
  preto: ~600 bytes em vez de uma página compactada com LZ (só uma página vazia compacta para
  ~970 bytes com o `lz.py`). Opções trocadas com uma tecla são redesenhadas limpando seus bytes
  e desenhando o texto seguinte. O endereço de início do carregador é uma entrada separada
  (`$401E`), para que todo teste, que começa em `$4000`, pule a tela; RETURN ali segura o reset
  do jogo por 10 tiques (o jogo começa direto, sem demonstração).
- **Espaço no arquivo**: o carregador de fita/disco fica em `$BC00`, então o arquivo do
  programa tem de terminar antes dele; tabelas que podem ser calculadas (endereços das linhas
  da tela de alta resolução (hi-res), sprites pré-deslocados) são montadas na partida em RAM que não está no arquivo
  (`$0800-$1FFF`, `$8800-$9FFF` por cima das imagens de carga copiadas, `$C200+`).
- **Escolhas do dono do projeto** que vale reaproveitar: prévias de som para cada efeito
  (ruído da neve em meia taxa; só o motor do outro carro mais próximo; o bipe de aviso sozinho,
  motor pausado); manter o fps em vez de 60 tiques/s exatos (1-2% mais lento aceito); nuvens
  removidas pela velocidade; tela inicial em português com uma opção para deixar o motor dos
  outros carros curto ou mudo (ele fica irritante).
