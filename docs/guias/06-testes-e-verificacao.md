# 6. Testes e verificação

A regra que salvou os dois portes: **cada parte do porte é conferida contra uma referência, por um
programa, e não jogando.** Jogando, os bugs aparecem tarde, e jogar não diz se o porte faz o que
o original faz.

## 6.1 Três tipos de verificação

| Verificação | O que ela compara | Exemplo |
|---|---|---|
| Lógica contra o original | As rotinas do porte e o programa original, com as mesmas entradas | River Raid: blocos de rio gerados pelo código do 2600 (py65) e pelo porte (316 blocos, 0 diferenças). Xadrez: o lance, o tabuleiro e a casa de en passant do motor 6502 contra os do motor em JavaScript, depois de cada lance de muitas partidas |
| As rotinas do próprio jogo | As rotinas que o jogo pronto de fato executa (leitura do teclado, menus, escolha do nível, livro de aberturas) contra o que elas deveriam fazer | Xadrez: `BookMove` do programa real contra os dados do livro (3.698 casos); a profundidade escolhida por cada nível (15.192 posições) |
| O jogo inteiro no emulador | Capturas de tela e dumps de memória da fita real, comandada por teclas apertadas por script | Título, instruções, alguns lances, os sons de fim de jogo |

## 6.2 Teste o código que vai para o jogador, não uma cópia

O porte do xadrez tinha uma versão de teste do motor (pontos de entrada `think`, `player`) e a
comparava com o JavaScript depois de cada mudança: 0 diferenças. Mesmo assim, dois bugs sérios
chegaram ao jogador, os dois **no jogo em volta do motor**:

1. Uma rotina que deveria devolver o resultado em A e no flag zero deixava o flag de um `ldx`
   anterior. Quem a chamava confiava no flag, concluía "final especial" e buscava todos os
   lances com profundidade 0: o computador entregava a dama em poucos lances. Os testes do motor
   definiam a profundidade diretamente, então nunca passavam por esse caminho.
2. Uma rotina auxiliar documentada como "preserva A" sobrescrevia A. O percurso do livro de
   aberturas então testava o bit errado, e uma linha do livro funcionar ou não dependia de
   **onde o livro estava na memória**. Funcionou até o programa crescer; aí 40% das posições do
   livro falharam.

A correção foi um harness (o emulador sem janela, usado para testes) que chama **qualquer rotina
do programa real** na CPU do emulador:
[`tools/harness/call.cpp`](../../plugin/skills/tk2000-port/scripts/tk2000/harness/call.cpp).

```sh
c++ -std=c++17 -O2 -w -I$EMU $(sdl2-config --cflags) -include $EMU/pch.h \
    tools/harness/call.cpp $EMU/{Bus,Cpu6502,Rom,Ram}.cpp $(sdl2-config --libs) -o build/call
# uma chamada por linha: ENTRADA [a:HH] [w:ENDEREÇO:HEX]... [r:ENDEREÇO:TAM]...
echo "45B6 w:0300:...board... r:009C:1" | build/call build/game.bin 4000
# -> CYCLES A X Y P <bytes lidos>
```

Pegue os endereços das rotinas no arquivo de rótulos do ld65 (`-Ln`), escreva as entradas na
memória, leia as saídas de volta e compare com uma referência escrita numa linguagem de script.
Faça as verificações falharem primeiro no código antigo (a verificação do livro falhou em 1.537
de 3.698 casos na versão com o bug): uma verificação que não consegue falhar não prova nada.

Lições:

- **Os flags fazem parte do contrato de uma rotina.** Se um comentário diz "devolve em A e Z",
  termine a rotina com uma instrução que ajusta Z a partir de A (`ora #0`) e teste o flag.
- **Rode todas as verificações depois de cada mudança no código do jogo**, não só depois de
  mudanças no motor.
- Num harness ingênuo, a memória persiste entre as chamadas: zere as variáveis que uma rotina lê
  (a verificação do livro chegou a acusar 2.152 falhas que eram um flag velho do caso anterior).

## 6.3 O emulador sem janela

[`tools/harness/run.cpp`](../../plugin/skills/tk2000-port/scripts/tk2000/harness/run.cpp) carrega uma fita, digita `LOADT`, aperta
Play, aperta teclas em tempos emulados determinados, salva capturas de tela e faz dump da memória:

```sh
build/run dist/game.ct2 -t 172 -k 160:0.1:space -k 163:0.05:left -s 170:build/shot.ppm -m 0600:20
```

- Os tempos são segundos emulados contados a partir do Play. O programa só começa quando o
  carregamento termina, e isso fica mais tarde à medida que o programa cresce: confira de novo a
  linha do tempo depois que o binário crescer (uma captura feita durante o carregamento mostra a
  linha de status da ROM).
- Teclas: `left right up down space return` ou uma letra/dígito.
- As capturas de tela são PPM; converta com o Pillow (ou com `sips` no macOS) e olhe para elas
  antes de dizer que algo funciona.
- Escreva scripts para partidas inteiras: calcule os movimentos do cursor para uma lista de lances
  de xadrez, aperte-os e faça dump do histórico de lances da memória depois de cada um. Foi assim
  que o bug do livro de aberturas foi reproduzido, a partir da partida do jogador, em minutos.

## 6.4 Meça, não chute

- **Tempo:** ciclos da CPU do emulador divididos por 1.022.727. Informe médias e o pior caso
  sobre muitas posições; o pior caso é o que os jogadores percebem.
- **Força ou qualidade:** partidas motor contra motor a partir das mesmas aberturas, com as duas
  cores (100 partidas), levando em conta a margem: com 100 partidas, um resultado de 55% está
  dentro da variação aleatória em torno de 50%.
- **Gráficos e som:** prévias que o dono do projeto consegue abrir (capturas de tela em PNG,
  arquivos WAV) na pasta `build/` do projeto, uma coisa de cada vez.

## 6.5 Quando o jogador relata um lance ruim ou um bug

1. Reconstrua a posição a partir da captura de tela ou da lista de lances do jogador.
2. Rode o porte **e** a referência nela.
3. Se os dois concordam, é o comportamento do original (por exemplo, os limites de uma busca
   rasa): explique com os números. Se discordam, é um bug do porte: descubra qual rotina diverge
   com o harness de chamadas.
4. Acrescente uma verificação que o teria pegado.
