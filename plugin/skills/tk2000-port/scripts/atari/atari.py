"""Roda a ROM original do River Raid do Atari 2600 (reference/riverraid.bin) no simulador de
6502 py65, com a TIA e o RIOT reduzidos a registradores simples, para obter estados de referência
do jogo.

Os registradores de colisão sempre leem 0 (o kernel do 2600 não é emulado pixel a pixel), então o
avião nunca bate e nunca reabastece: use-o para a lógica de geração, não para a jogabilidade.
"""
import os
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', '..', 'reference')


def load_symbols(path=os.path.join(REF, 'riverraid.sym')):
    syms = {}
    for line in open(path):
        parts = line.split()
        if len(parts) >= 2 and not line.startswith('---'):
            try:
                syms[parts[0]] = int(parts[1], 16)
            except ValueError:
                pass
    return syms


class Memory:
    """Decodificação de endereços do 2600 (13 linhas de endereço)."""

    def __init__(self, machine):
        self.m = machine

    def __len__(self):
        return 0x10000

    def __getitem__(self, addr):
        if isinstance(addr, slice):
            return [self[i] for i in range(*addr.indices(0x10000))]
        a = addr & 0x1FFF
        if a & 0x1000:
            return self.m.rom[a & 0x0FFF]
        if a & 0x80 and not a & 0x200:
            return self.m.ram[a & 0x7F]
        if not a & 0x80:                        # registradores de leitura da TIA
            reg = a & 0x0F
            if reg == 0x0C:                     # INPT4: botão de tiro (bit 7 = 0 apertado)
                return 0x00 if self.m.fire else 0x80
            if reg == 0x0D:
                return 0x80
            return 0x00                         # colisões
        reg = a & 0x07                          # RIOT
        if reg == 0:
            return self.m.swcha
        if reg == 2:
            return self.m.swchb
        return 0x00                             # INTIM: temporizador já expirou

    def __setitem__(self, addr, value):
        a = addr & 0x1FFF
        if not a & 0x1000 and a & 0x80 and not a & 0x200:
            self.m.ram[a & 0x7F] = value & 0xFF


class Atari:
    def __init__(self, rom_path=os.path.join(REF, 'riverraid.bin')):
        self.rom = open(rom_path, 'rb').read()
        self.ram = bytearray(128)
        self.syms = load_symbols()
        self.swcha = 0xFF                       # joystick: nada apertado
        self.swchb = 0x0B                       # cor, RESET e SELECT soltos, dificuldade B
        self.fire = False
        self.mpu = MPU(memory=Memory(self), pc=self.syms['START'])
        self.hooks = {}                         # pc -> função(atari)

    def zp(self, addr):
        return self.ram[addr & 0x7F]

    def frame(self, max_steps=200000):
        """Roda até a próxima entrada em MainLoop."""
        main = self.syms['MainLoop']
        mpu = self.mpu
        for _ in range(max_steps):
            mpu.step()
            hook = self.hooks.get(mpu.pc)
            if hook:
                hook(self)
            if mpu.pc == main:
                return
        raise RuntimeError('o quadro não terminou em $%04X' % mpu.pc)

    def start_game(self):
        """Liga a máquina e aperta RESET para começar um jogo de um jogador."""
        self.frame()
        self.swchb &= ~1
        for _ in range(3):
            self.frame()
        self.swchb |= 1
