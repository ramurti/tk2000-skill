#!/usr/bin/env python3
"""Roda um disco no AppleWin para Linux (sa2 --headless) como Apple II+ de 64K e, pelo servidor de
depuração HTTP dele, tira capturas das duas páginas hi-res e despeja a memória ao longo do tempo.

    awrun.py DISK.dsk OUTDIR [-t SEGUNDOS_EMULADOS] [-s CADA_SEGUNDOS] [-k SEGUNDOS:TECLA]... [--sa2 CAMINHO] [--wav]

--snap SEGUNDOS: salva um estado do AppleWin (YAML) em OUTDIR/snap-SEGUNDOS.yaml nesse segundo emulado
(precisa do /api/snapshot do applewin-key.patch); repetível.
-k: aperta TECLA (um caractere, 'r' = RETURN, 'esc', 'sp' = espaço) no segundo emulado dado; precisa do
sa2 com o /api/key (branch tk2000-tools do clone do AppleWin: references/apple-ii.md).

OUTDIR/shot-NNN.png (página 1 | página 2, barra amarela na mostrada), OUTDIR/mem-NNN.bin
($0000-$BFFF + a visão da CPU de $D000-$FFFF), OUTDIR/log.txt (ciclo, PC, página),
OUTDIR/speaker.wav com --wav. Usa um applewin.yaml próprio em OUTDIR (não mexe no ~/.config).
"""
import json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from sfboot import hgr_img
from PIL import Image

HZ = 1020484


def get(port, path, tries=20):
    for k in range(tries):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d%s' % (port, path), timeout=5) as r:
                return json.loads(r.read())
        except (ConnectionError, urllib.error.URLError, json.JSONDecodeError):
            if k == tries - 1:
                raise
            time.sleep(0.1)


def read_mem(lo, hi):
    out = bytearray()
    for a in range(lo, hi, 256):
        d = get(64504, '/api/read?addr=%04X&len=256' % a)
        vals = d.get('bytes') or d.get('data') or d.get('values')
        if vals is None:
            vals = [v for k, v in d.items() if isinstance(v, list)][0]
        out += bytes(int(v, 16) if isinstance(v, str) else v for v in vals[:256])
    return out


def main():
    a = sys.argv[1:]
    dsk, out = os.path.abspath(a[0]), os.path.abspath(a[1])  # absolutos: o sa2 troca de pasta
    secs, every = 200, 5
    sa2 = os.path.expanduser('~/code/tk2000/AppleWin/build/sa2')
    wav = '--wav' in a
    keys = []
    snaps = []
    for i, x in enumerate(a):
        if x == '-t': secs = float(a[i + 1])
        if x == '-s': every = float(a[i + 1])
        if x == '--sa2': sa2 = a[i + 1]
        if x == '--snap': snaps.append(float(a[i + 1]))
        if x == '-k':
            t, _, k = a[i + 1].partition(':')
            keys.append((float(t) * HZ, {'r': 0x0D, 'esc': 0x1B, 'sp': 0x20}.get(k, ord(k[0]) if k else 0x20)))
    keys.sort()
    os.makedirs(out, exist_ok=True)
    import socket
    for port in (64501, 64503, 64504):                         # outra janela do AppleWin aberta ocupa as portas
        with socket.socket() as sk:
            if sk.connect_ex(('127.0.0.1', port)) == 0:
                sys.exit('a porta %d já está em uso: feche o outro AppleWin (sa2) antes' % port)
    cmd = [sa2, '--headless', '--fixed-speed', '-c', os.path.join(out, 'applewin.yaml'),
           '-r', 'Configuration.Apple2 Type=1', '--d1', dsk]
    cmd += ['--wav-speaker', os.path.join(out, 'speaker.wav')] if wav else ['--no-audio']
    p = subprocess.Popen(cmd, stdout=open(os.path.join(out, 'sa2.log'), 'w'), stderr=subprocess.STDOUT)
    log = open(os.path.join(out, 'log.txt'), 'w')
    try:
        for _ in range(50):
            try:
                get(64501, '/api/info'); break
            except Exception:
                time.sleep(0.2)
        for t in snaps:
            get(64504, '/api/snapshot?file=%s&at=%d' % (urllib.parse.quote(os.path.join(out, 'snap-%g.yaml' % t), safe=''), int(t * HZ)))
        n, nxt = 0, every * HZ
        while True:
            info = get(64501, '/api/info')
            cyc = info['cycles']['cumulative']
            while keys and cyc >= keys[0][0]:
                get(64504, '/api/key?code=%02X' % keys[0][1])
                line = '      %6.1fs tecla %r' % (cyc / HZ, chr(keys[0][1]))
                print(line, flush=True); log.write(line + '\n')
                keys.pop(0)
            if cyc < nxt:
                time.sleep(0.05); continue
            mem = read_mem(0x0000, 0xC000)
            hi = read_mem(0xD000, 0x10000)
            reg = get(64503, '/api/registers')
            pg2 = info['memory']['page2']
            open(os.path.join(out, 'mem-%03d.bin' % n), 'wb').write(mem + bytes(0x1000) + hi)
            p1, p2 = hgr_img(mem, 1), hgr_img(mem, 2)
            img = Image.new('RGB', (568, 204), (60, 60, 60))
            img.paste(p1, (0, 12)); img.paste(p2, (288, 12))
            for x in range(288 if pg2 else 0, (288 if pg2 else 0) + 280):
                for y in range(8): img.putpixel((x, y), (255, 200, 0))
            img.save(os.path.join(out, 'shot-%03d.png' % n))
            line = '%03d %6.1fs ciclo %d PC %s pág%d %s' % (n, cyc / HZ, cyc, reg['PC'], 2 if pg2 else 1, info.get('videoMode'))
            print(line, flush=True); log.write(line + '\n'); log.flush()
            n += 1; nxt += every * HZ
            if cyc >= secs * HZ:
                break
    finally:
        p.terminate(); p.wait()


if __name__ == '__main__':
    main()
