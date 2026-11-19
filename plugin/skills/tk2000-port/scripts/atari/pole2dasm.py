#!/usr/bin/env python3
"""Fonte do Pole Position da Atari (reference/POLE26.S, sintaxe do montador de 1985) -> fonte para
o dasm.

    pole2dasm.py POLE26.S [--tk] > saida.asm

Sintaxe: DB -> DC.B; L(x)/H(x) -> byte baixo/alto; linhas de comentário com '*'; 'LSR A' ->
'LSR'; números decimais com zeros à esquerda (o dasm os leria como octais); um comentário com
':'; deslocamentos STAMPZN truncados para bytes (o montador antigo ficava com o byte baixo).

Disposição: os dois bancos de 4K dividem uma mesma janela de endereços; o dasm recebe ORG =
deslocamento no arquivo e RORG = endereço:
  padrão   banco D no arquivo 0-4K ($D000), banco F em 4-8K ($F000): a disposição do cartucho
  --tk     a compilação para o TK2000: banco D em $8000, banco F em $9000 (arquivo 0-4K / 4-8K,
           carregado em $8000); os deslocamentos dentro da página ficam iguais (a página ROADCURV
           de bytes de código lidos como dados mantém seu padrão de zero / não zero). Ganchos no
           programa do TK2000 (tabela de saltos em $4003): o salto para o kernel de vídeo
           (GOBANKD) -> TK_KERNEL, e o salto de volta para VBLNK no fim do overscan ->
           TK_TICKEND.
"""
import re
import sys

TK_KERNEL, TK_TICKEND = 0x4003, 0x4006


def convert(lines, tk):
    out = ['        processor 6502']
    prev = ''
    for line in lines:
        line = line.rstrip('\r\n')
        if line.startswith('*'):
            line = ';' + line[1:]
        line = re.sub(r'^([A-Za-z0-9_?]*[ \t]+)DB([ \t])', r'\1DC.B\2', line)
        line = re.sub(r'([^A-Za-z0-9_])L\(([^)]*)\)', r'\1[[\2]&$FF]', line)
        line = re.sub(r'([^A-Za-z0-9_])H\(([^)]*)\)', r'\1[[\2]>>8]', line)
        line = re.sub(r'^([A-Za-z0-9_?]*[ \t]+(ASL|LSR|ROL|ROR))[ \t]+A([ \t;]|$)', r'\1\3', line)
        code, sep, comment = line.partition(';')
        code = re.sub(r'(?<![$%0-9A-Za-z_])0+([0-9])', r'\1', code)
        line = code + sep + comment
        line = re.sub(r'(STAMP[0-9]-STAMP1)', r'[[\1]&$FF]', line)
        line = re.sub(r'(,X)[ \t]+:', r'\1 ;', line)
        m = re.match(r'^([ \t]+)ORG([ \t]+)\$([DF])([0-9A-F]{3})(.*)$', line)
        if m:
            ind, sp, bank, off, rest = m.groups()
            fileoff = ('0' if bank == 'D' else '1') + off
            addr = (('8' if bank == 'D' else '9') if tk else bank) + off
            out.append('%sORG%s$%s' % (ind, sp, fileoff))
            out.append('%sRORG%s$%s%s' % (ind, sp, addr, rest))
            prev = line
            continue
        if tk:
            if re.match(r'^GOBANKD[ \t]+JMP[ \t]+DOBANKD', line):
                line = 'GOBANKD   JMP     $%04X                  ;TK2000: TK_KERNEL' % TK_KERNEL
            elif re.match(r'^[ \t]+JMP[ \t]+VBLNK', line) and 'ENDOVSCN' in prev:
                line = '          JMP     $%04X                  ;TK2000: TK_TICKEND' % TK_TICKEND
        out.append(line)
        if line.strip():
            prev = line
    return out


if __name__ == '__main__':
    src = open(sys.argv[1], encoding='latin-1').read().split('\n')
    tk = '--tk' in sys.argv[2:]
    text = '\n'.join(convert(src, tk)) + '\n'
    if tk:
        assert ';TK2000: TK_KERNEL' in text and ';TK2000: TK_TICKEND' in text, 'ganchos não encontrados'
    sys.stdout.write(text)
