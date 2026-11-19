#!/usr/bin/env python3
"""Mostra o desassemblado em volta de endereços: ctx.py FILE ADDR [ADDR...] [-n LINES]
(FILE = C, D, G, ...; usa build/dis/FILE.lst, feito com ca65 -l)"""
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
args = sys.argv[1:]
n = 8
if '-n' in args:
    i = args.index('-n'); n = int(args[i + 1]); del args[i:i + 2]
f = args[0]
lst = os.path.join(ROOT, 'build', 'dis', f + '.lst')
src = os.path.join(ROOT, 'build', 'dis', f + '.s')
if not os.path.exists(lst) or os.path.getmtime(lst) < os.path.getmtime(src):
    subprocess.run(['ca65', '-l', lst, '-o', '/dev/null', src], check=True)
rows = []
for line in open(lst):
    m = re.match(r'^([0-9A-F]{6})', line)
    if m and len(line) > 24:
        rows.append((int(m.group(1), 16), line[:6] + line[24:].rstrip()))
for a in args[1:]:
    a = int(a, 16)
    k = max(i for i, (ad, _) in enumerate(rows) if ad <= a)
    for i in range(max(0, k - n), min(len(rows), k + n // 2 + 1)):
        print(('>> ' if i == k else '   ') + rows[i][1])
    print('-' * 40)
