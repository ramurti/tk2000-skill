# Kit de porte para o TK2000

Uma skill do Claude Code (`plugin/`) e guias (`docs/guias/`) para portar jogos para o
Microdigital TK2000, a partir de seis portes concluídos: River Raid, Tennis, Pole Position e Enduro (Atari
2600), Kung Fu Master (Apple II) e um programa de xadrez.

**Comece por [`docs/guias/10-curso-rapido.md`](guias/10-curso-rapido.md)**: instalação do
Claude Code e das ferramentas, instalação desta skill e um primeiro porte passo a passo.
Se você nunca usou o Claude Code, leia antes [`docs/guias/00-para-iniciantes.md`](guias/00-para-iniciantes.md).

Instale a skill a partir do GitHub:

```sh
claude plugin marketplace add ramurti/tk2000-skill --sparse .claude-plugin plugin
claude plugin install tk2000@tk2000
```

Ou a partir de uma cópia local deste repositório (rode na pasta dele):

```sh
claude plugin marketplace add "$(pwd)"
claude plugin install tk2000@tk2000
```
