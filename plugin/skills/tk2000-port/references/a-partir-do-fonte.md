# Portar a partir do código-fonte (fonte 6502, um disassembly comentado, outra linguagem)

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. Pastas com nome de projeto (como `chess-tk2000`) são projetos do autor, não publicados (podem não existir em outra máquina); as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## Qual fonte, qual caminho

O melhor começo é o fonte do próprio original: nomes, comentários, nada de adivinhar o que é
código e o que é dado. Seja qual for a forma, **primeiro faça-o reproduzir o binário distribuído
byte a byte**, depois siga o arquivo da máquina correspondente para o porte em si.

- **O fonte 6502 original** (Pole Position: o `POLE26.S` da Atari, de 1985). Converta a sintaxe
  do assembler antigo para uma que você consiga rodar (`scripts/atari/pole2dasm.py` -> dasm),
  monte e compare com o dump do cartucho: o do Pole Position bateu, exceto os stubs de troca de
  banco, o que provou que os comentários de "protótipo inacabado" estavam errados. Depois
  `atari-2600.md` §8.3 (rode-o sem mudanças, substitua o kernel).
- **Um disassembly comentado** (River Raid: o de Thomas Jentzsch). Remonte-o (dasm `-f3`,
  `vcs.h`), confira o MD5 com o do cartucho; podem ser necessárias flags de compilação para um
  simulador (`-DTIA_BASE_READ_ADDRESS=48`). Depois `atari-2600.md` §8.2 (rotina por rotina) ou
  §8.3.
- **Fonte de Apple II**: a mesma ideia; a realocação é mais fácil (os rótulos se movem sozinhos),
  mas endereços montados em tempo de execução ainda precisam da busca de `apple-ii.md` §9.2
  passo 4, e o lockstep (execução lado a lado, passo a passo; passo 5) continua valendo: rode o
  binário que o fonte gera contra o distribuído.
- **Sem fonte**: desmonte a ROM (`atari-2600.md` §8.1) ou os arquivos do disco (`apple-ii.md`
  §9.2) até o disassembly remontar idêntico: a partir daí ele *é* o fonte.
- **Outra linguagem** (Queen's Gambit: um motor de xadrez em JavaScript): traduza comando por
  comando para 6502, mantenha o original executável como referência e confira lance a lance
  (abaixo).

## 14. Lições do porte de xadrez (`chess-tk2000`, out/2026)

Um programa em JavaScript (o motor de xadrez de 1 KB de Toledo, modificado por vole.wtf)
traduzido para 6502; a história completa, para pessoas, está em
`docs/guias/05-portando-de-outra-linguagem.md`.

- **Tradução:** primeiro comando por comando, placares de 16 bits (placares de mate pela metade),
  pilha de quadros própria para a recursão, uma chave para desligar o desempate aleatório nos
  testes. Cada melhoria posterior foi testada numa cópia em JavaScript com opções
  (`tools/ordered.js`), medida, depois portada e conferida lance a lance (`tools/check6502.js`,
  0 diferenças).
- **Teste o código que vai ser entregue, não uma versão de teste.** Dois bugs chegaram ao dono do
  projeto embora as verificações do motor estivessem limpas: uma rotina devolvia A mas deixava Z
  de um `ldx` anterior (quem chamava buscava na profundidade 0), e uma auxiliar documentada como
  "preserva A" destruía A (o percurso do livro de aberturas dependia de onde o livro ficava na
  memória; quebrou quando o programa cresceu). Corrigido com um harness que chama qualquer rotina
  do binário real (`enginetest call ENTRY ... w:ADDR:HEX r:ADDR:LEN`; versão genérica nesta
  skill: `scripts/tk2000/harness/call.cpp`), e com verificações que falham no código antigo
  (`tools/checkbook6502.js`, `tools/checklevels.js`).
- **Texto da ROM num jogo:** `sta $C051` (mono), `jsr $FC58` (HOME), caracteres com o bit 7
  ligado para `jsr $FDF0` (COUT), 13 = nova linha, depois `sta $C050`. A ROM usa a página zero
  enquanto imprime (`$32` = máscara de inverso: um ponteiro ali embaralhou o texto); percorra o
  texto com endereçamento absoluto automodificável e inicialize as variáveis de página zero do
  jogo depois da tela de texto. O dono do projeto preferiu esse visual simples de texto da ROM na
  tela de instruções a uma tela desenhada, e nenhuma descrição por nível.
- **Vinhetas:** uma tabela de pares (meio período, contagem) tocada por um laço `Tone`, notas
  longas divididas em várias entradas, entradas `REST` que só esperam; X = (1022727 / (2f) - 11) / 5,
  mais grave ~400 Hz. Fanfarra de vitória 23 bytes, "trombone triste" de derrota 41 bytes. O dono
  do projeto aprovou depois de prévias em WAV e de uma fita de teste com uma posição de mate em
  um (builds `-D TEST=1/2`).
- **Tela de título:** mantenha a tela convertida de 8 KB no repositório (`art/title.bin`),
  carimbe a versão na compilação (`tools/titleversion.py`, `VERSION` no Makefile); a linha de
  status de fita da ROM sobrescreve as linhas 184-191 durante a carga: guarde uma cópia e
  restaure-a no início.
- **Profundidade de busca vs. tempo no 6502** (tempo real do TK2000): 2 meios-lances (plies) 2-6 s, 3 meios-lances
  25-45 s em média (pior caso 2-5 min), 4 meios-lances ~5,7 min em média (pior caso ~16 min): ×7-8 por
  meio-lance. Os níveis misturam profundidades conforme a situação (atrás em material; melhor placar
  com 2 meios-lances abaixo de 0), cada limiar escolhido a partir de taxas de disparo medidas, tempos e
  partidas de 100 jogos.
- **Sem relógio:** a exibição do tempo de pensamento foi abandonada: o tempo do jogador pode ser
  contado no laço de teclado, mas o tempo de busca do computador, estimado pelas posições
  analisadas, errava em até 30% por lance (contando também os passos do laço interno: ±8%, mas
  busca 3-4% mais lenta).
- **Decisões do dono do projeto a lembrar:** nível 2 por padrão; teclas 1-6; "LEVEL n" no painel
  (nomes só na tela de instruções); repositórios privados para qualquer coisa com arte de
  terceiros; arquivo da fita com o nome do jogo (`dist/queens-gambit.ct2`).
