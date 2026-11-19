# 0. Para quem está começando do zero

Este guia é para quem gosta do TK2000 e quer ver um jogo rodando nele, mas nunca usou o Claude,
nunca programou com ajuda de uma inteligência artificial e talvez nunca tenha instalado
ferramentas de programação. Você não precisa saber programar: o Claude escreve o código. O seu
papel é dizer o que quer, testar e decidir como o jogo deve ficar.

Ao final deste guia você terá tudo instalado e o primeiro projeto aberto. Depois, o
[curso rápido](10-curso-rapido.md) acompanha um porte inteiro, passo a passo.

## O que são o Claude, a Anthropic e o Claude Code

- **Anthropic** é a empresa que cria o Claude.
- **Claude** é uma inteligência artificial com quem você conversa em linguagem comum, em
  português. Ela entende pedidos, explica coisas, lê e escreve programas.
- **Claude Code** é o Claude trabalhando dentro do seu computador, numa pasta que você escolhe:
  ele lê os arquivos, roda comandos (montar o jogo, testar no emulador) e escreve código. Antes de
  fazer qualquer coisa ele pede sua permissão.
- **Uma skill** é um pacote de conhecimento que ensina o Claude a fazer uma tarefa específica. A
  skill deste repositório, `tk2000-port`, ensina como funciona o TK2000 e como portar jogos para
  ele, com as ferramentas usadas em seis portes já terminados.
- **VS Code** (Visual Studio Code) é um editor de programas gratuito da Microsoft. O Claude Code
  funciona dentro dele, numa janela de conversa ao lado dos arquivos.

## Passo 1. Crie sua conta no Claude

1. Acesse https://claude.ai e clique em **Sign up** (criar conta). Pode usar seu e-mail ou sua
   conta do Google.
2. Para usar o Claude Code é preciso um **plano pago**: o **Pro** já serve para começar; o **Max**
   dá mais uso por dia. Veja os planos e preços atuais em https://claude.ai/upgrade.
3. Um porte é muitas horas de conversa: de vez em quando você vai bater no limite de uso, e o
   Claude avisa a que horas ele volta. Isso é normal.

## Passo 2. Instale o VS Code e a extensão do Claude Code

1. Baixe o VS Code em https://code.visualstudio.com e instale (Mac, Windows ou Linux).
2. Abra o VS Code. Na barra da esquerda, clique no ícone de **Extensões** (quatro quadradinhos),
   procure por **Claude Code** e instale a extensão publicada pela **Anthropic**.
3. Vai aparecer o ícone do Claude na barra lateral (ou no alto da janela). Clique nele e entre
   com a conta que você criou no passo 1.

Para conferir: abra a conversa do Claude e escreva "olá, você está funcionando?". Ele responde.

## Passo 3. Instale as ferramentas do TK2000

O jogo é montado por ferramentas que rodam no terminal: o montador do 6502 (cc65), o Python, o
git e as bibliotecas para compilar o emulador. No VS Code, abra o terminal pelo menu
**Terminal > New Terminal** (Terminal > Novo Terminal). Cole as linhas abaixo, uma de cada vez.

**Mac:**

```sh
# Homebrew, o instalador de programas do Mac (https://brew.sh)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# as ferramentas
brew install cc65 dasm sdl2 python git cmake
```

Se o Mac pedir para instalar as "Command Line Tools" (ferramentas de linha de comando), aceite.

**Linux (Debian/Ubuntu):**

```sh
sudo apt update
sudo apt install cc65 libsdl2-dev build-essential cmake python3 python3-venv git curl unzip
```

**Windows:** use o WSL (um Linux dentro do Windows: https://learn.microsoft.com/windows/wsl/install)
e siga os passos do Linux dentro dele. Ainda não foi testado; se algo der errado, mostre o erro ao
Claude e peça para ele resolver.

Não sabe se deu certo? Pergunte ao Claude: "confira se cc65, python3, git e cmake estão instalados".

## Passo 4. Instale a skill do TK2000

No terminal do VS Code:

```sh
claude plugin marketplace add ramurti/tk2000-skill --sparse .claude-plugin plugin
claude plugin install tk2000@tk2000
```

Se o comando `claude` não existir no terminal, instale-o com
`curl -fsSL https://claude.ai/install.sh | bash`, feche e abra o terminal de novo, e repita.

## Passo 5. Organize as pastas (isto importa)

O Claude Code trabalha **na pasta que está aberta no VS Code**: é ali que ele lê, cria arquivos e
roda comandos. Por isso, a organização é esta:

```
tk2000/                     uma pasta só para o TK2000, na sua pasta pessoal
  emulador-tk2000/          o código do emulador (as ferramentas de teste são feitas a partir dele)
  meu-jogo-tk2000/          um projeto por jogo, ao lado do emulador
```

Crie a pasta e baixe o código do emulador (no terminal):

```sh
mkdir -p ~/tk2000
git clone https://github.com/ramurti/emulador-tk2000 ~/tk2000/emulador-tk2000
```

**Primeira vez: abra a pasta do emulador.** No VS Code, **File > Open Folder** (Arquivo > Abrir
Pasta) e escolha `tk2000/emulador-tk2000`. Na conversa do Claude, peça:

> Compile este emulador para o meu computador e me diga como abri-lo para jogar.

Assim você fica com o emulador pronto para testar os jogos. É também desse código que o Claude
monta, dentro de cada projeto, a versão sem janela que ele usa para testar sozinho.

**Para cada jogo: abra a pasta do jogo, não a do emulador.** Crie a pasta do projeto (por exemplo
`tk2000/meu-jogo-tk2000`), abra-a com **File > Open Folder** e, na primeira mensagem, diga ao
Claude onde está o emulador ("o código do emulador está em ~/tk2000/emulador-tk2000"). Ele lê de
lá o que precisa (pedindo permissão), e o seu jogo fica separado, com seus próprios arquivos e seu
próprio histórico.

## Passo 6. Comece um porte

Siga o [curso rápido](10-curso-rapido.md) a partir do passo 5: ele leva você pelo porte do
Seaquest (Atari 2600), com a primeira mensagem pronta para colar e o que esperar em cada etapa.

Se o seu original é outro (um disco `.dsk` de Apple II, uma ROM de Atari 2600, um fonte em
assembly 6502 ou um programa em JavaScript), a primeira mensagem pronta para cada caso está em
[11. Começando um porte](11-primeiras-mensagens.md).

## O que faz um porte ficar bom

Duas coisas, e as duas dependem de você:

1. **Um plano antes de começar.** Peça ao Claude para estudar o jogo e mostrar um plano: as
   etapas, o que cada uma entrega, como vai ser testada e quais escolhas você vai fazer. Só
   depois de você concordar ele começa, e trabalha um passo de cada vez, parando para você
   experimentar.
2. **Boas escolhas de cores e de sons.** O TK2000 tem só 6 cores e um alto-falante simples:
   quase nada do jogo original existe nele do mesmo jeito, então cada cor e cada som são uma
   aproximação, e há sempre mais de uma. Peça sempre **opções lado a lado com o original**
   (imagens e sons que você abre e compara), olhe e escute com calma, e escolha. Não deixe o
   Claude decidir sozinho: é aqui que um porte fica bonito ou fica feio. O
   [curso rápido](10-curso-rapido.md#53-o-seu-trabalho-mais-importante-escolher-as-cores-e-os-sons)
   explica como fazer isso bem.

## Dicas para conversar com o Claude

- Fale como falaria com uma pessoa: "o tubarão está rápido demais comparado com o Atari" é ótimo.
- Ele **pede permissão** antes de rodar comandos ou mudar arquivos. Leia e aceite; se algo
  parecer estranho, recuse e explique.
- **Esc** interrompe o que ele está fazendo.
- Ele **esquece entre conversas** o que não está escrito em arquivos. Por isso a skill mantém um
  `README.md` no projeto. Para continuar outro dia: "continue o porte, leia o README primeiro".
- Mande capturas de tela: arraste a imagem para a conversa.
- Ele pode errar com convicção. Pergunte **"como você conferiu isso?"**: uma boa resposta é um
  teste, uma captura de tela ou uma comparação com o original.

## Onde ler mais

- [Curso rápido](10-curso-rapido.md): o primeiro porte, do começo ao fim.
- [1. Primeiros passos](01-primeiros-passos.md) e [2. A máquina](02-a-maquina.md): o TK2000 para
  quem quer entender por dentro.
- [7. Trabalhando com um agente de IA](07-trabalhando-com-um-agente-de-ia.md): o que funcionou e o
  que deu errado nos primeiros portes.
