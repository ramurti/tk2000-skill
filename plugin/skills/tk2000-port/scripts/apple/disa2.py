#!/usr/bin/env python3
"""Desassembla os arquivos binários de Kung Fu Master (build/files, do tools/dos33.py) em fontes
ca65 (build/dis/NAME.s) que montam nos mesmos bytes (make check).

Código = o que o tools/a2boot.py viu rodando (build/*-code.txt: arquivo e endereço de cada instrução
executada) mais o que um rastreio estático alcança dali (desvios não tomados, destinos de JSR/JMP
dentro do arquivo); um caminho rastreado que encontra um opcode ilegal ou o meio de uma instrução é
descartado. O resto é dado (.byte). Rótulos Lxxxx para endereços dentro do arquivo; endereços de E/S
e de ROM do Apple II pelo nome; outros endereços de fora como Lxxxx := $xxxx.

    disa2.py NAME [NAME...]        (padrão: todos os arquivos binários; NAME = A, C, D, ..., ou LOADER:
                                    o carregador do disco em $BB00-$BFFF, de build/play-start.bin)
"""
import glob
import os
import sys

from py65.devices.mpu6502 import MPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BUILD = os.path.join(ROOT, 'build')
OPS = MPU().disassemble
LEN = {'imp': 1, 'acc': 1, 'imm': 2, 'zpg': 2, 'zpx': 2, 'zpy': 2, 'inx': 2, 'iny': 2, 'rel': 2,
       'abs': 3, 'abx': 3, 'aby': 3, 'ind': 3}
FMT = {'imp': '', 'acc': 'a', 'imm': '#%s', 'zpg': '%s', 'zpx': '%s,x', 'zpy': '%s,y',
       'inx': '(%s,x)', 'iny': '(%s),y', 'rel': '%s', 'abs': '%s', 'abx': '%s,x', 'aby': '%s,y',
       'ind': '(%s)'}
END = {'RTS', 'RTI', 'JMP', 'BRK'}
NAMES = {
    0xC000: 'KBD', 0xC010: 'KBDSTRB', 0xC030: 'SPKR', 0xC050: 'TXTCLR', 0xC051: 'TXTSET',
    0xC052: 'MIXCLR', 0xC053: 'MIXSET', 0xC054: 'LOWSCR', 0xC055: 'HISCR', 0xC056: 'LORES',
    0xC057: 'HIRES', 0xC061: 'BUTN0', 0xC062: 'BUTN1', 0xC063: 'BUTN2', 0xC064: 'PADDL0',
    0xC065: 'PADDL1', 0xC070: 'PTRIG', 0xC080: 'LCRAM2', 0xC081: 'LCROM2W', 0xC088: 'LCRAM1',
    0xC08C: 'DISK_Q6L', 0xC08D: 'DISK_Q6H', 0xC08E: 'DISK_Q7L', 0xC08F: 'DISK_Q7H',
    0xC088 + 0: 'LCRAM1', 0xC089: 'DISK_MOTORON', 0xC08A: 'DISK_DRV1',
    0xFDED: 'COUT', 0xFC58: 'HOME', 0xF832: 'CLRSCR', 0xFCA8: 'WAIT', 0xF3F6: 'ROM_F3F6',
}


def units():
    u = {}
    for f in glob.glob(os.path.join(BUILD, 'files', '*_*.bin')):
        name, addr = os.path.basename(f)[:-4].split('_')
        u[name] = (int(addr, 16), open(f, 'rb').read())
    mem = open(os.path.join(BUILD, 'play-start.bin'), 'rb').read()
    u['LOADER'] = (0xBB00, mem[0xBB00:0xC000])
    return u


def coverage(name, base, n):
    cov = set()
    owner = 'boot' if name == 'LOADER' else name
    for f in glob.glob(os.path.join(BUILD, '*-code.txt')):
        for line in open(f):
            o, a = line.split()
            a = int(a, 16)
            if o == owner and base <= a < base + n:
                cov.add(a)
    return cov


def disassemble(name, base, data, seeds=(), tk=None, allow=None, inline=None):
    """allow(a): se dado, só aceita instruções cujos bytes todos ele permite (ex.: os buracos da tela).
    inline: {destino de JSR: n}: sub-rotinas com n bytes de parâmetros depois do JSR (o código continua
    depois deles)"""
    inline = inline or {}
    n = len(data)
    end = base + n

    def ins(a):
        if allow is not None and not all(allow(b) for b in range(a, min(a + 3, end))
                                         if b == a or LEN[OPS[data[a - base]][1]] > b - a):
            return None
        op = data[a - base]
        mn, mode = OPS[op]
        ln = LEN[mode]
        if mn == '???' or a + ln > end:
            return None
        v = data[a - base + 1] | (data[a - base + 2] << 8) if ln == 3 else \
            (data[a - base + 1] if ln == 2 else None)
        if mode == 'rel':
            v = (a + 2 + (v - 256 if v >= 128 else v)) & 0xFFFF
        return mn, mode, ln, v

    def nexts(a, i):
        mn, mode, ln, v = i
        out = []
        if mn == 'JSR' and mode == 'abs' and v in inline:
            k = inline[v]                       # os parâmetros embutidos são dados (n, ou uma função
            if not isinstance(k, int):          # que lê os bytes: k(byte, endereço do JSR))
                k = k(lambda x: data[x - base] if base <= x < end else 0, a)
            out.append(a + ln + k)
        elif mn not in END:
            out.append(a + ln)
        if mode == 'rel' or (mn in ('JSR', 'JMP') and mode == 'abs'):
            out.append(v)
        return [t for t in out if base <= t < end]

    code = {}                                   # endereço -> instrução
    for a in sorted(coverage(name, base, n)):
        i = ins(a)
        if i:
            code[a] = i
    covered = set(code)

    def owned(a):                               # bytes das instruções conhecidas
        s = set()
        for c, i in code.items():
            s.update(range(c, c + i[2]))
        return s

    taken = owned(0)
    work = [t for a in list(code) for t in nexts(a, code[a])]
    work += [t for t in seeds if base <= t < base + n]
    seedset = set(seeds)
    while work:
        start = work.pop()
        if start in code:
            continue
        path, todo, ok, used = {}, [start], True, set()
        while todo and ok:
            a = todo.pop()
            if a in code or a in path:
                continue
            i = ins(a)
            if i is None or any(b in taken or b in used for b in range(a, a + i[2])):
                ok = False
                break
            path[a] = i
            used.update(range(a, a + i[2]))
            todo += nexts(a, i)
        if ok:
            code.update(path)
            taken |= used
        elif start in seedset:              # um ponto de entrada dado: aceita o trecho reto até o
            a = start                       # primeiro problema (os desvios dele seguem a regra estrita)
            while base <= a < end and a not in code:
                i = ins(a)
                if i is None or any(b in taken for b in range(a, a + i[2])):
                    break
                code[a] = i
                taken.update(range(a, a + i[2]))
                work += [t for t in nexts(a, i) if t != a + i[2]]
                if i[0] in END:
                    break
                a += i[2]

    # rótulos: destinos e operandos dentro do arquivo
    labels = set()
    for a, (mn, mode, ln, v) in code.items():
        if v is not None and mode not in ('imm',) and base <= v < end:
            labels.add(v)
    refs = set()
    for a, (mn, mode, ln, v) in code.items():
        if v is not None and mode not in ('imm', 'rel') and not base <= v < end:
            if mode in ('zpg', 'zpx', 'zpy', 'inx', 'iny') or (mode == 'ind' and v < 0x100):
                continue
            refs.add(v)
    starts = set(code)
    inside = {}                                 # rótulo no meio de uma instrução
    for lab in labels:
        if lab in starts:
            continue
        for k in (1, 2):
            c = lab - k
            if c in code and code[c][2] > k:
                inside[lab] = (c, k)
    labels |= {c for c, k in inside.values()}
    lines = ['; Kung Fu Master (Data East, 1985), Apple II: arquivo %s ($%04X-$%04X)' % (name, base, end - 1),
             '; gerado por tools/disa2.py: %d instruções executadas no emulador, mais %d por um rastreio estático'
             % (len(covered & set(code)), len(code) - len(covered & set(code))), '']
    rl = (lambda v: v) if tk is None else reloc
    if tk is not None:
        lines[0] += ', para o TK2000 (tools/relocs.py)'
    for v in sorted(refs):
        lines.append('%-15s := $%04X' % (NAMES.get(v, 'L%04X' % v), rl(v) if v < 0xC000 else v))
    lines += ['', '        .org    $%04X' % rl(base), '']
    tkmode, tk = tk is not None, tk or {}

    def lab(v, mode):
        if base <= v < end:
            if v in inside:
                c, k = inside[v]
                return 'L%04X+%d' % (c, k)
            return 'L%04X' % v
        if mode in ('zpg', 'zpx', 'zpy', 'inx', 'iny'):
            return '$%02X' % v
        s = NAMES.get(v, 'L%04X' % v)
        return s

    a = base
    data_row = []

    def flush():
        if data_row:
            lines.append('        .byte   ' + ','.join('$%02X' % b for b in data_row))
            data_row.clear()

    while a < end:
        if tkmode and a == 0xA000 and base < 0xA000:  # a parte a partir de $A000 vai para $4000
            flush()
            lines += ['', '        .org    $4000', '']
        if a in code:
            flush()
            mn, mode, ln, v = code[a]
            if a in labels and a not in inside:
                lines.append('L%04X:' % a)
            if (mode != 'imm' or a in tk) and any(b in tk for b in range(a, a + ln)):
                raw = [tk.get(b, data[b - base]) for b in range(a, a + ln)]
                orig = ' '.join('%02X' % data[b - base] for b in range(a, a + ln))
                lines.append('        .byte   %s  ; TK2000: era %s (%s)' % (
                    ','.join('$%02X' % b for b in raw), mn.lower(), orig))
                a += ln
                continue
            if mode == 'imm':
                opnd = '#$%02X' % tk.get(a + 1, v)
                if a + 1 in tk:
                    opnd += '  ; TK2000: era $%02X' % v
            elif v is None:
                opnd = 'a' if mode == 'acc' else ''
            else:
                s = lab(v, mode)
                if mode == 'ind' and v < 0x100:  # JMP (página zero): sempre absoluto
                    s = '$%04X' % v
                elif ln == 3 and v < 0x100:     # modo absoluto na página zero: mantém
                    s = 'a:' + s
                opnd = FMT[mode] % s
            note = '' if a in covered else '  ; (rastreado)'
            lines.append(('        %-7s %s' % (mn.lower(), opnd)).rstrip() + note)
            a += ln
        else:
            if a in labels:
                flush()
                lines.append('L%04X:' % a)
            data_row.append(tk.get(a, data[a - base]))
            if len(data_row) == 8:
                flush()
            a += 1
    flush()
    return lines, len(covered), len(code)


def reloc(a):
    """O endereço no TK2000 de um endereço do Apple: $4000-$5FFF e $A000-$BFFF trocam de lugar
    (a página 2 de hi-res fica em $A000 no TK2000)"""
    return a ^ 0xE000 if 0x4000 <= a < 0x6000 or 0xA000 <= a < 0xC000 else a


def calls_into(u, lo, hi):
    """Destinos de JSR/JMP em $lo-$hi a partir dos arquivos residentes (C, D): os pontos de entrada dos overlays"""
    out = set()
    for nm in ('C', 'D'):
        base, data = u[nm]
        for i in range(len(data) - 2):
            if data[i] in (0x20, 0x4C):
                t = data[i + 1] | data[i + 2] << 8
                if lo <= t < hi:
                    out.add(t)
    return out


def handlers(u):
    """{file: code addresses} que o jogo alcança por ponteiros: os tratadores dos registros de
    objetos (tools/records.py), e os ponteiros de tratador / callback definidos com imediatos:
    LDA #lo, STA $C3,X, LDA #hi, STA $C9,X and LDA #lo, STA $02F8 .. LDA #hi, STA $02F9"""
    import records
    out = {}
    for k, f, rec, mask, fields in records.records(u):
        if 11 in fields:
            base, d = u[f]
            a = fields[11] - base
            out.setdefault(f, set()).add(d[a] | d[a + 1] << 8)
    for f, (base, d) in u.items():
        for i in range(len(d) - 8):
            if d[i] == 0xA9 and d[i + 2:i + 4] == bytes([0x95, 0xC3]) and d[i + 4] == 0xA9 and \
                    d[i + 6:i + 8] == bytes([0x95, 0xC9]):
                out.setdefault(f, set()).add(d[i + 1] | d[i + 5] << 8)
        for i in range(len(d) - 12):
            if d[i] == 0xA9 and d[i + 2:i + 5] == bytes([0x8D, 0xF9, 0x02]) and d[i + 5] == 0xA9 and \
                    d[i + 7:i + 10] == bytes([0x8D, 0xF8, 0x02]):
                out.setdefault(f, set()).add(d[i + 6] | d[i + 1] << 8)
    return out


def main():
    tkmode = '--tk' in sys.argv
    iomode = '--io' in sys.argv
    if tkmode:
        sys.argv.remove('--tk')
        import relocs
    if iomode:
        sys.argv.remove('--io')
    u = units()
    entries = calls_into(u, 0xAB00, 0xBB00)
    hand = handlers(u)
    names = sys.argv[1:] or sorted(u)
    os.makedirs(os.path.join(BUILD, 'dis'), exist_ok=True)
    for nm in names:
        base, data = u[nm]
        if nm in ('A', 'F', 'O'):               # imagens hi-res
            continue
        seeds = set()
        if base >= 0xAB00 and nm != 'LOADER':   # overlays: a primeira instrução deles e as
            first = next(i for i, b in enumerate(data) if b)    # chamadas do código residente
            seeds = entries | {base + first}
        seeds = set(seeds) | hand.get(nm, set())
        if nm not in ('D', 'C'):                # tratadores dos registros de D podem ficar em overlays
            seeds |= {a for a in hand.get('D', set()) if a >= 0xAB00}
        tk = relocs.patches(nm, base, data, iomode) if tkmode else None
        lines, cov, tot = disassemble(nm, base, data, seeds, tk)
        out = os.path.join(BUILD, ('tk' if iomode else 'port') if tkmode else 'dis')
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, nm + '.s'), 'w').write('\n'.join(lines) + '\n')
        print('%-6s $%04X-$%04X  %5d bytes  %5d instruções executadas, %5d com o rastreio' % (
            nm, base, base + len(data) - 1, len(data), cov, tot))


if __name__ == '__main__':
    main()
