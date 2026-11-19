# 5. Portando um programa de outra linguagem

A partir do porte do xadrez: o motor de xadrez de 1 KB em JavaScript de Óscar Toledo G. (na
versão modificada para *The Kilobyte's Gambit*, do vole.wtf) virou código 6502 e depois ficou
mais rápido e mais forte. O método vale para qualquer lógica de jogo ou IA escrita numa
linguagem de alto nível (JavaScript, C, Python, BASIC).

## 5.1 Primeiro, uma tradução fiel

Traduza **comando por comando**, mantendo os nomes do original em comentários, antes de melhorar
qualquer coisa. Um porte fiel pode ser conferido mecanicamente contra o original; um porte
"melhorado", não.

Decisões que a tradução obriga a tomar:

- **Tamanho dos números.** Os números do JavaScript são de ponto flutuante de 64 bits; o 6502
  trabalha com bytes. Descubra a faixa real de cada variável e escolha 8 ou 16 bits. As
  pontuações do xadrez couberam em 16 bits depois que as pontuações de mate (cerca de ±40.000)
  foram cortadas pela metade; todo o resto ficou igual.
- **Recursão.** A pilha do 6502 tem 256 bytes: guarde as variáveis locais da função recursiva
  numa pilha de quadros própria na RAM e deixe só os endereços de retorno na pilha do 6502.
- **Aleatoriedade.** O original usava `Math.random()` para desempatar; o porte tem seu próprio
  gerador, com a semente tirada do tempo entre os toques de tecla, e uma chave para desligá-lo
  nos testes.
- **Coisas que o original nunca faz.** O motor nunca escolhia um lance na profundidade 1; o porte
  acrescentou isso explicitamente (e documentou como uma diferença).

Espere um resultado lento: o porte fiel do xadrez levava cerca de 6 s por lance com 2 meios
lances (plies) e quase 10 minutos com 3 plies numa máquina de 1 MHz.

## 5.2 Depois, melhore um passo medido de cada vez

Cada melhoria passou pelo mesmo ciclo:

1. Implemente-a numa **cópia em JavaScript** do motor, com uma opção para ligá-la ou desligá-la.
2. **Meça** ali: posições examinadas, partidas de motor contra motor, tempo no 6502 (contagem de
   ciclos no emulador).
3. Mostre os números e os prós e contras; decida.
4. Porte-a para 6502 e confira o porte contra a versão em JavaScript, lance a lance.

O que foi testado no porte do xadrez, com os resultados:

| Mudança | Resultado | Ficou? |
|---|---|---|
| Ordenação de lances (ordenar os lances pelo ganho imediato onde a busca vai mais fundo) | 2× mais rápido com 2 plies, 15× com 3 plies, mesmos lances (só os empates diferem) | Sim |
| Avaliação posicional (tabelas peça-casa, a *Simplified Evaluation Function* de Michniewski) | 62% em 100 partidas contra só material, e 20-26% mais rápido | Sim |
| Livro de aberturas tirado de partidas reais (Lichess, jogadores 1800+, árvore de 3,7 KB) | Aberturas instantâneas e sensatas | Sim |
| Avaliação de "mop-up" (empurrar o rei sozinho para a borda) | Dá mate em todo final de rei + dama (antes nunca dava) | Sim |
| Lances assassinos (killer moves: tentar cedo os últimos lances que causaram corte) | 11% mais rápido com 3 plies, mesmos lances | Sim |
| Tabela de transposição, aprofundamento iterativo | Nenhum ganho relevante nessas profundidades, 8 KB de memória | Não |
| Heurística de histórico | Nada além do que os killer moves já davam | Não |

Ponha no README o link para a explicação de cada técnica (a Chess Programming Wiki tem uma página
por técnica); quem lê deve conseguir entender por que cada uma está ali.

## 5.3 Níveis e tempo

Numa máquina de 1 MHz, cada ply a mais de busca multiplica o tempo por cerca de 7-8. As medições
do porte do xadrez (tempo de um TK2000 real):

| Busca | Média por lance | Mais lento visto |
|---|---|---|
| 2 plies | 2-6 s | ~11 s |
| 3 plies | 25-45 s | 2-5 min |
| 4 plies | ~5,7 min | ~16 min |

Por isso os níveis misturam profundidades conforme a situação em vez de uma profundidade fixa:
buscar mais fundo só quando o computador está atrás em material, ou quando até o seu melhor lance
de 2 plies perde alguma coisa (uma ameaça que ele deveria examinar melhor). Cada limite foi
escolhido a partir de medições (com que frequência é acionado, tempo médio e pior tempo) e de
partidas contra o nível de baixo.

## 5.4 A armadilha da busca rasa

Com 2 plies o motor enxerga o seu lance e a resposta, mais as capturas um passo adiante. Às vezes
ele entrega uma torre por um cavalo porque toda alternativa que consegue ver parece quase tão
ruim. Isso não é um defeito do porte (o original faz o mesmo na mesma posição); confira isso
antes de "consertar" qualquer coisa: refaça a posição, rode os dois motores e compare as
pontuações.

## 5.5 Memória

O porte do xadrez, para ter uma ideia: programa, gráficos, tabelas e livro de aberturas de
`$4000` a `$831F`; tabuleiro em `$0300`; quadros da busca em `$0400`; listas de lances para 5
plies (128 lances cada) em `$A000-$B8FF` (ele usa só uma página de hi-res). Ficaram livres cerca
de 15 KB.

Para começar um porte assim com o Claude Code, veja a primeira mensagem pronta em
[11. Começando um porte](11-primeiras-mensagens.md#115-um-programa-em-outra-linguagem-javascript).
