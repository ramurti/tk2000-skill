# Ritmo de quadros sem timer

Os números de seção (§n) são os do guia de porte original, mantidos para que as referências cruzadas funcionem: §1-5 `maquina.md`, §6 `fita-e-disco.md`, §7 `ritmo-de-quadros.md`, §8 e §15 `atari-2600.md`, §9 e §16 `apple-ii.md`, §10-13 `ferramentas.md`, §14 `a-partir-do-fonte.md`. Pastas com nome de projeto (como `enduro-tk2000`) são projetos do autor, não publicados (podem não existir em outra máquina); as ferramentas reutilizáveis estão em `scripts/` da skill (veja `scripts/README.md`).

## 7. Ritmo de quadros sem timer (o problema central do projeto)

Os jogos originais de 2600/Apple supõem uma taxa fixa (2600: um quadro a cada 1/60 s). No TK2000
desenhar um quadro leva mais tempo (River Raid: ~20-24 fps) e varia. A solução do River Raid:

- **Tiques**: rode a lógica original do jogo na taxa nativa dela (um "tique" = um quadro do 2600 =
  17.068 ciclos) e desenhe na taxa que o TK2000 conseguir. Cada imagem desenhada roda tantos
  tiques quanto o tempo gasto exigir (River Raid: 2-3 a ~24 fps, no máximo 6).
- **Contabilidade do custo em ciclos**: como nada mede o tempo, toda rotina soma uma *estimativa*
  dos seus ciclos a um contador `cost` de 16 bits (em unidades de 5 ciclos): fixo por quadro
  (`COST_FRAME`), por tique, por bloco novo, por linha/byte de sprite desenhado, restaurado ou
  composto, por grupo do renderizador, por dígito do placar, por fatia de som... `Pace`
  transforma o custo acumulado em tiques; um quadro mais curto que um tique espera o resto (laço
  de espera ou som).
- **Calibração**: meça os ciclos reais de cada rotina no py65 (`calibrate.py` ajusta os custos
  por mínimos quadrados sobre milhares de quadros, contando os eventos de fora — instrumentar por
  dentro distorce o tempo; `costcheck.py` compara o estimado com o real a cada quadro; um script
  de "rotinas" dá a média de ciclos por chamada). Depois verifique a velocidade do jogo **no
  emulador** contando os tiques por segundo emulado (contador `TICKS16` despejado pelo executor
  sem janela): o alvo é 59,9 tiques/s.
- A CPU do emulador **não** soma os ciclos de cruzamento de página (leituras indexadas, desvios
  para outra página); ela soma +1 por desvio tomado. O py65 conta os cruzamentos de página, então
  o emulador roda ~3-5% mais rápido do que os custos calibrados no py65 preveem. O River Raid
  escala todos os custos para que o emulador mostre ~60 tiques/s (o dono do projeto joga no
  emulador). No hardware real o jogo rodaria, então, alguns por cento mais lento.
- Ajuste de velocidade do jogo = ritmo de quadros; **não** use overclock da CPU.
- **Variante mais simples: dívida de tempo** (Tennis, em que uma imagem custa menos que um
  tique): uma `debt` de 16 bits com sinal (ciclos de tempo real além do tempo do jogo). A cada
  tique: `debt += LOGIC_COST - TICK` (TICK = 17.045); atrasado (`debt > 0`): pule a imagem deste
  tique; senão desenhe e some `DRAW_COST` (uma constante: o custo do desenho quase não varia);
  ainda adiantado: espere em laço, somando os ciclos exatos do laço a cada volta, até
  `debt >= 0`. Trabalho extra raro soma o próprio custo (redesenho do placar, repintura da linha
  lateral, tons). Calibre as constantes medindo os tiques por segundo emulado (o contador de
  quadros despejado pelo executor): Tennis 59,6 em jogo, 58 parado.
- **Variante de saldo com muitos custos variáveis** (Enduro): `Pace` lança o custo estimado de
  cada imagem (parte fixa + por linha de estrada redesenhada + por linha de carro + morros quando
  se mexeram + células do painel + colisões + um bipe temporizado) num saldo de 16 bits em
  unidades de 16 ciclos e roda tiques sem imagem até pagá-lo. **Toda constante de custo precisa
  ser medida de novo depois que uma rotina fica mais rápida**: um teste de colisão mais rápido
  com a constante antiga fez o jogo rodar 1,5% rápido demais (mais tiques pagos do que gastos).
  Meça de novo os tiques/s no py65 e no emulador depois de cada aceleração; o dono do projeto
  preferiu fps a 60 exatos (58-59 tiques/s aceitos).
