#!/usr/bin/env python3
"""Estudo de um disco sem catálogo DOS 3.3 (feito para o Sky Fox): dá boot no .dsk no Apple II do a2boot.py (py65, 64K, language card,
Disk II) e registra o que acontece, sem catálogo DOS 3.3 (o crack tem carregador próprio).

    sfboot.py DISK.dsk [-c MAX_CYCLES] [-k CYCLE[:KEY]]... [-s EVERY_CYCLES] [-o PREFIX]

Imprime: as trilhas lidas (com o ciclo), cada salto para uma região nova de memória, a E/S usada,
e no fim o mapa de memória escrita (RAM principal por página de 256 bytes, banco 1 e 2 de $D000,
$E000-$FFFF da language card) e quais páginas foram executadas.
-s: a cada EVERY_CYCLES grava PREFIX-shot-NNN.png com as duas páginas hi-res e a página mostrada.
-L STATE.pkl: continua de um estado salvo (o -c continua contando ciclos absolutos)
-S STATE.pkl: salva o estado (máquina inteira) no fim
-D N: o disco gira de verdade, um nibble a cada N ciclos (32 = Apple II real; sem -D, instantâneo)
-A SNAP.yaml: começa de um estado salvo do AppleWin (Apple II+; awrun.py --snap): RAM, language card,
    CPU, trilha do disco (o motor tem de estar desligado no estado)
-p CYCLE: imprime um perfil das páginas executadas a partir desse ciclo
-o: grava PREFIX-main.bin ($0000-$BFFF), PREFIX-lc1.bin, PREFIX-lc2.bin ($D000-$DFFF de cada
    banco), PREFIX-lchi.bin ($E000-$FFFF) no fim.
"""
import os
import pickle
import sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import a2boot
from a2boot import Apple, Mem, P2D, WRITE_TABLE
from py65.devices.mpu6502 import MPU
from PIL import Image


class Study(Apple):
    def __init__(self, dsk):
        super().__init__(dsk)
        self.w_main = Counter()      # página -> escritas
        self.w_lc = [Counter(), Counter()]
        self.w_hi = Counter()
        self.page2 = False           # página hi-res mostrada (C054/C055)
        self.mixed = False
        self.text = True
        self.track_log = []
        self.last_track = -1
        self.lc_used_read = Counter()

    def write(self, addr, v):
        if addr < 0xC000:
            self.w_main[addr >> 8] += 1
        elif addr >= 0xD000 and self.lc_write:
            if addr < 0xE000:
                self.w_lc[self.lc_bank - 1][addr >> 8] += 1
            else:
                self.w_hi[addr >> 8] += 1
        super().write(addr, v)

    def io(self, addr):
        a = addr & 0xFF
        if a == 0x50: self.text = False
        if a == 0x51: self.text = True
        if a == 0x52: self.mixed = False
        if a == 0x53: self.mixed = True
        if a == 0x54: self.page2 = False
        if a == 0x55: self.page2 = True
        if a == 0xEC and self.motor:
            t = self.ht // 2
            if t != self.last_track:
                self.last_track = t
                self.track_log.append((self.mpu.processorCycles, t))
        return super().io(addr)


def load_applewin(ap, path):
    """Carrega um estado salvo do AppleWin (YAML) no Apple do py65: RAM $0000-$BFFF, os 16K do
    language card ([$0000-$0FFF] banco 1 de $D000, [$1000-$1FFF] banco 2, [$2000-$3FFF] $E000-$FFFF),
    o modo do language card, os registradores e o ciclo, a meia trilha do disco."""
    lines = open(path).read().split('\n')

    def block(start):
        out = bytearray()
        for ln in lines[start + 1:]:
            t = ln.strip()
            if len(t) < 6 or t[4] != ':' or not all(c in '0123456789ABCDEF' for c in t[:4]):
                break
            out += bytes.fromhex(t[6:])
        return out

    def val(key, after=0):
        for ln in lines[after:]:
            if ln.strip().startswith(key + ':'):
                return ln.split(':', 1)[1].strip()
        raise KeyError(key)
    i_main = next(k for k, ln in enumerate(lines) if ln.strip() == 'Main Memory:')
    ap.ram[0:0xC000] = block(i_main)[:0xC000]
    i_lc = next(k for k, ln in enumerate(lines) if ln.strip() == 'Card: Language Card')
    lc = block(next(k for k in range(i_lc, len(lines)) if lines[k].strip() == 'Memory Bank:'))
    ap.lc[0][:] = lc[0x0000:0x1000]
    ap.lc[1][:] = lc[0x1000:0x2000]
    ap.lc_hi[:] = lc[0x2000:0x4000]
    mode = int(val('Memory Mode', i_lc), 16)
    ap.lc_read = bool(mode & 0x20)
    ap.lc_write = bool(mode & 0x400)
    ap.lc_bank = 2 if mode & 0x10 else 1
    i_cpu = next(k for k, ln in enumerate(lines) if ln.strip() == 'CPU:')
    m = ap.mpu
    m.a, m.x, m.y = (int(val(r, i_cpu), 16) for r in ('A', 'X', 'Y'))
    m.p = int(val('P', i_cpu), 16) | 0x30
    m.sp = int(val('S', i_cpu), 16)
    m.pc = int(val('PC', i_cpu), 16)
    m.processorCycles = int(val('Cumulative Cycles', i_cpu), 16)
    i_disk = next(k for k, ln in enumerate(lines) if ln.strip() == 'Card: Disk][')
    if val('Floppy Motor On', i_disk) != 'false':
        sys.exit('o motor do disco está ligado no estado do AppleWin: salve outro momento')
    ap.ht = int(val('Phase', i_disk))
    ap.motor = False
    ap.key = int(val('Last Key', i_cpu), 16) | (0x80 if val('Key Waiting', i_cpu) == 'true' else 0)


def hgr_img(mem, pg):
    """página hi-res como imagem 280x192, cores do Apple (aproximadas)"""
    img = Image.new('RGB', (280, 192))
    px = img.load()
    base = 0x2000 * pg
    for y in range(192):
        a = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
        bits, pal = [], []
        for b in mem[a:a + 40]:
            for k in range(7):
                bits.append((b >> k) & 1)
                pal.append(b >> 7)
        for x in range(280):
            if not bits[x]:
                continue
            l = x > 0 and bits[x - 1]
            r = x < 279 and bits[x + 1]
            if l or r:
                c = (255, 255, 255)
            else:
                c = [[(255, 68, 253), (20, 245, 60)], [(20, 207, 253), (255, 106, 60)]][pal[x]][x & 1]
            px[x, y] = c
    return img


def shot(ap, path):
    p1, p2 = hgr_img(ap.ram, 1), hgr_img(ap.ram, 2)
    img = Image.new('RGB', (280 * 2 + 8, 192 + 12), (60, 60, 60))
    img.paste(p1, (0, 12))
    img.paste(p2, (288, 12))
    # barra em cima da página mostrada
    x0 = 288 if ap.page2 else 0
    for x in range(x0, x0 + 280):
        for y in range(0, 8):
            img.putpixel((x, y), (255, 200, 0) if not ap.text else (120, 120, 255))
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    img.save(path)


def main():
    args = sys.argv[1:]
    dsk = open(args[0], 'rb').read()
    max_cycles, keys, every, prefix = 100_000_000, [], 0, None
    load, save, prof_from = None, None, None
    disk_cycles = 0
    awstate = None
    i = 1
    while i < len(args):
        if args[i] == '-c':
            max_cycles = int(args[i + 1]); i += 2
        elif args[i] == '-k':
            c, _, k = args[i + 1].partition(':')
            code = {'r': 0x0D, 'esc': 0x1B}.get(k, ord(k) if k else 0x20)
            keys.append((int(c), code | 0x80)); i += 2
        elif args[i] == '-s':
            every = int(args[i + 1]); i += 2
        elif args[i] == '-o':
            prefix = args[i + 1]; i += 2
        elif args[i] == '-L':
            load = args[i + 1]; i += 2
        elif args[i] == '-S':
            save = args[i + 1]; i += 2
        elif args[i] == '-A':
            awstate = args[i + 1]; i += 2
        elif args[i] == '-D':
            disk_cycles = int(args[i + 1]); i += 2
        elif args[i] == '-p':
            prof_from = int(args[i + 1]); i += 2
        else:
            sys.exit('desconhecido: ' + args[i])
    if load:
        ap = pickle.load(open(load, 'rb'))
        run(ap, ap.mpu, max_cycles, keys, every, prefix, save, prof_from)
        return
    ap = Study(dsk)
    ap.disk_cycles = disk_cycles
    n = dsk[0]
    for p in range(n):
        ap.ram[0x800 + p * 256:0x900 + p * 256] = dsk[P2D[p] * 256:P2D[p] * 256 + 256]
    ap.ram[0x2B] = 0x60
    for k, v in enumerate(WRITE_TABLE):
        ap.ram[0x02D6 + v] = k
    ap.ram[0x3D] = n
    mpu = MPU(memory=Mem(ap), pc=0x0801)
    mpu.cycletime = list(mpu.cycletime); mpu.cycletime[0xCE] = 6
    ap.mpu = mpu
    ap.fire_from = 1 << 62
    mpu.x = 0x60
    mpu.sp = 0xFF
    if awstate:
        load_applewin(ap, awstate)
    run(ap, mpu, max_cycles, keys, every, prefix, save, prof_from)


def run(ap, mpu, max_cycles, keys, every, prefix, save, prof_from):
    keys.sort()
    exec_pages = Counter()
    prof = Counter()
    region = None
    next_shot = (mpu.processorCycles // every + 1) * every if every else 0
    nshot = mpu.processorCycles // every if every else 0
    while mpu.processorCycles < max_cycles:
        if keys and mpu.processorCycles >= keys[0][0]:
            ap.key = keys[0][1]
            print('%10d tecla %r' % (mpu.processorCycles, chr(keys[0][1] & 0x7F)))
            keys.pop(0)
        pc = mpu.pc
        exec_pages[pc >> 8] += 1
        if prof_from is not None and mpu.processorCycles >= prof_from:
            prof[pc >> 8] += 1
        mpu.step()
        if every and mpu.processorCycles >= next_shot and prefix:
            shot(ap, '%s-shot-%03d.png' % (prefix, nshot))
            nshot += 1
            next_shot += every
        if mpu.pc == pc and ap.read(pc) == 0x4C:
            print('parado em $%04X' % pc)
            break
    print('ciclos', mpu.processorCycles, 'pc $%04X' % mpu.pc)
    if prof:
        tot = sum(prof.values())
        print('perfil (instruções por página):', ' '.join('$%02X00:%d%%' % (p, 100 * c // tot) for p, c in prof.most_common(16)))
    print('trilhas lidas (ciclo:trilha):', ' '.join('%d:%d' % (c // 1000000, t) for c, t in ap.track_log))
    print('E/S usada:', ' '.join('$%04X:%d' % (a, k) for a, k in sorted(ap.io_count.items())))

    def ranges(cnt):
        ps = sorted(cnt)
        out, s = [], None
        for p in ps:
            if s is None:
                s = e = p
            elif p == e + 1:
                e = p
            else:
                out.append((s, e)); s = e = p
        if s is not None:
            out.append((s, e))
        return ' '.join('$%02X00-$%02XFF' % (a, b) for a, b in out) or '(nada)'
    print('RAM principal escrita:', ranges(ap.w_main))
    print('LC banco 1 ($D000) escrito:', ranges(ap.w_lc[0]))
    print('LC banco 2 ($D000) escrito:', ranges(ap.w_lc[1]))
    print('LC $E000-$FFFF escrito:', ranges(ap.w_hi))
    print('páginas executadas:', ranges(exec_pages))
    print('estado de vídeo: texto=%s misto=%s página2=%s' % (ap.text, ap.mixed, ap.page2))
    if prefix:
        open(prefix + '-main.bin', 'wb').write(bytes(ap.ram[:0xC000]))
        open(prefix + '-lc1.bin', 'wb').write(bytes(ap.lc[0]))
        open(prefix + '-lc2.bin', 'wb').write(bytes(ap.lc[1]))
        open(prefix + '-lchi.bin', 'wb').write(bytes(ap.lc_hi))
        shot(ap, prefix + '-end.png')
    if save:
        pickle.dump(ap, open(save, 'wb'))


if __name__ == '__main__':
    main()
