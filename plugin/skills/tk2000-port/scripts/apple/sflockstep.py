#!/usr/bin/env python3
"""Lockstep do Sky Fox: o original (Apple de 64K do py65) e o porte relocado (mapa de memória do
TK2000, ainda com a E/S do Apple) lado a lado, instrução por instrução, a partir de um estado salvo
do AppleWin, com as mesmas teclas e o mesmo joystick.

O porte: a memória do estado traduzida para o TK2000 (sfrelocs.reloc na RAM principal; o banco do
language card em uso na fase em $D000; as figuras do banco 1 do voo em $C200 + 2 páginas; $E000-$FFFF
igual) e, em cada unidade carregada (tools/dispkg.py), os bytes em que a versão do TK2000
(build/tk/NAME.bin) difere do original. $C100-$FFFF é RAM simples, sem bancos.

Confere depois de cada instrução que o porte está no mesmo lugar (pc = pcmap(pc do original)) e, a
cada CHECK instruções, que a memória bate (bytes de código relocados ficam de fora; um byte alto
relocado ou o deslocamento de página $20 -> $80 contam como iguais). As cargas do disco rodam só no
original; o porte recebe o que elas escreveram, traduzido, e as unidades carregadas na versão TK2000.

    sflockstep.py SNAP.yaml CICLOS [-j SEG:x=..,y=..,b0=..] [-k SEG:TECLA] [-z] [-w ADDR]

-L NOME:T1,T2,...: salva build/lado/NOME-T.png, o Apple II (cores do Apple) | o TK2000, no mesmo instante.
-p ADDR=VAL: muda um byte da memória do estado antes de começar (hex; ex.: -p 4C7E=1, um avião só).
-w ADDR: mostra as escritas em ADDR (um endereço do Apple) nos dois, com o PC e o valor.
-c NOME: confere as cores: cada byte escrito na tela do porte tem de ser o esperado (o do original
com sfrelocs.COLOR_MAP dentro da janela da cabine, src/janela-mask.bin; o bit 7 desligado nos bytes
preto/branco da moldura à esquerda da janela; o resto igual). As diferenças, por instrução que
escreveu, vão para build/cores-check-NOME.txt.
"""
import os, sys
from collections import deque
sys.path.insert(0, os.path.dirname(__file__))
import sfboot, dispkg
from sfrelocs import reloc
from sftaint import Ap
from a2boot import Mem
from py65.devices.mpu6502 import MPU

ROOT = dispkg.ROOT
CHECK = 20000
from sfrelocs import FIG_HI, FIGSPLIT, fig_map
FIGS = {'t18', 't13'}


class Port(Ap):
    """O TK2000 de 64K com a RAM ligada: $C100-$FFFF é RAM simples (E/S do Apple em $C000-$C0FF)."""
    def __init__(self, dsk):
        super().__init__(dsk)
        self.hi = bytearray(0x4000)

    def read(self, addr):
        if 0xC000 <= addr < 0xC100:
            return self.io(addr)
        if addr >= 0xC100:
            return self.hi[addr - 0xC000]
        return self.ram[addr]

    def write(self, addr, v):
        if 0xC000 <= addr < 0xC100:
            self.io(addr)
        elif addr >= 0xC100:
            self.hi[addr - 0xC000] = v
        else:
            self.ram[addr] = v


def tk_render(ram, page2):
    """a página mostrada do porte como o TK2000 a mostra (página 2 em $A000): pares de pontos a partir
    de x = 0, a paleta do byte da esquerda (0: 10 verde, 01 azul; 1: 10 ciano, 01 vermelho)"""
    from PIL import Image
    img = Image.new('RGB', (280, 192))
    px = img.load()
    base = 0xA000 if page2 else 0x2000
    C = {(0, 1, 0): (20, 200, 40), (0, 0, 1): (40, 80, 255), (1, 1, 0): (20, 207, 253), (1, 0, 1): (255, 60, 40)}
    for y in range(192):
        a = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
        bits, pal = [], []
        for k in range(40):
            b = ram[a + k]
            for j in range(7):
                bits.append((b >> j) & 1)
                pal.append(b >> 7)
        for x in range(0, 280, 2):
            l, r = bits[x], bits[x + 1]
            c = (255, 255, 255) if l and r else (0, 0, 0) if not (l or r) else C[(pal[x], l, r)]
            px[x, y] = px[x + 1, y] = c
    return img


def lado(ao, pt, path):
    """-L: o Apple II (cores do Apple) | o TK2000 (o porte), o mesmo instante, em escala 2"""
    from PIL import Image
    ap = sfboot.hgr_img(bytes(ao.ram[:0x6000]), 2 if ao.page2 else 1)
    tk = tk_render(pt.ram, ao.page2)
    out = Image.new('RGB', (280 * 2 + 8, 192), (255, 255, 255))
    out.paste(ap, (0, 0)); out.paste(tk, (288, 0))
    out.resize((out.width * 2, out.height * 2), Image.NEAREST).save(path)
    pa, pk = (0x4000, 0xA000) if ao.page2 else (0x2000, 0x2000)   # e as duas telas (8K cada), para conferir bytes
    open(path[:-4] + '.bin', 'wb').write(bytes(ao.ram[pa:pa + 0x2000]) + bytes(pt.ram[pk:pk + 0x2000]))


def moved(vo, vp):
    return (0x40 <= vo < 0x60 and vp == vo + 0x60) or (0xA0 <= vo < 0xC0 and vp == vo - 0x60) \
        or (vo, vp) == (0x20, 0x80)


def pcmap(pc):
    return reloc(pc) if pc < 0xC000 else pc


def fig_addr(k, unit):
    """o endereço no TK2000 do byte k ($000-$FFF) das figuras do banco 1 (None: página vazia)"""
    return fig_map(0xD000 + k, unit)


def put_figs(pt, data, unit):
    for k in range(0x1000):
        x = fig_addr(k, unit)
        if x is not None:
            pt.write(x, data[k])


class Units:
    """os bytes originais e os da versão TK2000 de cada unidade"""
    def __init__(self, dsk):
        self.src, self.tk = {}, {}
        for nm, (t, base, region, runs) in dispkg.PKGS.items():
            self.src[nm] = dispkg.source(dsk, t, base)
            f = os.path.join(ROOT, 'build', 'tk', nm + '.bin')
            self.tk[nm] = open(f, 'rb').read() if os.path.exists(f) else self.src[nm]

    def which(self, region, base, mem):
        """a unidade de PKGS nessa região e endereço que mais se parece com mem (4K ou o tamanho dela)"""
        best, score = None, 0.5
        for nm, (t, b, r, runs) in dispkg.PKGS.items():
            if r != region or b != base:
                continue
            s = self.src[nm]
            m = sum(1 for k in range(0, len(s), 4) if mem[k] == s[k]) / (len(s) / 4)
            if m > score:
                best, score = nm, m
        return best


def build_port(ao, pt, U):
    for a in range(0xC000):
        pt.ram[reloc(a)] = ao.ram[a]
    if pt.ram[0x20] == 0x20:
        pt.ram[0x20] = 0x80
    import sfrelocs as _sr
    for a in _sr.SMC_PG:                # deslocamentos de página já copiados para imediatos
        if ao.ram[a] == 0x20:
            pt.ram[reloc(a)] = 0x80
    import sfrelocs, dispkg as dk
    res = dk.source(None, ('res', 0x10000), 0)       # a memória depois da carga inicial
    for p in range(0x20, 0x60):                     # código instalado nos buracos depois da carga
        for h in (0x78, 0xF8):
            x = p * 256 + h
            cur = bytes(ao.ram[x:x + 8])
            if cur != res[x:x + 8]:
                pt.ram[reloc(x):reloc(x) + 8] = sfrelocs.snippet(cur)
    sp = ao.mpu.sp                  # endereços de retorno na pilha: um JSR antes do endereço apontado
    for s in range(0x101 + sp, 0x1FF):
        ret = ao.ram[s] | ao.ram[s + 1] << 8
        if (0x4000 <= ret < 0x6000 or 0xA000 <= ret < 0xC000) and ao.ram[(ret - 2) & 0xFFFF] == 0x20:
            pt.ram[s + 1] = reloc(ret) >> 8
    lc1 = U.which('lc1', 0xD000, ao.lc[0])
    lc2 = U.which('lc2', 0xD000, ao.lc[1])
    if lc1 in FIGS:
        put_figs(pt, ao.lc[0], lc1)
        pt.hi[0x1000:0x2000] = ao.lc[1]
        dset = lc2
    elif lc1 == 't25' and lc2 != 't23':
        pt.hi[0x1000:0x2000] = ao.lc[0]
        dset = lc1
    else:
        pt.hi[0x1000:0x2000] = ao.lc[1]
        dset = lc2
    pt.hi[0x2000:0x4000] = ao.lc_hi
    hi1 = U.which('lchi', 0xE000, ao.lc_hi[:0x1000])
    hi2 = U.which('lchi', 0xF000, ao.lc_hi[0x1000:])
    loaded = {}
    for nm, (t, base, region, runs) in dispkg.PKGS.items():   # t7: residente (metade são variáveis)
        if region == 'main':
            n = len(U.src[nm])
            if isinstance(t, tuple) or nm == 't7' or U.which('main', base, ao.ram[base:base + n]) == nm:
                loaded[nm] = base
    for nm in (dset, hi1, hi2):
        if nm:
            loaded[nm] = dispkg.PKGS[nm][1]
    code = set()                    # endereços do Apple (RAM principal) de bytes relocados
    for nm, base in loaded.items():
        s, t = U.src[nm], U.tk[nm]
        for k in range(len(s)):
            if s[k] != t[k]:
                a = base + k
                cur = ao.ram[a] if a < 0xC000 else pt.read(a)
                if a < 0xC000 and cur == s[k]:
                    pt.ram[reloc(a)] = t[k]
                elif a < 0xC000 and s[k] ^ t[k] == 0xE0 and (0x40 <= cur < 0x60 or 0xA0 <= cur < 0xC0) \
                        and not (0x2000 <= a < 0x6000 and (a & 0x7F) >= 0x78):   # buracos: já traduzidos
                    pt.ram[reloc(a)] = cur ^ 0xE0          # um operando reescrito antes do estado salvo
                elif a >= 0xD000:
                    pt.write(a, t[k])
                code.add(a)
    return loaded, code, lc1


def _bw(v):
    """preto/branco com o bit 7: nenhum ponto isolado"""
    return v & 0x80 and all(((v >> k) & 1) == 0 or (k > 0 and (v >> (k - 1)) & 1) or (k < 6 and (v >> (k + 1)) & 1)
                            for k in range(7))


def _yx(x):
    o = x & 0x1FFF
    r = o & 0x7F
    return (r // 40) * 64 + ((o >> 7) & 7) * 8 + (o >> 10), r % 40


class ColorCheck:
    """-c: a tela do porte contra a tela esperada (o original com as cores do TK2000)"""
    def __init__(self, ao, pt, mo, mp, t0):
        from sfrelocs import COLOR_MAP
        from sftaint import JANELA
        from collections import Counter
        self.ao, self.pt, self.mo, self.mp, self.t0 = ao, pt, mo, mp, t0
        self.cmap, self.jan = COLOR_MAP, JANELA
        self.pending = {}                       # endereço do Apple -> (pc original, pc porte)
        self.hits = {}                          # (classe, pc original, pc porte) -> [n, posições, exemplo]
        self.bad = {}                           # endereço -> classe, na tela agora
        import sfcores
        self.sc = sfcores.Screens(ao.ram)
        self.sc.update()                        # o ponto de partida: as telas já com as cores do TK2000
        for x in range(0x2000, 0x6000):         # (no disco a tela do título vem inteira traduzida; aqui
            if (x & 0x7F) < 0x78:               # a memória do AppleWin só bate com ela em parte)
                pt.ram[x if x < 0x4000 else x + 0x6000] = self.sc.expect(x, ao.ram[x])
        self.n = 0
        wo, wp = ao.write, pt.write

        def cwo(x, v):
            if 0x2000 <= x < 0x6000 and (x & 0x7F) < 0x78:
                self.pending[x] = (mo.pc, self.pending.get(x, (0, 0))[1])
            wo(x, v)

        def cwp(x, v):
            ax = x if 0x2000 <= x < 0x4000 else x - 0x6000 if 0xA000 <= x < 0xC000 else None
            if ax is not None and (ax & 0x7F) < 0x78:
                self.pending[ax] = (self.pending.get(ax, (0, 0))[0], mp.pc)
            wp(x, v)
        ao.write, pt.write = cwo, cwp

    def cabine(self):
        self.sc.update()

    def expect(self, x, vo):
        return self.sc.expect(x, vo)

    def classify(self, x):
        vo = self.ao.ram[x]
        vp = self.pt.ram[x if x < 0x4000 else x + 0x6000]
        ex = self.expect(x, vo)
        if vp == ex:
            return None, vo, vp
        if ex & 0x7F == vp & 0x7F and vo not in (0xD5, 0xAA, 0x2A, 0x55):
            return 'bit7', vo, vp
        if vo not in (0xD5, 0xAA, 0x2A, 0x55) and not _bw(vo) and ex == vo:
            return 'mistura', vo, vp            # figura sobre céu/chão já trocados (não se julga)            # figura sobre céu/chão já trocados (não se julga)
        if vp == vo:
            return 'falta troca', vo, vp
        if ex == vo:
            return 'troca a mais', vo, vp
        return 'outro', vo, vp

    def flush(self):
        """julga as escritas guardadas da página mostrada (a escondida ainda está sendo desenhada)"""
        self.cabine()
        b = 0x4000 if self.ao.page2 else 0x2000
        done = [x for x in self.pending if (x >= 0x4000) == (b == 0x4000)]
        for x in done:
            po, pp = self.pending.pop(x)
            c, vo, vp = self.classify(x)
            if c is None:
                self.bad.pop(x, None)
                continue
            self.bad[x] = c
            h = self.hits.setdefault((c, po, pp), [0, set(), None])
            h[0] += 1
            h[1].add(x)
            if h[2] is None:
                h[2] = (x, vo, vp, (self.mo.processorCycles - self.t0) / 1020484)

    def full(self, why):
        self.cabine()
        n = {}
        for x in range(0x2000, 0x6000):
            if (x & 0x7F) >= 0x78:
                continue
            c = self.classify(x)[0]
            if c:
                n[c] = n.get(c, 0) + 1
        if n:
            print('%10d cores depois de %s: %s' % (self.mo.processorCycles, why, n))

    def tkimg(self, get):
        """a página mostrada como no TK2000: pares de pontos a partir de x = 0, a paleta do byte
        da esquerda (0: 10 verde, 01 azul; 1: 10 ciano, 01 vermelho)"""
        from PIL import Image
        img = Image.new('RGB', (280, 192))
        px = img.load()
        base = 0x4000 if self.ao.page2 else 0x2000
        C = {(0, 1, 0): (20, 200, 40), (0, 0, 1): (40, 80, 255), (1, 1, 0): (20, 207, 253), (1, 0, 1): (255, 60, 40)}
        for y in range(192):
            a = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
            bits, pal = [], []
            for k in range(40):
                b = get(a + k)
                for j in range(7):
                    bits.append((b >> j) & 1)
                    pal.append(b >> 7)
            for x in range(0, 280, 2):
                l, r = bits[x], bits[x + 1]
                c = (255, 255, 255) if l and r else (0, 0, 0) if not (l or r) else C[(pal[x], l, r)]
                px[x, y] = px[x + 1, y] = c
        return img

    def shot(self, path):
        from PIL import Image
        self.cabine()
        ex = self.tkimg(lambda x: self.expect(x, self.ao.ram[x]))
        po = self.tkimg(lambda x: self.pt.ram[x if x < 0x4000 else x + 0x6000])
        df = Image.new('RGB', (280, 192))
        a, b, d = ex.load(), po.load(), df.load()
        for y in range(192):
            for x in range(280):
                d[x, y] = (255, 0, 255) if a[x, y] != b[x, y] else tuple(v // 3 for v in a[x, y])
        out = Image.new('RGB', (280 * 3 + 16, 192), (60, 60, 60))
        for k, im in enumerate((ex, po, df)):
            out.paste(im, (k * 288, 0))
        out.resize((out.width * 2, out.height * 2), Image.NEAREST).save(path)

    def report(self, name):
        self.flush()
        import sfrelocs
        out = os.path.join(ROOT, 'build', 'cores-check-%s.txt' % name)
        rows = sorted(self.hits.items(), key=lambda kv: (kv[0][0] == 'mistura', -len(kv[1][1])))
        with open(out, 'w') as f:
            for (c, po, pp), (n, pos, ex) in rows:
                pg = {p & 0x1FFF for p in pos}
                f.write('%-12s orig $%04X porte $%04X  %6d escritas %5d posições' % (c, po, pp, n, len(pg)))
                if ex:
                    y, col = _yx(ex[0])
                    f.write('  ex. $%04X (y %d, col %d) %02X->%02X aos %.2f s' % (ex[0], y, col, ex[1], ex[2], ex[3]))
                f.write('\n')
        tot = {}
        for (c, _, _), (n, pos, _) in rows:
            tot[c] = tot.get(c, 0) + len(pos)
        print('cores: %d instruções com diferença, posições por classe %s -> %s' % (len(rows), tot, out))


def main():
    a = sys.argv[1:]
    dsk = open(dispkg.DSK, 'rb').read()
    U = Units(dsk)
    ao = Ap(dsk)
    mo = MPU(memory=Mem(ao), pc=0)
    mo.cycletime = list(mo.cycletime); mo.cycletime[0xCE] = 6
    ao.mpu = mo; ao.fire_from = 1 << 62; ao.disk_cycles = 32
    sfboot.load_applewin(ao, a[0])
    for k in [k for k in range(len(a)) if a[k] == '-p']:  # -p ADDR=VAL: muda a memória do estado (hex)
        x, _, v = a[k + 1].partition('=')
        ao.ram[int(x, 16)] = int(v, 16)
    t0 = mo.processorCycles
    end = t0 + int(a[1])
    zcheck = '-z' in a
    watch = {int(a[k + 1], 16) for k in range(len(a)) if a[k] == '-w'}
    cname = a[a.index('-c') + 1] if '-c' in a else None
    shots = sorted(float(v) for v in a[a.index('-S') + 1].split(',')) if '-S' in a else []
    lname, _, lt = a[a.index('-L') + 1].partition(':') if '-L' in a else ('', '', '')
    lshots = sorted(float(v) for v in lt.split(',')) if lt else []   # -L NOME:T1,T2: Apple | TK2000
    ev = []
    i = 2
    while i < len(a):
        if a[i] in ('-w', '-c', '-S', '-p', '-L'):
            i += 2
        elif a[i] in ('-k', '-j'):
            t, _, v = a[i + 1].partition(':')
            ev.append((t0 + int(float(t) * 1020484), a[i], v)); i += 2
        else:
            i += 1
    ev.sort()

    pt = Port(dsk)
    mp = MPU(memory=Mem(pt), pc=pcmap(mo.pc))
    mp.cycletime = mo.cycletime
    pt.mpu = mp; pt.fire_from = 1 << 62
    for r in ('a', 'x', 'y', 'sp', 'p', 'processorCycles'):
        setattr(mp, r, getattr(mo, r))
    pt.key = ao.key
    loaded, code, lc1 = build_port(ao, pt, U)
    import sfrelocs
    owned = set()                                       # bytes que o porte acrescenta: fora da conferência
    for x, b in sfrelocs.LAYER.items():
        for k, v in enumerate(b):
            pt.write(x + k, v)
            owned.add(x + k)
    spans = {a: (a + len(old), '') for d in (sfrelocs.CODE, sfrelocs.INCODE) for nm in d
             for a, (old, new) in d[nm].items() if len(old) > 1}   # trechos trocados
    spans.update(sfrelocs.SPANS)
    want = {a: old for d in (sfrelocs.CODE, sfrelocs.INCODE) for nm in d for a, (old, new) in d[nm].items()}
    for d in sfrelocs.INPUT.values():
        for x, io in d:
            want[x] = None, io

    def spanok(x):
        """o trecho vale só se o original tem ali a instrução trocada (outro pacote pode estar no
        mesmo endereço)"""
        w = want.get(x)
        if w is None:
            return True
        if isinstance(w, tuple):
            return mo.memory[x + 1] | mo.memory[x + 2] << 8 == w[1]
        return bytes(mo.memory[x + k] for k in range(len(w))) == w
    print('unidades carregadas:', ' '.join(sorted(loaded)), '| banco 1:', lc1)
    pt.joy, pt.btn = ao.joy, ao.btn                     # o mesmo joystick

    if watch:
        wo, wp = ao.write, pt.write
        wpt = {reloc(x) if x < 0xC000 else x: x for x in watch}

        def wwo(x, v):
            if x in watch:
                print('%10d original $%04X <- $%02X em $%04X' % (mo.processorCycles, x, v, mo.pc))
            wo(x, v)

        def wwp(x, v):
            if x in wpt:
                print('%10d porte    $%04X <- $%02X em $%04X' % (mp.processorCycles, x, v, mp.pc))
            wp(x, v)
        ao.write, pt.write = wwo, wwp
    if cname:
        ck = ColorCheck(ao, pt, mo, mp, t0)
    hist = deque(maxlen=40)
    seen = set()
    steps = 0
    while mo.processorCycles < end:
        while ev and mo.processorCycles >= ev[0][0]:
            _, kind, v = ev.pop(0)
            if kind == '-k':
                ao.key = pt.key = ({'r': 0x0D, 'sp': 0x20, 'esc': 0x1B}.get(v, ord(v[0]))) | 0x80
            else:
                for kv in v.split(','):
                    k, _, n = kv.partition('=')
                    if k in ('x', 'y'): ao.joy['xy'.index(k)] = int(n)
                    else: ao.btn[int(k[1])] = n != '0'
            print('%10d %s %s' % (mo.processorCycles, kind, v))
        if ao.motor:                                    # uma carga: só no original, até o motor parar
            writes = []
            w0 = ao.write

            def wtrace(x, v):
                if x < 0xC000:
                    writes.append(('main', x))
                elif x >= 0xD000 and ao.lc_write:
                    writes.append(('lc%d' % ao.lc_bank if x < 0xE000 else 'lchi', x))
                w0(x, v)
            ao.write = wtrace
            while ao.motor:
                mo.step()
            ao.write = w0
            blocks = set()
            for region, x in writes:
                if region == 'main':
                    pt.ram[reloc(x)] = ao.ram[x]
                    blocks.add(('main', x & 0xF000))
                elif region == 'lc1':
                    v = ao.lc[0][x - 0xD000]
                    blocks.add(('lc1', 0xD000))
                elif region == 'lc2':
                    pt.write(x, ao.lc[1][x - 0xD000])
                    blocks.add(('lc2', 0xD000))
                else:
                    pt.write(x, ao.lc_hi[x - 0xE000])
                    blocks.add(('lchi', x & 0xF000))
            mains = {b for nm_, (t_, b, r_, _) in dispkg.PKGS.items() if r_ == 'main' and not isinstance(t_, tuple)}
            wmain = {x for region, x in writes if region == 'main'}
            blocks = {bl for bl in blocks if bl[0] != 'main'} | {('main', b) for b in mains
                                                                 if any(b <= x < b + 0x1000 for x in wmain)}
            names = []
            for region, base in sorted(blocks):
                mem = ao.ram[base:base + 0x1000] if region == 'main' else (
                    ao.lc[0] if region == 'lc1' else ao.lc[1] if region == 'lc2' else
                    ao.lc_hi[base - 0xE000:base - 0xD000])
                nm = U.which(region, base, mem)
                if region == 'lc1':
                    if nm in FIGS:
                        put_figs(pt, ao.lc[0], nm)
                    else:
                        pt.hi[0x1000:0x2000] = ao.lc[0]
                    lc1 = nm
                if nm:
                    names.append(nm)
                    s, t = U.src[nm], U.tk[nm]
                    for k in range(len(s)):
                        x = base + k
                        if s[k] != t[k]:
                            code.add(x)
                            if region == 'main':
                                pt.ram[reloc(x)] = t[k]
                            elif region != 'lc1' or nm not in FIGS:
                                pt.write(x, t[k])
            import sfrelocs as _sr                      # buracos da tela escritos durante a carga: traduzidos
            for hb in {x & 0xFFF8 for region, x in writes if region == 'main' and 0x2000 <= x < 0x6000
                       and (x & 0x7F) >= 0x78}:
                pt.ram[reloc(hb):reloc(hb) + 8] = _sr.snippet(bytes(ao.ram[hb:hb + 8]))
            for s_ in range(0x101 + mo.sp, 0x1FF):      # a pilha que a carga deixou: retornos traduzidos
                ret = ao.ram[s_] | ao.ram[s_ + 1] << 8
                if (0x4000 <= ret < 0x6000 or 0xA000 <= ret < 0xC000) and ao.ram[(ret - 2) & 0xFFFF] == 0x20:
                    pt.ram[s_ + 1] = reloc(ret) >> 8
            for r in ('a', 'x', 'y', 'sp', 'p', 'processorCycles'):
                setattr(mp, r, getattr(mo, r))
            mp.pc = pcmap(mo.pc)
            scr = sorted({x >> 8 for region, x in writes if region == 'main' and 0x2000 <= x < 0x6000})
            if scr:
                print('%10d carga na tela: páginas %s' % (mo.processorCycles, ' '.join('%02X' % p_ for p_ in scr)))
            print('%10d carga: %s (trilhas %s)' % (mo.processorCycles, ' '.join(names) or '?',
                                                   ','.join(str(t) for c, t in ao.track_log[-12:])))
            if cname:
                ck.full('carga ' + ' '.join(names))
            continue
        hist.append((mo.pc, mp.pc))
        pt.ram[sfrelocs.KEY] = ao.key                   # a entrada do porte: a mesma do original
        pt.ram[sfrelocs.BTN0] = 0x80 if ao.btn[0] else 0
        pt.ram[sfrelocs.BTN1] = 0x80 if ao.btn[1] else 0
        if mo.pc in spans and spanok(mo.pc):            # atravessa o trecho trocado nos dois
            e, sync = spans[mo.pc]
            ends = e if isinstance(e, tuple) else (e,)     # um laço com contagem diferente: as saídas dele
            s0, n0 = mo.pc, 0
            while mo.pc not in ends:
                mo.step()
                n0 += 1
                if n0 == 4000000:
                    print('trecho $%04X: o original não chega ao fim (em $%04X)' % (s0, mo.pc))
                    return 1
            e = mo.pc
            n0 = 0
            while mp.pc != pcmap(e):
                mp.step()
                n0 += 1
                if n0 == 4000000:
                    print('trecho $%04X: o porte não sai por $%04X (em $%04X)' % (s0, e, mp.pc))
                    return 1
            for r in sync:
                setattr(mp, r, getattr(mo, r))
            mp.processorCycles = mo.processorCycles
        else:
            mo.step()
            mp.step()
        steps += 1
        if cname and steps % 3000 == 0 and ck.pending:
            ck.flush()
        if cname and shots and mo.processorCycles - t0 >= shots[0] * 1020484:
            sp_ = os.path.join(ROOT, 'build', 'cores-check-%s-%05.2f.png' % (cname, shots.pop(0)))
            ck.shot(sp_)
            print('captura', sp_)
        if lshots and mo.processorCycles - t0 >= lshots[0] * 1020484:
            os.makedirs(os.path.join(ROOT, 'build', 'lado'), exist_ok=True)
            sp_ = os.path.join(ROOT, 'build', 'lado', '%s-%06.2f.png' % (lname, lshots.pop(0)))
            lado(ao, pt, sp_)
            print('lado a lado', sp_)
        if mp.pc != pcmap(mo.pc) or mp.sp != mo.sp:
            if cname:
                ck.report(cname)
            print('DIVERGIU no ciclo %d (%.2f s): original $%04X, porte $%04X (esperado $%04X)' % (
                mo.processorCycles, (mo.processorCycles - t0) / 1020484, mo.pc, mp.pc, pcmap(mo.pc)))
            for o, p in list(hist)[-14:]:
                print('   orig $%04X  porte $%04X' % (o, p))
            print('   agora A %02X/%02X X %02X/%02X Y %02X/%02X S %02X/%02X' % (mo.a, mp.a, mo.x, mp.x, mo.y, mp.y, mo.sp, mp.sp))
            print('   pilha original', ' '.join('%02X' % ao.ram[0x100 + ((mo.sp - 2 + k) & 0xFF)] for k in range(10)))
            print('   pilha porte   ', ' '.join('%02X' % pt.ram[0x100 + ((mp.sp - 2 + k) & 0xFF)] for k in range(10)))
            print('   bytes original $%04X:' % (mo.pc - 8), ' '.join('%02X' % mo.memory[(mo.pc - 8 + k) & 0xFFFF] for k in range(16)))
            print('   bytes porte    $%04X:' % (mp.pc - 9), ' '.join('%02X' % mp.memory[(mp.pc - 9 + k) & 0xFFFF] for k in range(16)))
            return 1
        if zcheck:
            for x in range(0x100):
                vo, vp = ao.ram[x], pt.ram[x]
                if vo != vp and not moved(vo, vp) and x not in seen:
                    seen.add(x)
                    print('%10d página zero $%02X: %02X/%02X depois de $%04X' % (mo.processorCycles, x, vo, vp, hist[-1][0]))
        if steps % CHECK == 0:
            diffs = []
            for x in range(0xC000):
                if x in code or x in owned or 0x0100 <= x < 0x0200 or (lc1 == "t13" and FIG_HI <= x < FIG_HI + 0xE000 - FIGSPLIT):
                    continue
                vo, vp = ao.ram[x], pt.ram[reloc(x)]
                if 0x2000 <= x < 0x6000 and (vp == sfrelocs.COLOR_MAP.get(vo) or vp == vo & 0x7F):
                    continue                            # as cores do TK2000 (-c confere)
                if vo != vp and not moved(vo, vp):
                    diffs.append((x, vo, vp))
            for x in range(0xE000, 0x10000):
                if x in code:
                    continue
                vo, vp = ao.lc_hi[x - 0xE000], pt.hi[x - 0xC000]
                if vo != vp and not moved(vo, vp):
                    diffs.append((x, vo, vp))
            new = [d for d in diffs if d[0] not in seen]
            if new:
                seen.update(d[0] for d in new)
                print('%10d (%.2f s) memória: %d diferenças, novas: %s' % (
                    mo.processorCycles, (mo.processorCycles - t0) / 1020484, len(diffs),
                    ' '.join('$%04X:%02X/%02X' % d for d in new[:20])))
    print('nenhuma divergência até o ciclo %d (%.1f s)' % (mo.processorCycles, (mo.processorCycles - t0) / 1020484))
    if cname:
        ck.report(cname)
    return 0


if __name__ == '__main__':
    sys.exit(main())
