# 10. Curso rápido: seu primeiro porte para o TK2000 com o Claude Code

Para entusiastas do TK2000 que nunca usaram o Claude Code, no macOS ou no Linux. Se você nunca
usou o Claude nem o VS Code, leia antes o guia [00. Para iniciantes](00-para-iniciantes.md). Você
não precisa saber assembly 6502 nem Python: o Claude escreve o código, você decide como o jogo
deve ficar na tela e no som, e testa. O exemplo do começo ao fim é o **Seaquest** (Activision,
1983, um cartucho de 4K do Atari 2600).

## Passo 1. O que você precisa

- Um **Mac ou um PC com Linux** (os comandos abaixo são para Debian/Ubuntu; outras distribuições
  têm os mesmos pacotes com nomes parecidos). Os primeiros portes foram feitos no macOS; o suporte
  do emulador e das ferramentas ao Linux está sendo adaptado, então, se algo falhar no Linux,
  mostre o erro ao Claude e peça para ele corrigir. No Windows, use o WSL (Ubuntu) e siga os
  passos do Linux (ainda não testado).
- Uma assinatura do Claude (claude.ai). O Pro funciona; um porte são muitas horas de conversa,
  então de vez em quando você vai bater nos limites de uso (o Claude Code avisa quando eles
  renovam). O Max dá mais.
- Cerca de 2 GB de espaço em disco e paciência: uma primeira versão jogável leva um ou dois dias
  de sessões, não minutos.

## Passo 2. Instale as ferramentas (uma vez só)

Abra um terminal e cole estes comandos, uma linha de cada vez.

**macOS:**

```sh
# Homebrew, se você ainda não tem (https://brew.sh)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# os montadores, a biblioteca do emulador, Python
brew install cc65 dasm sdl2 python git cmake
```

**Linux (Debian/Ubuntu):**

```sh
sudo apt update
sudo apt install cc65 libsdl2-dev build-essential cmake python3 python3-venv git curl unzip
```

O `dasm` (o montador do Atari 2600) pode não estar empacotado: se `sudo apt install dasm` falhar,
baixe a versão para Linux em https://github.com/dasm-assembler/dasm/releases e copie o `dasm`
para `~/.local/bin` (ou peça ao Claude para fazer isso).

**Nos dois:**

```sh
# Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# o emulador do TK2000, em código-fonte (as ferramentas de teste são compiladas a partir dele)
mkdir -p ~/tk2000 && git clone https://github.com/ramurti/emulador-tk2000 ~/tk2000/emulador-tk2000
```

Para jogar, você precisa do próprio emulador: no macOS há um instalador (`.dmg`) em
https://github.com/ramurti/emulador-tk2000; no Linux, compile-o a partir do código-fonte que você
acabou de clonar (ele usa CMake e SDL2). O mais fácil nos dois: inicie o `claude` em
`~/tk2000/emulador-tk2000` e diga "compile este emulador para a minha máquina e me diga como
rodá-lo".

Depois rode `claude` uma vez no Terminal e entre com a sua conta do Claude.

## Passo 3. Instale a skill do TK2000 (uma vez só)

A skill é o que transforma o Claude num portador de jogos para o TK2000: os detalhes da máquina,
as formas de portar um jogo e as ferramentas de seis portes terminados.

Ela está no repositório público `ramurti/tk2000-skill` no GitHub:

```sh
claude plugin marketplace add ramurti/tk2000-skill --sparse .claude-plugin plugin
claude plugin install tk2000@tk2000
```

**Alternativa sem acesso à internet: se você recebeu o kit num arquivo zip** (`tk2000-kit.zip`):

```sh
mkdir -p ~/tk2000 && cd ~/tk2000 && unzip ~/Downloads/tk2000-kit.zip
claude plugin marketplace add ~/tk2000/tk2000-kit
claude plugin install tk2000@tk2000
```

Nesse caso, deixe a pasta `tk2000-kit` onde ela está: o Claude Code lê a skill dela.

Para conferir, inicie o `claude` e digite `/plugin`: o `tk2000` deve aparecer como instalado.

## Passo 4. O Claude Code em dez minutos

- Você **conversa em linguagem comum**, em português ou em inglês. O Claude lê arquivos, roda
  comandos e escreve código na pasta onde você o iniciou.
- **Ele pergunta antes de agir**: rodar um comando ou editar um arquivo mostra um pedido de
  permissão. Leia, depois permita (ou "permitir e não perguntar de novo" para comandos inofensivos,
  como compilações). Se algo parecer errado, diga não e explique por quê.
- **Esc** interrompe o Claude no meio de alguma coisa. Depois é só digitar o que você quer no
  lugar.
- **Shift+Tab** troca de modo; o "plan mode" faz o Claude propor um plano antes de mexer nos
  arquivos: útil para passos grandes.
- **Ele esquece entre uma sessão e outra**, menos o que está escrito em arquivos. É por isso que a
  skill pede que ele mantenha o `README.md` do projeto em dia. Para continuar no dia seguinte,
  inicie o `claude` na mesma pasta e digite `/resume` (escolha a última conversa), ou diga
  "continue o porte do Seaquest, leia o README primeiro".
- `/clear` começa uma conversa nova (quando a atual ficar longa ou mudar de assunto). `/help`
  lista o resto.
- Você pode arrastar uma captura de tela para a janela do Terminal para mostrar ao Claude o que
  você está vendo.
- O Claude pode errar com convicção. Pergunte **"como você conferiu isso?"**. Uma boa resposta é
  um teste, uma captura de tela ou uma comparação com o original.

## Passo 5. Seu primeiro porte: Seaquest

### 5.1 Prepare a pasta

```sh
mkdir -p ~/tk2000/seaquest-tk2000/reference
```

Baixe a imagem do cartucho
(https://github.com/mratari2600/Atari-2600/blob/master/Seaquest%20(USA).zip, "Download raw
file"), descompacte e copie o arquivo `.a26` para `~/tk2000/seaquest-tk2000/reference/` com o
nome `seaquest.a26`. (Ou passe o link ao Claude e deixe que ele faça isso.)

Imagens de ROM de jogos comerciais têm direitos autorais: mantenha o porte para uso pessoal e,
se for colocá-lo no GitHub, use um repositório **privado**.

### 5.2 A primeira conversa

```sh
cd ~/tk2000/seaquest-tk2000
claude
```

Depois cole algo assim (adapte os caminhos e o sistema):

> Use a skill tk2000-port. Quero portar o Seaquest da Activision (Atari 2600) para o TK2000
> (64K). O cartucho é reference/seaquest.a26. O código-fonte do emulador está em
> ~/tk2000/emulador-tk2000 e eu jogo no emulador do TK2000 neste computador
> (macOS / Linux).
>
> Sou novo no Claude Code e em portes, então: primeiro estude o jogo e me mostre um plano (as
> etapas, o que cada uma entrega, como você vai testar e quais escolhas eu vou fazer) e espere o
> meu OK. Depois trabalhe um passo pequeno de cada vez: explique em poucas linhas, teste você
> mesmo no emulador sem janela e pare depois de cada um para eu experimentar. Nunca escolha
> cores, disposição da tela ou sons sozinho: para cada um, me mostre de 2 a 4 opções ao lado do
> original (imagens e arquivos WAV na pasta build/ do projeto), diga quanto cada uma custa e
> qual você escolheria, e deixe eu escolher. Mantenha no projeto um README com o plano, o que foi
> feito e o que vem a seguir.
>
> Comece conferindo as minhas ferramentas e montando o projeto.

### 5.3 O seu trabalho mais importante: escolher as cores e os sons

O TK2000 tem só 6 cores, com limites a cada 7 pixels, e um alto-falante que só sabe dar
cliques. Quase nenhuma cor ou som do original existe nele do jeito que é: cada um precisa ser
aproximado, e sempre há vários jeitos de fazer isso, cada um com seus compromissos (uma cor
misturada que fica certa numa TV mas listrada de perto, um som mais rico que custa velocidade). A
primeira tentativa raramente é a melhor. **É aqui que um porte fica bom ou medíocre, e isso
depende de você**, não do código.

- Para cada cor (céu, chão, objetos, cada fase ou hora do dia), cada efeito sonoro, a música e a
  tela de título, peça **opções lado a lado com o original** e escolha. O Claude as faz como
  imagens e arquivos WAV em `build/`; abra, olhe e escute.
- Veja as imagens no tamanho real e também borradas "como numa TV" (peça as duas): as cores
  misturadas foram feitas para serem vistas numa TV.
- Escute os sons ao lado do WAV do original, mais de uma vez, e também no jogo: um som que parece
  bom sozinho pode cansar depois de dez minutos.
- Se nenhuma opção estiver boa, diga o que incomoda e peça outras. Se não conseguir decidir entre
  duas, peça as duas em fitas e jogue um pouco com cada uma.
- Não tenha pressa aqui: um porte é jogado por anos; uma cor ou um som escolhido às pressas vai
  incomodar toda vez.

### 5.4 O que acontece em seguida, e o que dizer

Um porte passa por estas etapas. Cada uma leva um ou mais passos; depois de cada passo, o Claude
para e você testa. Exemplos de mensagens entre aspas.

0. **O plano**: o Claude estuda o jogo e propõe as etapas e as escolhas que você vai fazer. Leia,
   pergunte o que não entender e dê o OK (ou diga o que mudar).
1. **Preparação**: as pastas do projeto, um ambiente Python, o emulador de testes sem janela
   compilado.
2. **O original, reproduzido**: o Claude desmonta o cartucho até ele remontar nos mesmos bytes e
   o roda num pequeno simulador de Atari 2600. Você vai ver capturas de tela do jogo original.
   *"Me mostre capturas de tela do início, do jogo e do game over."*
3. **O plano da tela**: como o quadro do 2600 vira imagem na tela de 280 × 192 do TK2000 e nas cores dele
   (o TK2000 tem só preto, branco, verde, azul, ciano e vermelho, com limites a cada 7 pixels).
   *"Me mostre opções para o mar e o submarino lado a lado com o original, nítidas e borradas
   como numa TV."*
4. **Uma primeira imagem no TK2000**: uma fita que mostra a cena parada. Carregue-a no seu
   emulador: F2 (menu) -> insira a fita `.ct2`, digite `LOADT` e RETURN, aperte F6 (play).
5. **O jogo rodando**: a lógica original roda e o código do Claude desenha; depois, a velocidade
   (o TK2000 não tem timer, então a velocidade é contada em ciclos da CPU). *"Os tubarões estão
   rápidos demais em comparação com o Atari"* é exatamente o retorno de que ele precisa.
6. **Controles**: setas e SPACE. *"Dá para atirar com a tecla de ponto também?"*
7. **Sons, um de cada vez**: para cada som o Claude faz um WAV do original e duas ou três opções
   para o TK2000; você escolhe, e depois ele grava o jogo de verdade para confirmar. *"O torpedo
   soa como um clique, dá para ele ser mais longo?"*
8. **Tela de título e a fita**: uma imagem de carregamento, uma tela de início, o `.ct2` final, um
   `.wav` para um TK2000 de verdade (toque-o na entrada de cassete) e uma pasta `dist/`.

Ao fim de cada sessão de trabalho: *"Atualize o README com o que fizemos, o que está pendente e
as decisões que eu tomei."*

### 5.5 Bons hábitos

- **Teste cada versão no seu emulador** e diga o que viu, com precisão: "depois do terceiro
  tubarão, a metade de cima da tela pisca" é melhor que "está com bug". Uma captura de tela é
  melhor ainda.
- **Uma coisa de cada vez.** Se você pedir cinco mudanças de uma vez, testar fica confuso.
- **Você decide a imagem e o som**; o Claude decide o código. Se não gostar de algo, diga: mudar
  um passo ainda não testado e sem commit sai barato.
- Peça **commits no git** quando um passo funcionar ("faça o commit disto"), para poder sempre
  voltar atrás.
- Se a conversa ficar longa ou confusa, use `/clear` e recomece com "continue o porte do
  Seaquest, leia o README".

## Passo 6. Quando você aprender algo

Cada porte ensina algo novo. Peça ao Claude que escreva isso no README do projeto, e mande para o
autor do kit: a skill fica melhor para o próximo porte.

## Onde ler mais

- [1. Primeiros passos](01-primeiros-passos.md) e [2. A máquina](02-a-maquina.md): o TK2000 para
  programadores.
- [4. Portes de Atari 2600](04-portando-um-jogo-de-atari-2600.md), [8. Portes de Apple II](08-portando-um-jogo-de-apple-ii.md).
- [7. Trabalhando com um agente de IA que programa](07-trabalhando-com-um-agente-de-ia.md): o que
  funcionou e o que deu errado nos primeiros portes.

Para outros originais (um `.dsk` de Apple II, um fonte em 6502, JavaScript), a primeira mensagem está em
[11. Começando um porte](11-primeiras-mensagens.md).
