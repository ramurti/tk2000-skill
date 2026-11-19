#!/usr/bin/env python3
"""Ciclos por rotina de um porte para o TK2000 que roda um original do Atari 2600 (modelo:
Enduro). Roda o programa inteiro no py65 com uma pilotagem roteirizada (as entradas e os rótulos
de tools/lockstep.py) e atribui os ciclos de cada instrução ao rótulo mais próximo abaixo do
endereço dela: os rótulos do original vêm do arquivo .sym do dasm (O:), os do código do TK2000 do
arquivo -Ln do ld65 (T:), deixando de fora os locais baratos e os locais de macro. Imprime a
divisão original/TK2000 e as rotinas que mais gastam, exclusivo (código do rótulo até o próximo)
e inclusivo (com o que elas chamam, por JSR/RTS). Só mede.

Uso: profile_labels.py [tiques]   (a partir da raiz do projeto; adapte os nomes de arquivo e
ReadKeys)
"""
import sys, bisect, collections
sys.path.insert(0,'tools')
from py65.devices.mpu6502 import MPU
import lockstep as L
lab=L.labels()
syms=[]
for line in open('build/tk/enduro.sym'):
    p=line.split()
    if len(p)>=2 and len(p[1])==4 and not p[0].startswith('0.'):
        try: syms.append((int(p[1],16),'O:'+p[0]))
        except: pass
for line in open('build/enduro.lbl'):
    _,a,nm=line.split()
    if not nm.startswith('.@') and not nm.startswith('.__'):
        syms.append((int(a,16),'T:'+nm[1:]))
syms.sort(); addrs=[a for a,_ in syms]
def name(pc):
    i=bisect.bisect_right(addrs,pc)-1
    return syms[i][1] if i>=0 else '?'
cache={}
def nm(pc):
    if pc not in cache: cache[pc]=name(pc)
    return cache[pc]
n=int(sys.argv[1]) if len(sys.argv)>1 else 6000
mem=bytearray(0x10000); prog=open('build/enduro.bin','rb').read(); mem[0x4000:0x4000+len(prog)]=prog
t=MPU(memory=mem,pc=0x4000)
excl=collections.Counter(); incl=collections.Counter(); stack=[]
total=0; f=0; area=collections.Counter()
while f<n:
    pc=t.pc
    if pc==lab['ReadKeys']:
        sw,sb,fi=L.inputs(f+1); mem[0x280],mem[0x282],mem[0x3C]=sw,sb,0 if fi else 0x80
        r=mem[0x100+((t.sp+1)&0xFF)]|mem[0x100+((t.sp+2)&0xFF)]<<8; t.sp=(t.sp+2)&0xFF; t.pc=r+1; continue
    op=mem[pc]; c0=t.processorCycles
    t.step()
    dc=t.processorCycles-c0
    if f>=300:
        excl[nm(pc)]+=dc; total+=dc
        area['original' if pc>=0xF000 else 'tk']+=dc
        for s in set(stack): incl[s]+=dc
    if op==0x20: stack.append(nm(t.pc))
    elif op==0x60 and stack: stack.pop()
    if len(stack)>40: stack=stack[-40:]
    if pc==L.MAINLOOP:
        f+=1; mem[0]=mem[2]=mem[7]=0
print('total de %d ciclos em %d tiques (%.0f por tique)'%(total,n-300,total/(n-300)))
for k,v in area.items(): print('%-10s %5.1f%%'%(k,100*v/total))
print('--- exclusivo (código daquele rótulo até o próximo)')
for k,v in excl.most_common(45): print('%-22s %5.1f%%'%(k,100*v/total))
print('--- inclusivo (rotinas chamadas, com o que elas chamam)')
for k,v in incl.most_common(45): print('%-22s %5.1f%%'%(k,100*v/total))
