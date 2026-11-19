#!/usr/bin/env python3
"""Monta uma imagem de fita do TK2000 (.ct2) que se inicia sozinha, a partir de um binário.

Uso: mkct2.py program.bin load_address start_address NAME output.ct2 [extra.bin@address ...]

A fita contém os arquivos, todos carregados com LOADT:
  1. Um arquivo de página zero ($0036-$0070). Ele aponta o vetor de saída (CSW, $36) para um
     pequeno carregador em $0050; quando a ROM imprime depois da carga, o carregador roda, lê os
     próximos arquivos com a rotina $EDAE da ROM e salta para o programa.
  2. O próprio programa.
  3. Os arquivos extras (até 2), cada um no seu endereço; FILE@ADDR< o põe antes do programa (uma
     tela de carga em $2000 aparece enquanto o resto carrega).

Formato de fita do TK2000 (como a ROM produz):
  - cada arquivo é um bloco de cabeçalho seguido de blocos de dados de até 256 bytes
  - bloco = nome (6 caracteres, bit alto ligado) + número de blocos de dados + índice do bloco
            (0 = cabeçalho) + conteúdo + checksum (XOR de todos os bytes anteriores do bloco, invertido)
  - conteúdo do cabeçalho = endereço inicial, endereço final (little endian)
Contêiner CT2: "CTK2", depois trechos "CA" (piloto longo), "CB" (sync), "DA" (dados), com um
tamanho de 16 bits little-endian.
"""
import struct
import sys

ZP_START, ZP_END = 0x0036, 0x0070
LOADER = 0x0050


def zero_page_file(start_address, files):
    zp = bytearray(ZP_END - ZP_START + 1)

    def poke(addr, value):
        zp[addr - ZP_START] = value & 0xFF

    def poke16(addr, value):
        poke(addr, value)
        poke(addr + 1, value >> 8)

    # Variáveis do monitor sobrescritas enquanto este arquivo carrega: precisam conter, quando
    # escritas, os valores que o carregador da ROM tem naquele momento (A1 = endereço atual, A2 = fim, ...)
    poke16(0x36, LOADER)        # CSW: vetor de saída -> nosso carregador
    poke16(0x38, LOADER)        # KSW: vetor de entrada
    poke16(0x3A, 0x0078)
    poke16(0x3C, 0x003C)        # A1: endereço sendo carregado quando $3C é escrito
    poke16(0x3E, ZP_END)        # A2: endereço final deste arquivo
    poke16(0x40, ZP_START)      # A3: endereço inicial deste arquivo
    # Carregador: as mesmas chamadas à ROM que as fitas comerciais usam, depois o programa
    code = [
        0xA9, 0xF0, 0x85, 0x36,     # LDA #$F0 / STA $36   CSW de volta ao COUT da ROM ($FDF0)
        0xA9, 0xFD, 0x85, 0x37,     # LDA #$FD / STA $37
        0x20, 0x74, 0xFB,           # JSR $FB74
        0x20, 0x00, 0xEC,           # JSR $EC00            variáveis da página 1 de hi-res
        0x20, 0x32, 0xF8,           # JSR $F832
        0x8D, 0x50, 0xC0,           # STA $C050            vídeo em cores (uma tela de carga)
    ]
    code += [0x20, 0xAE, 0xED] * files  # JSR $EDAE            lê o próximo arquivo da fita
    code += [0x4C, start_address & 0xFF, start_address >> 8]  # JMP start
    assert LOADER + len(code) <= ZP_END + 1
    for i, b in enumerate(code):
        poke(LOADER + i, b)
    return bytes(zp)


def block(name, count, index, payload):
    data = bytearray(name) + bytes([count, index]) + payload
    checksum = 0xFF
    for b in data:
        checksum ^= b
    return bytes(data) + bytes([checksum])


def tape_file(name, address, data):
    end = address + len(data) - 1
    count = (len(data) + 255) // 256
    blocks = [block(name, count, 0, struct.pack('<HH', address, end))]
    for i in range(count):
        blocks.append(block(name, count, i + 1, data[i * 256:(i + 1) * 256]))
    return blocks


def ct2(files):
    out = bytearray(b'CTK2')
    for blocks in files:
        for i, b in enumerate(blocks):
            if i == 0:
                out += b'CA' + struct.pack('<H', 0)     # piloto longo antes de cada arquivo
            out += b'CB' + struct.pack('<H', 0)
            out += b'DA' + struct.pack('<H', len(b)) + b
    return bytes(out)


def main():
    if not 6 <= len(sys.argv) <= 8:
        sys.exit(__doc__)
    program = open(sys.argv[1], 'rb').read()
    load = int(sys.argv[2], 0)
    start = int(sys.argv[3], 0)
    name = bytes(c | 0x80 for c in sys.argv[4].upper()[:6].ljust(6).encode('ascii'))
    extra = [(open(f, 'rb').read(), int(a.rstrip('<'), 0), a.endswith('<'))
             for f, a in (x.split('@') for x in sys.argv[6:])]
    files = [tape_file(name, ZP_START, zero_page_file(start, 1 + len(extra)))]
    files += [tape_file(name, a, d) for d, a, first in extra if first]
    files.append(tape_file(name, load, program))
    files += [tape_file(name, a, d) for d, a, first in extra if not first]
    open(sys.argv[5], 'wb').write(ct2(files))


if __name__ == '__main__':
    main()
