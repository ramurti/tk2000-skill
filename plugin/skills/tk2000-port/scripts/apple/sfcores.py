#!/usr/bin/env python3
"""As cores do Sky Fox no TK2000 (opção B do dono do projeto: céu azul e chão verde, como no Apple).

No Apple o céu é $D5 nas colunas pares e $AA nas ímpares (azul), o chão $2A/$55 (verde). No TK2000
os pares de pontos contam a partir de x = 0 e a paleta vem do byte da esquerda: os mesmos bytes dão
céu ciano e chão azul. A troca depende da coluna, porque o mesmo valor na outra coluna é outra cor
(o vermelho do logo é $AA nas pares e $D5 nas ímpares, e tem de ficar):
    pares:  $D5 -> $2A (azul), $2A -> $55 (verde)
    ímpares: $AA -> $55 (azul), $55 -> $2A (verde)

Onde a troca vale (tipo da tela, pela parte de baixo dela, comparada com uma tela de referência):
    'cabine'   : só dentro da janela (src/janela-mask.bin); e os bytes preto/branco da moldura logo à
                 esquerda da janela perdem o bit 7 (sem degraus ciano);
    'abertura' : a paisagem do título, acima de TEXTO_Y (desenhada pelo mesmo código do voo); abaixo,
                 os nomes: letras brancas sobre o verde (texto(); a tela inicial vem pronta no disco);
    'menu'     : a tela toda (céu azul e chão verde como no Apple; textos em caixas pretas);
    outras     : nada muda.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SWAP = {(0xD5, 0): 0x2A, (0x2A, 0): 0x55, (0xAA, 1): 0x55, (0x55, 1): 0x2A}   # (valor, coluna & 1)
FILL = {0xD5, 0xAA, 0x2A, 0x55}
_jm = os.path.join(ROOT, 'src', 'janela-mask.bin')
JANELA = open(_jm, 'rb').read() if os.path.exists(_jm) else bytes(0x2000)
REFS = {'cabine': ('build/aw/sc0/snap-73.yaml', range(176, 192)),      # em voo: o painel de baixo
        'abertura': ('build/aw/snaps/snap-128.yaml', range(184, 192)),  # o título: "(c)1984 ..."
        'menu': ('src/menu-ref.bin', range(150, 184))}                  # "Joystick Selects ... Mission"


def row(y):
    return (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28


def col(o):
    return (o & 0x7F) % 40


def line(o):
    r = o & 0x7F
    return (r // 40) * 64 + ((o >> 7) & 7) * 8 + ((o >> 10) & 7)


TEXTO_Y = 128                           # abertura: acima, a paisagem (troca por coluna); abaixo, os
                                        # nomes (letras brancas redesenhadas sobre o verde, opção C)


def texto(row40):
    """uma linha dos nomes do título: os pontos brancos (acesos com um vizinho aceso) ficam, o
    resto vira o verde do TK2000 (pontos pares acesos, paleta 0)"""
    bits = [(b >> j) & 1 for b in row40 for j in range(7)]
    new = [1 if bits[x] and ((x > 0 and bits[x - 1]) or (x < 279 and bits[x + 1])) else 1 - (x & 1)
           for x in range(280)]
    return [sum(new[k * 7 + j] << j for j in range(7)) for k in range(40)]


def abertura(page):
    """uma página (8K) da tela do título como fica no TK2000"""
    out = bytearray(page)
    for y in range(192):
        a = row(y)
        if y >= TEXTO_Y:
            out[a:a + 40] = bytes(texto(page[a:a + 40]))
        else:
            for c in range(40):
                out[a + c] = SWAP.get((page[a + c], c & 1), page[a + c])
    return out


def bw(v):
    """preto/branco com o bit 7: nenhum ponto isolado"""
    return bool(v & 0x80) and all(((v >> k) & 1) == 0 or (k > 0 and (v >> (k - 1)) & 1) or
                                  (k < 6 and (v >> (k + 1)) & 1) for k in range(7))


class Screens:
    """o tipo de cada página ($2000, $4000) de uma memória do Apple (ram[]), recalculado com update()"""
    def __init__(self, ram):
        from sftaint import Ap
        from a2boot import Mem
        from py65.devices.mpu6502 import MPU
        import sfboot, dispkg
        self.ram = ram
        self.refs = []
        for kind, (f, ys) in REFS.items():
            offs = [row(y) + c for y in ys for c in range(40)]
            if f.endswith('.bin'):              # uma página da tela, salva (o menu: tools/sfcores.py)
                page = open(os.path.join(ROOT, f), 'rb').read()
                self.refs.append((kind, offs, [page[o] for o in offs]))
                continue
            ap = Ap(open(dispkg.DSK, 'rb').read())
            ap.mpu = MPU(memory=Mem(ap), pc=0)
            sfboot.load_applewin(ap, os.path.join(ROOT, f))
            base = 0x4000 if ap.page2 else 0x2000
            self.refs.append((kind, offs, [ap.ram[base + o] for o in offs]))
        self.kind = {0x2000: None, 0x4000: None}

    def update(self):
        for b in self.kind:
            self.kind[b] = None
            for kind, offs, ref in self.refs:
                if sum(1 for o, r in zip(offs, ref) if self.ram[b + o] == r) >= 0.75 * len(offs):
                    self.kind[b] = kind
                    break

    def of(self, x):
        return self.kind[0x2000 if x < 0x4000 else 0x4000]

    def where(self, x, v):
        """para o rastreio: 'troca' (céu/chão que muda), 'bit7' (moldura), ou None"""
        k, o = self.of(x), x & 0x1FFF
        if k is None:
            return None
        if k == 'abertura' and line(o) >= TEXTO_Y:
            return 'texto'
        if (v, col(o) & 1) in SWAP and (JANELA[o] if k == 'cabine' else True):   # abertura e menu: tudo
            return 'troca'
        if k == 'cabine' and bw(v) and not JANELA[o] and JANELA[(o + 1) & 0x1FFF]:
            return 'bit7'
        return None

    def expect(self, x, v):
        """o byte que o TK2000 deve ter onde o Apple tem v"""
        w = self.where(x, v)
        if w == 'texto':
            a = x - col(x & 0x1FFF)
            return texto([self.ram[a + c] for c in range(40)])[col(x & 0x1FFF)]
        if w == 'troca':
            return SWAP[(v, col(x & 0x1FFF) & 1)]
        if w == 'bit7':
            return v & 0x7F
        return v


class Deferred:
    """julga as escritas na tela só quando a página aparece (a página escondida ainda está sendo
    desenhada: o painel de baixo, que diz o tipo da tela, pode vir depois da janela). put() guarda a
    última escrita de cada endereço; settle() julga as da página mostrada com o tipo dela agora."""
    def __init__(self, ap):
        self.ap = ap
        self.sc = Screens(ap.ram)
        self.pend = {0x2000: {}, 0x4000: {}}

    def put(self, x, v, payload):
        self.pend[0x2000 if x < 0x4000 else 0x4000][x] = (v, payload)

    def settle(self, fn):
        """fn(x, v, payload, where) para cada escrita guardada da página mostrada"""
        self.sc.update()
        b = 0x4000 if self.ap.page2 else 0x2000
        for x, (v, payload) in self.pend[b].items():
            fn(x, v, payload, self.sc.where(x, v))
        self.pend[b].clear()
