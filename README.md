# tk2000-skill

Uma skill do [Claude Code](https://claude.com/claude-code), guias e ferramentas para portar jogos
para o **TK2000**, o micro brasileiro da Microdigital (1984). Tudo isso nasceu de portes reais
feitos com o Claude Code: River Raid, Tennis, Pole Position e Enduro (Atari 2600), Kung Fu Master
(Apple II, a partir de um `.dsk`) e um jogo de xadrez (a partir de JavaScript).
Os portes foram feitos com o Claude Code usando o modelo **Claude Opus 5.5**, de 27/10 a 19/11/2026.

**Nunca usou o Claude nem o VS Code?** Comece por
[0. Para quem está começando do zero](docs/guias/00-para-iniciantes.md): conta no Claude,
instalação, organização das pastas e o primeiro projeto.

| Pasta | Conteúdo |
|---|---|
| `plugin/skills/tk2000-port/` | **A skill do Claude Code**: `SKILL.md` (como começar um porte a partir de uma ROM, de um disco ou de um código-fonte, e como trabalhar com o dono do projeto), `references/` (o guia de porte, por assunto) e `scripts/` (as ferramentas dos portes: fitas, discos e harness do TK2000, Atari 2600, Apple II) |
| `docs/guias/` | **Guias para pessoas** (comece por aqui): para iniciantes, primeiros passos, a máquina, fitas, portes de Atari 2600, outras linguagens, testes, como trabalhar com um agente de IA, portes de Apple II, como instalar a skill e um curso rápido |
| `examples/hello/` | Um programa mínimo (texto pela ROM, alta resolução, teclado, bipe) com Makefile e fita |
| `reference/manuals/` | Manuais do TK2000 digitalizados: técnico, de operação e *Entendendo a ROM* (veja a nota abaixo) |
| `GUIA_DE_PORTE_TK2000.md` | Onde está hoje cada seção do antigo guia em arquivo único |

## Instalar a skill

```sh
claude plugin marketplace add ramurti/tk2000-skill --sparse .claude-plugin plugin
claude plugin install tk2000@tk2000
```

Detalhes em [docs/guias/09-a-skill-do-claude-code.md](docs/guias/09-a-skill-do-claude-code.md);
o passo a passo de um porte inteiro está no [curso rápido](docs/guias/10-curso-rapido.md).
As ferramentas de teste são compiladas a partir do código do emulador:
https://github.com/ramurti/emulador-tk2000 (o emulador de Fabio Belavenuto, *in memoriam*).

## Sobre os manuais

Os manuais em `reference/manuals/` são digitalizações dos manuais originais do TK2000, da
Microdigital Eletrônica. A empresa encerrou as atividades há décadas, e cópias destes manuais
circulam livremente há anos em acervos e sites de preservação. Estão aqui para preservação e
consulta, sem fins comerciais, e não fazem parte da licença GPL deste repositório. Se você detém
direitos sobre eles e prefere que não estejam aqui, abra uma issue que eles serão retirados.

## Jogos e ROMs

Este repositório não contém ROMs nem imagens de disco de jogos comerciais. Os portes citados nos
guias usam cópias que cada pessoa obtém por conta própria; ROMs de jogos comerciais têm direitos
autorais, então guarde seus portes para uso pessoal e, se colocá-los no GitHub, use um repositório
**privado**.

## Licença

GPL v2 (veja [LICENSE](LICENSE)), exceto os manuais digitalizados (veja acima).
