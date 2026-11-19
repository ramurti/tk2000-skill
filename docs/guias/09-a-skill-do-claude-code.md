# 9. A skill do Claude Code: portando com um agente de IA

Tudo o que está nestes guias, mais as ferramentas dos seis portes, está empacotado como um plugin
do Claude Code com uma skill, `tk2000-port`. Com ela instalada, o Claude Code conhece o TK2000
(memória, vídeo, teclado, som, fitas, discos) e as três formas de começar um porte (uma ROM de
Atari 2600, um disco de Apple II, um código-fonte), e tem as ferramentas para copiar para um
projeto novo.

## 9.1 Instalação

Você precisa do [Claude Code](https://claude.com/claude-code). Depois, num terminal:

```sh
claude plugin marketplace add ramurti/tk2000-skill --sparse .claude-plugin plugin
claude plugin install tk2000@tk2000
```

O `--sparse` pula os manuais escaneados (54 MB); deixe-o de fora para baixá-los também. Reinicie
o Claude Code. Atualizações futuras: `claude plugin marketplace update tk2000`, depois
`claude plugin update tk2000@tk2000`.

Instale também as ferramentas da máquina ([guia 1](01-primeiros-passos.md)): o emulador e o
código-fonte dele, o cc65, o Python 3 com um venv (`py65`, `pillow`), o SDL2; o `dasm` para jogos
de Atari 2600.

## 9.2 Começando um porte

Crie uma pasta vazia para o jogo, ponha o original em `reference/` (o `.a26`/`.bin`, o `.dsk` ou
o código-fonte), abra o Claude Code ali e diga o que você quer, por exemplo:

> Porte para o TK2000 o jogo de Apple II que está em reference/lode.dsk.

O Claude carrega a skill sozinho (ou digite `/tk2000-port`). Ele vai montar o projeto, reproduzir
o original byte a byte e depois trabalhar em passos pequenos, mostrando capturas de tela, esboços
e prévias de som antes de cada decisão. A sua parte: jogar cada versão no emulador, decidir cores
e sons e dizer o que está errado ([guia 7](07-trabalhando-com-um-agente-de-ia.md)).

## 9.3 O que esperar

- Uma primeira versão jogável: cerca de um dia de sessões para um jogo do tamanho do Tennis ou do
  Kung Fu Master; as melhorias (som, música, menus) vêm depois, uma de cada vez.
- Jogos comerciais, ROMs e imagens de disco ficam em repositórios **privados**.
- A skill é a experiência dos portes, não uma garantia: cada jogo tem suas próprias surpresas.
  Quando aprender algo novo, acrescente aos `references/` da skill (pull requests são bem-vindos).
