"""Um pequeno Atari 2600 para trabalho de referência (copiado do porte do Pole Position): o py65
roda o cartucho (reference/tennis.a26; 2K ou 4K sem troca de bancos, ou 8K com troca de bancos F8
como no Pole Position) e uma TIA desenha a imagem color clock a color clock a partir das escritas
nos registradores, no tempo do ciclo de CPU de cada escrita. Basta para capturas de tela,
registros por linha e colisões; não é exato no ciclo em todos os cantos (sem HMOVE durante a
linha visível, sem escritas atrasadas no playfield, tempo de RESPx simplificado).

    m = VCS(); m.frame(); img = m.image()        # imagem do Pillow, 160 x linhas, pixels do 2600
"""
import os
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
ROM = os.path.join(ROOT, 'reference', 'tennis.a26')
SYM = os.path.join(ROOT, 'build', 'ref', 'tennis.sym')

# paleta NTSC (aproximada): matiz 0 = cinzas, matizes 1-15 ao redor do círculo de cores
def _palette():
    import colorsys
    pal = []
    for c in range(128):
        hue, lum = c >> 3, c & 7
        y = 0.08 + lum / 7 * 0.84
        if hue == 0:
            r = g = b = y
        else:
            # matiz 1 = dourado, depois ao redor do círculo em passos de 24 graus (ordem parecida com a do Stella)
            h = (0.155 - (hue - 1) * (1 / 15)) % 1.0
            r, g, b = colorsys.hls_to_rgb(h, y * 0.92, 0.75)
        pal.append(tuple(int(max(0, min(1, v)) * 255) for v in (r, g, b)))
    return pal

PALETTE = _palette()

# number-size: deslocamentos das cópias (em pixels) e multiplicador de largura dos players
NUSIZ_COPIES = {0: (0,), 1: (0, 16), 2: (0, 32), 3: (0, 16, 32), 4: (0, 64), 5: (0,), 6: (0, 32, 64), 7: (0,)}
NUSIZ_SCALE = {5: 2, 7: 4}


def load_symbols(path=SYM):
    syms = {}
    if os.path.exists(path):
        for line in open(path):
            parts = line.split()
            if len(parts) >= 2 and not line.startswith('---'):
                try:
                    syms[parts[0]] = int(parts[1], 16)
                except ValueError:
                    pass
    return syms


class TIA:
    def __init__(self):
        self.r = [0] * 64
        self.pos = {'P0': 0, 'P1': 0, 'M0': 0, 'M1': 0, 'BL': 0}
        self.grp_old = [0, 0]
        self.enabl_old = 0
        self.cx = 0                             # bits de colisão, veja CX abaixo
        self.events = []                        # (color clock no quadro, reg, valor)

    # pares de colisão -> (registrador, bit)
    CX = {('M0', 'P1'): (0, 7), ('M0', 'P0'): (0, 6), ('M1', 'P0'): (1, 7), ('M1', 'P1'): (1, 6),
          ('P0', 'PF'): (2, 7), ('P0', 'BL'): (2, 6), ('P1', 'PF'): (3, 7), ('P1', 'BL'): (3, 6),
          ('M0', 'PF'): (4, 7), ('M0', 'BL'): (4, 6), ('M1', 'PF'): (5, 7), ('M1', 'BL'): (5, 6),
          ('BL', 'PF'): (6, 7), ('P0', 'P1'): (7, 7), ('M0', 'M1'): (7, 6)}

    def read_cx(self, reg):
        v = 0
        for pair, (r, bit) in self.CX.items():
            if r == reg and self.cx & (1 << (r * 2 + (bit - 6))):
                v |= 1 << bit
        return v


class Memory:
    def __init__(self, m):
        self.m = m

    def __len__(self):
        return 0x10000

    def __getitem__(self, addr):
        if isinstance(addr, slice):
            return [self[i] for i in range(*addr.indices(0x10000))]
        m = self.m
        a = addr & 0x1FFF
        if a & 0x1000:
            m.bankswitch(a)
            off = m.rom_offset(a)
            m.reads.add(off)
            return m.rom[off]
        if a & 0x80 and not a & 0x200:
            return m.ram[a & 0x7F]
        if not a & 0x80:                        # leituras da TIA
            reg = a & 0x0F
            if reg < 8:
                return m.tia.read_cx(reg)
            if reg == 0x0C:
                return 0x00 if m.fire else 0x80
            if reg == 0x0D:
                return 0x80
            return 0x00
        reg = a & 0x07                          # RIOT
        if reg == 0:
            return m.swcha
        if reg == 2:
            return m.swchb
        if reg == 4:                            # INTIM
            return m.intim()
        return 0x00

    def __setitem__(self, addr, value):
        self._set(addr, value)
        if self.m._brk:                         # BRK: os três empilhamentos dele ficam a um ciclo um do outro
            self.m._cur_cycles += 1

    def _set(self, addr, value):
        m = self.m
        a = addr & 0x1FFF
        value &= 0xFF
        if a & 0x1000:
            m.bankswitch(a)
            return
        if a & 0x80 and not a & 0x200:
            m.ram[a & 0x7F] = value
            return
        if not a & 0x80:
            m.tia_write(a & 0x3F, value)
            return
        reg = a & 0x1F                          # escritas no temporizador do RIOT
        if reg in (0x14, 0x15, 0x16, 0x17):
            m.timer_set(value, {0x14: 1, 0x15: 8, 0x16: 64, 0x17: 1024}[reg])


class VCS:
    def rom_offset(self, a):
        """o byte da ROM que o endereço a do cartucho ($1000-$1FFF) lê"""
        n = len(self.rom)
        if n == 8192:
            return self.bank * 0x1000 + (a & 0x0FFF)
        return a & (n - 1)

    def bankswitch(self, a):
        """F8 (8K): qualquer acesso a $1FF8 seleciona o banco 0, a $1FF9 o banco 1"""
        if len(self.rom) == 8192 and a in (0x1FF8, 0x1FF9):
            self.bank = a - 0x1FF8

    def __init__(self, rom_path=ROM):
        self.rom = open(rom_path, 'rb').read()
        assert len(self.rom) in (2048, 4096, 8192), 'só cartuchos de 2K, 4K e 8K (F8)'
        self.bank = 1                           # cartuchos F8 começam no último banco
        self.reads = set()                      # deslocamentos da ROM lidos (código e dados)
        self.ram = bytearray(128)
        self.syms = load_symbols()
        self.swcha = 0xFF                       # joystick solto
        self.swchb = 0x0B                       # cor, RESET/SELECT soltos
        self.fire = False
        self.tia = TIA()
        self.mpu = MPU(memory=Memory(self))
        self.mpu.cycletime = list(self.mpu.cycletime)
        self.mpu.cycletime[0xCE] = 6            # o py65 conta DEC abs como 3 ciclos
        self.mpu.pc = self.rom[self.rom_offset(0x1FFC)] | self.rom[self.rom_offset(0x1FFD)] << 8
        self.mpu.sp = 0xFF
        self.timer_at, self.timer_val, self.timer_div = 0, 0, 1024
        self.frame_start = 0                    # ciclo de CPU do fim do último VSYNC
        self.lines = []                         # último quadro: lista de linhas de 160 pixels (índices da paleta)
        self.vblank_lines = []
        self.states = []                        # último quadro, por linha: (posições x dos objetos, registradores da TIA) no pixel 0
        self.wait_vsync = False
        self.line_writes = []                   # último quadro: (ciclo, reg, valor)
        self._writes = []
        self._cur_cycles = 0                    # ciclo de CPU da escrita atual (veja tia_write)
        self._brk = False

    # --- temporizador do RIOT
    def timer_set(self, value, div):
        self.timer_at, self.timer_val, self.timer_div = self.now(), value, div

    def intim(self):
        t = (self.now() - self.timer_at) // self.timer_div
        v = self.timer_val - 1 - t
        if v >= 0:
            return v
        return max(0, 256 + v) & 0xFF if v > -256 else 0

    def now(self):
        return self._cur_cycles

    # --- TIA
    def tia_write(self, reg, value):
        c = self._cur_cycles
        if reg == 0x02:                         # WSYNC: para até o fim da linha
            rel = c - self.frame_start
            self.mpu.processorCycles += (76 - (rel + 1) % 76) % 76
            return
        if reg == 0x00:                         # VSYNC
            if value & 2:
                self.vsync_on = True
            elif getattr(self, 'vsync_on', False):
                self.vsync_on = False
                self.vsync_done = c
            return
        self._writes.append((c, reg, value))

    def step(self):
        mpu = self.mpu
        op = mpu.memory[mpu.pc]
        start = mpu.processorCycles
        n = mpu.cycletime[op]
        # instante da (última) escrita da instrução no barramento: gravações escrevem no último
        # ciclo; BRK empilha nos ciclos 2, 3, 4 (um ciclo por escrita, veja Memory.__setitem__)
        self._cur_cycles = start + (2 if op == 0x00 else n - 1)
        self._brk = op == 0x00
        mpu.step()
        self._brk = False

    def frame(self, max_cycles=200000):
        """Roda um quadro (de VSYNC a VSYNC) e o desenha."""
        self.vsync_done = None
        start = self.mpu.processorCycles
        while self.vsync_done is None:
            self.step()
            if self.mpu.processorCycles - start > max_cycles:
                raise RuntimeError('sem VSYNC (pc $%04X)' % self.mpu.pc)
        writes, self._writes = self._writes, []
        prev_start, self.frame_start = self.frame_start, self.vsync_done
        self.render(prev_start, writes)

    # --- desenho
    def render(self, fstart, writes):
        t = self.tia
        r = t.r
        lines, vb, states = [], [], []
        i = 0
        nlines = max(1, (self.frame_start - fstart) // 76)
        writes.sort(key=lambda w: w[0])
        for ln in range(nlines):
            row = [0] * 160
            line_c = fstart + ln * 76
            hmove_bar = False
            for px in range(-68, 160):
                clk = (ln * 228) + 68 + px
                # aplica as escritas até este color clock
                while i < len(writes) and (writes[i][0] - fstart) * 3 <= clk:
                    c, reg, v = writes[i]
                    i += 1
                    self._apply(reg, v, ((c - fstart) * 3) % 228 - 68)
                    if reg == 0x2A and px < 0:
                        hmove_bar = True
                if px < 0:
                    continue
                if px == 0:                     # com o que a linha começa (veja line_state)
                    states.append((dict(t.pos), list(r)))
                if r[0x01] & 2 or (hmove_bar and px < 8):
                    row[px] = 0
                    continue
                row[px] = self._pixel(px)
            lines.append(row)
            vb.append(bool(r[0x01] & 2))
        while i < len(writes):
            c, reg, v = writes[i]
            i += 1
            self._apply(reg, v, ((c - fstart) * 3) % 228 - 68)
        self.lines, self.vblank_lines, self.states = lines, vb, states

    def _apply(self, reg, v, x):
        t = self.tia
        r = t.r
        p = t.pos
        res = {0x10: 'P0', 0x11: 'P1', 0x12: 'M0', 0x13: 'M1', 0x14: 'BL'}
        if reg in res:
            obj = res[reg]
            # no HBLANK o objeto começa na borda esquerda; players desenham 5 clocks depois do
            # strobe, mísseis e bola 4
            delay = 5 if obj[0] == 'P' else 4
            p[obj] = (max(x, -delay) + delay) % 160 if x >= 0 else (3 if obj[0] == 'P' else 2)
            return
        if reg == 0x1B:                         # GRP0: o valor antigo de GRP1 recebe o novo
            t.grp_old[1] = r[0x1C]
        elif reg == 0x1C:
            t.grp_old[0] = r[0x1B]
            t.enabl_old = r[0x1F]
        elif reg == 0x2A:                       # HMOVE
            for obj, hm in (('P0', 0x20), ('P1', 0x21), ('M0', 0x22), ('M1', 0x23), ('BL', 0x24)):
                mv = r[hm] >> 4
                if mv >= 8:
                    mv -= 16
                p[obj] = (p[obj] - mv) % 160
            return
        elif reg == 0x2B:                       # HMCLR
            for hm in range(0x20, 0x25):
                r[hm] = 0
            return
        elif reg == 0x2C:                       # CXCLR
            t.cx = 0
            return
        elif reg == 0x28 and v & 2:             # RESMP0: o míssil segue o player
            p['M0'] = (p['P0'] + 3) % 160
        elif reg == 0x29 and v & 2:
            p['M1'] = (p['P1'] + 3) % 160
        r[reg] = v

    def _pf(self, px):
        r = self.tia.r
        half = px >= 80
        q = px // 4 % 20
        if half and r[0x0A] & 1:
            q = 19 - q
        if q < 4:
            return (r[0x0D] >> (4 + q)) & 1
        if q < 12:
            return (r[0x0E] >> (11 - q)) & 1
        return (r[0x0F] >> (q - 12)) & 1

    def _player(self, n, px):
        t = self.tia
        r = t.r
        nus = r[0x04 + n] & 7
        scale = NUSIZ_SCALE.get(nus, 1)
        g = t.grp_old[n] if r[0x25 + n] & 1 else r[0x1B + n]
        if not g:
            return 0
        for off in NUSIZ_COPIES[nus]:
            d = (px - t.pos['P%d' % n] - off) % 160
            if d < 8 * scale:
                bit = d // scale
                if r[0x0B + n] & 8:
                    bit = 7 - bit
                if (g >> (7 - bit)) & 1:
                    return 1
        return 0

    def _missile(self, n, px):
        t = self.tia
        r = t.r
        if not r[0x1D + n] & 2 or r[0x28 + n] & 2:
            return 0
        nus = r[0x04 + n]
        size = 1 << ((nus >> 4) & 3)
        for off in NUSIZ_COPIES[nus & 7]:
            if (px - t.pos['M%d' % n] - off) % 160 < size:
                return 1
        return 0

    def _ball(self, px):
        t = self.tia
        r = t.r
        en = t.enabl_old if r[0x27] & 1 else r[0x1F]
        if not en & 2:
            return 0
        size = 1 << ((r[0x0A] >> 4) & 3)
        return 1 if (px - t.pos['BL']) % 160 < size else 0

    def _pixel(self, px):
        t = self.tia
        r = t.r
        pf, bl = self._pf(px), self._ball(px)
        p0, p1 = self._player(0, px), self._player(1, px)
        m0, m1 = self._missile(0, px), self._missile(1, px)
        on = {'PF': pf, 'BL': bl, 'P0': p0, 'P1': p1, 'M0': m0, 'M1': m1}
        for pair, (reg, bit) in TIA.CX.items():
            if on[pair[0]] and on[pair[1]]:
                t.cx |= 1 << (reg * 2 + (bit - 6))
        ctrl = r[0x0A]
        pfcol = r[0x08]
        if ctrl & 2:                            # modo placar: playfield nas cores dos players
            pfcol = r[0x06] if px < 80 else r[0x07]
        if ctrl & 4:                            # playfield e bola na frente
            if pf or bl:
                return pfcol >> 1 if pf else r[0x08] >> 1
        if p0 or m0:
            return r[0x06] >> 1
        if p1 or m1:
            return r[0x07] >> 1
        if pf:
            return pfcol >> 1
        if bl:
            return r[0x08] >> 1
        return r[0x09] >> 1

    def image(self, scale=(2, 1)):
        """A parte visível do último quadro (linhas fora do VBLANK) como imagem do Pillow; cada pixel
        do 2600 vira scale[0] x scale[1] pixels da imagem (2 x 1 dá mais ou menos a proporção da TV)."""
        from PIL import Image
        rows = [row for row, vb in zip(self.lines, self.vblank_lines) if not vb]
        img = Image.new('RGB', (160, max(1, len(rows))))
        img.putdata([PALETTE[v] for row in rows for v in row])
        return img.resize((160 * scale[0], len(rows) * scale[1]), Image.NEAREST)
