# 1. Primeiros passos

Objetivo: montar um programa 6502, colocá-lo numa imagem de fita e vê-lo rodar no emulador.
Cerca de uma hora num Mac (os passos são os mesmos no Linux, com o gerenciador de pacotes dele).

## 1.1 O que você precisa

| Ferramenta | Para quê | Instalação (macOS / Linux Debian-Ubuntu) |
|---|---|---|
| Emulador do TK2000 | Rodar e testar | https://github.com/ramurti/emulador-tk2000 (instalador para macOS ou compilar a partir do fonte) |
| cc65 (`ca65`, `ld65`) | Montar e ligar código 6502 | `brew install cc65` / `apt install cc65` |
| Python 3 | Gerador de fitas e geradores de dados | vem com o macOS / `apt install python3 python3-venv`; crie um venv para o Pillow: `python3 -m venv .venv && .venv/bin/pip install pillow` |
| SDL2 + um compilador C++ | Compilar as ferramentas de teste sem janela a partir do fonte do emulador | `brew install sdl2` + Xcode command line tools / `apt install libsdl2-dev build-essential cmake` |

Mantenha também o **código-fonte** do emulador baixado (por exemplo numa pasta `emulador-tk2000`):
os harnesses de teste (o emulador sem janela, usado para testes) em `tools/harness/` são
compilados com ele, e os arquivos `src/*.cpp` dele são a fonte da verdade sobre como a máquina
se comporta (cores do vídeo, matriz do teclado, formato da fita).

## 1.2 O menor programa útil

[`examples/hello/hello.s`](../../examples/hello/hello.s) mostra as quatro coisas de que todo porte precisa:

1. **Texto pela ROM**, como o BASIC mostra: vídeo monocromático, `HOME` (`$FC58`), `COUT`
   (`$FDF0`).
2. **Alta resolução (hi-res) colorida** na página 1: uma tabela de endereços de linha, um bloco
   branco desenhado com bytes.
3. **Matriz do teclado**: setas e espaço lidos a cada passo.
4. **Alto-falante e ritmo**: um bipe e um laço de espera (não há temporizador).

```sh
cd examples/hello
make            # build/hello.bin e build/hello.ct2
make run        # opcional: uma execução sem janela com duas capturas de tela (precisa de EMU=caminho/do/emulador/src)
```

No emulador: **F2 → Insert tape → `build/hello.ct2`**, digite `LOADT`, Enter, **F6** (Play).
A fita inicia o programa sozinha quando o carregamento termina (veja o [guia 3](03-fitas-e-telas-de-titulo.md)).

## 1.3 Organização de projeto que funcionou duas vezes

```
my-port/
  src/main.s          o programa (STARTUP/CODE em $4000)
  src/*.inc           dados gerados (gráficos, tabelas): nunca edite à mão
  cfg/tk2000.cfg      mapa de memória do ld65
  tools/*.py          geradores (gráficos, tabelas, fita)
  tools/harness/      ferramentas do emulador sem janela (copiadas deste repositório)
  reference/          o original: imagem da ROM, fonte, desmontagem, páginas (com um SOURCE.txt)
  build/              tudo o que é gerado (ignorado pelo git)
  dist/game.ct2       a fita pronta (vai no commit, para que os jogadores não precisem das ferramentas)
  Makefile            um só `make` refaz tudo, inclusive a fita
```

Uma configuração de ligação para um programa em `$4000` com as duas páginas de hi-res livres:

```
MEMORY {
    MAIN: start = $4000, size = $6000, file = %O;    # $4000-$9FFF: 24 KB
}
SEGMENTS {
    STARTUP: load = MAIN, type = ro, start = $4000;  # JMP Start
    CODE:    load = MAIN, type = ro;
    RODATA:  load = MAIN, type = ro;
}
```

Sempre gere um mapa (`ld65 -m build/game.map`) e um arquivo de rótulos (`-Ln build/game.lbl`): o
mapa avisa quando o programa cresce para dentro da página 2 de hi-res em `$A000`; o arquivo de
rótulos deixa as ferramentas de teste chamarem rotinas pelo nome.

## 1.4 Hábitos no ca65 que poupam tempo

- `Y` é um nome reservado: não use como variável de `.repeat` (use `I`).
- Gere as tabelas de endereços na hora da montagem em vez de calculá-las durante a execução:

  ```
  LineLo: .repeat 192, I
          .byte <($2000 + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * 40)
          .endrep
  ```

- Rótulos anônimos (`:`, `:-`, `:+`) dentro de macros quebram os laços em volta deles: use
  rótulos com nome ali.
- Desvio fora de alcance: inverta o desvio e use `jmp`.
- `.assert` pega erros de layout na hora da montagem, por exemplo uma linha de texto que passaria
  da borda da tela: `.assert col + .strlen(text) <= 34, error, "line too long"`.
- Um laço como `ldx #159 / dex / bpl` roda uma vez só (159 é negativo para o `bpl`): conte para
  cima com `inx / cpx #N`.

## 1.5 Próximo passo

Leia o [guia 2](02-a-maquina.md) antes de desenhar qualquer coisa: as cores do TK2000 não são as
do Apple II, e isso decide como todos os gráficos são guardados.
