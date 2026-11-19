# 7. Trabalhando com um agente de IA que programa

Os dois portes foram escritos pelo Claude Code, com o dono do projeto decidindo. O que fez isso
funcionar, e o que deu errado.

## 7.1 Dê o conhecimento ao agente logo de início

- Mantenha uma base de conhecimento que o agente lê antes de um porte novo: neste repositório,
  a skill do Claude Code [`tk2000-port`](../../plugin/skills/tk2000-port/SKILL.md). Peça ao agente
  que a atualize quando um porte ensinar algo novo.
- Deixe o código-fonte do emulador onde o agente possa lê-lo: os arquivos `Video.cpp`,
  `Keyboard.cpp` e `Tape.cpp` respondem às perguntas mais rápido e com mais confiança do que os
  manuais. Os manuais escaneados em `reference/manuals/` não têm camada de texto; o agente
  precisa renderizar as páginas ou usar OCR para lê-los.

## 7.2 Peça passos pequenos e opções

O que o dono do projeto pediu, e o que funcionou:

- **Passos pequenos e testáveis.** Uma funcionalidade por passo, testada antes da próxima.
- **Opções com prós e contras antes de decisões visuais ou de som:** esquemas de cores lado a
  lado, dois estilos de texto para o título, prévias de som em arquivos WAV.
- **Um som de cada vez.** Uma prévia misturando vários efeitos era difícil de avaliar.
- **Números antes das decisões.** "O nível 4 deve buscar mais fundo com até 24 ou com até 32
  peças?" foi respondida com tempos por número de peças; "qual limite para o nível 5?", com
  taxas de acionamento, tempo por lance e partidas de 100 jogos para cada opção.
- **Prévias na pasta `build/` do projeto**, informadas com caminhos absolutos (arquivos em `/tmp`
  eram difíceis de achar).

O dono do projeto muda de ideia (nomes dos níveis no painel, um relógio de tempo de reflexão,
manter a arte original): isso sai barato quando cada passo é pequeno e não vai para um commit
até ser aprovado.

## 7.3 Insista na verificação

- Pergunte "como isto foi conferido?" para cada afirmação. Uma boa resposta é uma verificação
  que compara o porte com uma referência e informa 0 diferenças, e que falha no código antigo.
- As verificações do próprio agente podem deixar passar o que o jogador encontra (veja o
  [guia 6](06-testes-e-verificacao.md#62-teste-o-código-que-vai-para-o-jogador-não-uma-cópia)):
  quando você achar um bug jogando, mande os lances ou uma captura de tela e peça uma verificação
  que o teria pegado.
- Quando o agente disser que um lance ruim relatado é o comportamento do original, ele deve
  mostrar os lances e as avaliações dos dois motores na mesma posição.

## 7.4 Direitos e visibilidade

- Decida cedo se um porte é privado. Jogos comerciais, imagens de cartucho, arte de caixa e arte
  de título ficam privados; dê crédito aos autores na tela de título e no README; publique só
  com permissão.
- Use uma conta e uma identidade pessoais nos repositórios pessoais quando a máquina estiver
  configurada para o trabalho (`user.name`/`user.email` e credential helper por repositório).

## 7.5 Pontos de atenção

- **Operações destrutivas com arquivos.** "Mova os arquivos para o repositório" também apagou a
  pasta original, o que surpreendeu o dono do projeto. Peça ao agente que diga o que vai ser
  apagado ou movido antes de fazer, e que mantenha os originais até você confirmar.
- **Aspas no shell.** Um here-document sem aspas transformou caminhos entre crases em comandos;
  daquela vez não fez estrago, mas scripts que escrevem arquivos devem usar here-documents com
  aspas (`<<'EOF'`).
- **Execuções longas.** Partidas e medições de tempo levam de minutos a horas; peça ao agente que
  as rode em segundo plano e avise quando terminarem, e que mantenha as ferramentas rápidas o
  bastante para iterar (uma verificação que levava 40 minutos foi reescrita para levar 36
  segundos).
