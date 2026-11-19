# 11. Começando um porte: a primeira mensagem

Você já tem o VS Code com o Claude Code e a skill `tk2000-port` instalados, e o código do emulador
baixado ao lado dos seus projetos (`~/tk2000/emulador-tk2000`, veja o
[guia para iniciantes](00-para-iniciantes.md)). Este guia traz uma primeira mensagem, pronta para
adaptar, para cada tipo de original:

| Você tem | Seção |
|---|---|
| Uma imagem de disco de Apple II (`.dsk`, `.do`, `.po`) | [11.2](#112-um-disco-de-apple-ii-dsk) |
| Uma imagem de cartucho de Atari 2600 (`.a26`, `.bin`) | [11.3](#113-um-cartucho-de-atari-2600-rom) |
| Assembly 6502: o fonte do jogo ou um disassembly comentado | [11.4](#114-assembly-6502-fonte-ou-disassembly-comentado) |
| Um programa em outra linguagem (JavaScript, C, BASIC...) | [11.5](#115-um-programa-em-outra-linguagem-javascript) |

Os exemplos usam jogos que ainda não foram portados; troque os nomes e os caminhos pelos seus.

## 11.1 Antes da mensagem (igual para todos)

1. Crie uma pasta para o jogo ao lado do emulador, com uma pasta `reference/` para o original, e
   copie o original para lá:

   ```sh
   mkdir -p ~/tk2000/meujogo-tk2000/reference
   cp ~/Downloads/<o original> ~/tk2000/meujogo-tk2000/reference/
   ```

2. No VS Code: **File > Open Folder** (Arquivo > Abrir Pasta) e escolha `tk2000/meujogo-tk2000`
   (a pasta do jogo, não a do emulador). Abra o painel do Claude.
3. Cole a mensagem do seu caso, adaptada. Todas pedem o mesmo jeito de trabalhar, que é o que
   faz um porte ficar bom:
   - **primeiro um plano**, depois de um estudo do original, e nada construído antes do seu OK;
   - **passos pequenos**, cada um testado pelo Claude e depois por você;
   - **cores, tela e sons escolhidos por você**, entre 2 e 4 opções ao lado do original;
   - **um README** com o plano, o andamento e as suas decisões, para que qualquer sessão futura
     possa continuar ("continue o porte, leia o README primeiro").

Jogos comerciais têm direitos autorais: guarde o original e o porte para uso pessoal e, no
GitHub, num repositório **privado**.

## 11.2 Um disco de Apple II (.dsk)

```sh
mkdir -p ~/tk2000/loderunner-tk2000/reference
cp ~/Downloads/lode_runner.dsk ~/tk2000/loderunner-tk2000/reference/
```

> Use a skill tk2000-port. Quero portar o jogo Lode Runner, do Apple II, para o TK2000 (64K).
> Tenho a imagem de disco em reference/lode_runner.dsk. O código-fonte do emulador do TK2000
> está em ~/tk2000/emulador-tk2000, e eu jogo no emulador neste computador (macOS).
>
> Sou novo nisso, então trabalhe assim:
> 1. Primeiro confira as minhas ferramentas, monte o projeto e estude o disco: quais arquivos
>    ele tem, como o jogo carrega, quanto de memória usa e se cabe no TK2000. Depois me mostre um
>    plano: as etapas, o que cada uma entrega, como você vai testar e quais escolhas eu vou
>    fazer. Espere o meu OK antes de começar.
> 2. Depois trabalhe um passo pequeno de cada vez: explique em poucas linhas, teste você mesmo
>    no emulador sem janela e pare para eu experimentar.
> 3. Nunca escolha cores, disposição da tela ou sons sozinho: para cada um, me mostre de 2 a 4
>    opções ao lado do original (imagens e WAVs em build/), diga quanto cada uma custa e qual
>    você escolheria, e deixe eu escolher.
> 4. Mantenha no projeto um README com o plano, o que foi feito, o que falta e as decisões que eu
>    tomei.

O que esperar: o Claude extrai os arquivos do disco, dá boot no disco num Apple II simulado e
mostra capturas de tela do original rodando. O plano diz logo se o jogo cabe: um jogo de Apple II
que usa as duas páginas de alta resolução e muito código pode não caber (um estudo do Prince of
Persia parou aí). Se o jogo usa joystick ou paddles, diga que teclas você quer, ou peça opções. O
guia [8](08-portando-um-jogo-de-apple-ii.md) explica o método.

## 11.3 Um cartucho de Atari 2600 (ROM)

```sh
mkdir -p ~/tk2000/pitfall-tk2000/reference
cp ~/Downloads/Pitfall.a26 ~/tk2000/pitfall-tk2000/reference/pitfall.a26
```

> Use a skill tk2000-port. Quero portar o Pitfall! (Activision, Atari 2600) para o TK2000 (64K).
> A imagem do cartucho está em reference/pitfall.a26. O código-fonte do emulador do TK2000 está
> em ~/tk2000/emulador-tk2000, e eu jogo no emulador neste computador (macOS).
>
> Sou novo nisso, então trabalhe assim:
> 1. Primeiro confira as minhas ferramentas, monte o projeto e estude o cartucho: o tamanho, um
>    disassembly que remonte nos mesmos bytes, e o original rodando num simulador, com capturas
>    de tela do início, do jogo e do fim de jogo. Depois me mostre um plano: as etapas, o que
>    cada uma entrega, como você vai testar (comparando com o original, passo a passo) e quais
>    escolhas eu vou fazer. Espere o meu OK antes de começar.
> 2. Depois trabalhe um passo pequeno de cada vez: explique em poucas linhas, teste você mesmo
>    no emulador sem janela e pare para eu experimentar.
> 3. Nunca escolha cores, disposição da tela ou sons sozinho: para cada um, me mostre de 2 a 4
>    opções ao lado do original (imagens e WAVs em build/), diga quanto cada uma custa e qual
>    você escolheria, e deixe eu escolher. A velocidade do jogo (imagens por segundo) também
>    importa para mim: diga quanto cada escolha custa.
> 4. Mantenha no projeto um README com o plano, o que foi feito, o que falta e as decisões que eu
>    tomei.

O que esperar: a lógica do original roda sem mudanças no TK2000 e o Claude escreve só o desenho,
o som e os controles; cada passo é comparado com o cartucho rodando no simulador. O guia
[4](04-portando-um-jogo-de-atari-2600.md) explica o método; o [curso rápido](10-curso-rapido.md)
acompanha um porte de 2600 inteiro.

## 11.4 Assembly 6502: fonte ou disassembly comentado

```sh
mkdir -p ~/tk2000/meujogo-tk2000/reference
cp -r ~/Downloads/meujogo-fonte ~/tk2000/meujogo-tk2000/reference/
cp ~/Downloads/meujogo.a26 ~/tk2000/meujogo-tk2000/reference/    # o binário original, se você tiver
```

> Use a skill tk2000-port. Quero portar <o jogo> (<a máquina original>) para o TK2000 (64K). O
> fonte em 6502 (ou: um disassembly comentado) está em reference/meujogo-fonte, e o binário
> original é reference/meujogo.a26 (ou: não tenho o binário). O código-fonte do emulador do
> TK2000 está em ~/tk2000/emulador-tk2000, e eu jogo no emulador neste computador (macOS).
>
> Sou novo nisso, então trabalhe assim:
> 1. Primeiro confira as minhas ferramentas, monte o projeto e estude o fonte: para qual
>    montador ele foi escrito, se ele monta e se gera exatamente o binário original (se não
>    gerar, me diga o que difere), e como ele usa o hardware da máquina original. Depois me
>    mostre um plano: as etapas, o que cada uma entrega, como você vai testar e quais escolhas eu
>    vou fazer. Espere o meu OK antes de começar.
> 2. Depois trabalhe um passo pequeno de cada vez: explique em poucas linhas, teste você mesmo
>    no emulador sem janela e pare para eu experimentar.
> 3. Nunca escolha cores, disposição da tela ou sons sozinho: para cada um, me mostre de 2 a 4
>    opções ao lado do original (imagens e WAVs em build/), diga quanto cada uma custa e qual
>    você escolheria, e deixe eu escolher.
> 4. Mantenha no projeto um README com o plano, o que foi feito, o que falta e as decisões que eu
>    tomei.

O que esperar: antes de portar qualquer coisa, o fonte é ajustado até gerar exatamente os bytes
do original (o fonte de 1985 do Pole Position e o disassembly do River Raid foram conferidos
assim): daí em diante, qualquer diferença é um erro do porte, não do fonte. Depois o método é o da
máquina original (guia [4](04-portando-um-jogo-de-atari-2600.md) ou
[8](08-portando-um-jogo-de-apple-ii.md)).

## 11.5 Um programa em outra linguagem (JavaScript)

```sh
mkdir -p ~/tk2000/damas-tk2000/reference
cp ~/Downloads/damas.js ~/tk2000/damas-tk2000/reference/
```

> Use a skill tk2000-port. Quero portar um jogo de damas escrito em JavaScript para o TK2000
> (64K). O programa está em reference/damas.js. O código-fonte do emulador do TK2000 está em
> ~/tk2000/emulador-tk2000, e eu jogo no emulador neste computador (macOS).
>
> Sou novo nisso, então trabalhe assim:
> 1. Primeiro confira as minhas ferramentas, monte o projeto e estude o programa: o que ele faz,
>    o tamanho, o que ele precisa que o TK2000 não tem (memória, velocidade, números com casas
>    decimais, gráficos, mouse) e como você vai conferir que a versão do TK2000 joga exatamente
>    como o original. Depois me mostre um plano: as etapas, o que cada uma entrega, como você vai
>    testar e quais escolhas eu vou fazer. Espere o meu OK antes de começar.
> 2. Primeiro traduza fielmente, comando por comando, e só depois deixe mais rápido ou melhor,
>    uma mudança medida de cada vez.
> 3. Trabalhe um passo pequeno de cada vez: explique em poucas linhas, teste você mesmo no
>    emulador sem janela e pare para eu experimentar.
> 4. Nunca escolha cores, disposição da tela ou sons sozinho: para cada um, me mostre de 2 a 4
>    opções (imagens e WAVs em build/), diga quanto cada uma custa e qual você escolheria, e
>    deixe eu escolher.
> 5. Mantenha no projeto um README com o plano, o que foi feito, o que falta e as decisões que eu
>    tomei.

O que esperar: o original continua rodando no computador como referência, e a versão do TK2000 é
conferida com ele jogada a jogada (o porte de xadrez foi comparado em milhares de posições). O
guia [5](05-portando-de-outra-linguagem.md) explica o método.

## 11.6 Depois da primeira mensagem

- Leia o plano com atenção e pergunte o que não entender. Mude agora se quiser algo diferente
  (uma tela de título maior, outras teclas, um som desligado): depois custa mais.
- A cada parada, teste no seu emulador e diga com precisão o que viu.
- Quando o Claude mostrar opções, não tenha pressa: veja as imagens no tamanho real e borradas
  como numa TV, escute os sons ao lado do original. Veja o
  [curso rápido, 5.3](10-curso-rapido.md#53-o-seu-trabalho-mais-importante-escolher-as-cores-e-os-sons).
- No fim de uma sessão: "atualize o README com o que fizemos, o que falta e as minhas decisões".
  No dia seguinte: "continue o porte, leia o README primeiro".

## 11.7 Uma cópia privada no GitHub

Guarde o projeto também no GitHub, num repositório **privado** (só você vê): se o computador
quebrar, nada se perde, e todo passo que você aprovou pode ser recuperado. Privado, porque o
projeto contém a ROM ou o disco do original, que você não pode compartilhar.

1. **Uma conta no GitHub**: crie em https://github.com/signup (gratuita). Se você já tem uma do
   trabalho, crie uma pessoal para os seus portes: não guarde projetos pessoais numa conta de
   trabalho.
2. **Entre pelo terminal**, uma vez (no terminal do VS Code):

   ```sh
   brew install gh            # macOS; no Debian/Ubuntu: sudo apt install gh
   gh auth login              # escolha GitHub.com, HTTPS, e entre pelo navegador
   ```

   Você digita a senha só no navegador, nunca na conversa com o Claude.
3. **Peça ao Claude**, no projeto, algo como:

   > Crie um repositório privado no GitHub para este projeto, na minha conta <seu usuário do
   > GitHub>, com o meu nome e e-mail <nome, e-mail> nos commits deste projeto, faça o primeiro
   > commit e envie (push). Depois confira que o repositório é privado.

   Se você tem mais de uma conta do GitHub neste computador (uma do trabalho, por exemplo), diga
   qual é a dos portes: o Claude configura a identidade só neste projeto e não mexe nas outras.
4. Daí em diante, quando um passo funcionar: "faça o commit e o push". O Claude só faz commit e
   push quando você pede.
