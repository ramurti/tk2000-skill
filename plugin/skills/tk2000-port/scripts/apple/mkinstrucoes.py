#!/usr/bin/env python3
"""As instruções do jogador: junta manual/INSTALACAO.md (como pôr o jogo para rodar) e manual/MANUAL.md (como
jogar) em dist/INSTRUCOES.md, para o repositório, e num .docx fora do repositório, para abrir no Google Docs
(Arquivo > Abrir > Fazer upload: ele converte).

    mkinstrucoes.py [SAIDA.docx]      (padrão: ~/code/tk2000/skyfox-entrega/Sky Fox para TK2000 - Instruções.docx)

O .docx sai de um markdown simples: títulos (#, ##, ###), parágrafos, listas (- e 1.), tabelas, imagens, citações
(>), separadores (---), **negrito**, *itálico* e `código`. Precisa do python-docx (.venv/bin/pip install python-docx).
"""
import os, re, sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAN = os.path.join(ROOT, 'manual')
DOCX = os.path.expanduser('~/code/tk2000/skyfox-entrega/Sky Fox para TK2000 - Instruções.docx')
LARG = 6.3                                   # polegadas úteis (A4 com margens de 1")


def junta():
    ins = open(os.path.join(MAN, 'INSTALACAO.md')).read().rstrip() + '\n'
    man = open(os.path.join(MAN, 'MANUAL.md')).read()
    return ins + '\n---\n\n' + man


def markdown_repo(txt):
    """dist/INSTRUCOES.md: as imagens do manual a partir de dist/"""
    return re.sub(r'\]\(telas/', '](../manual/telas/', txt)


# --- o .docx ---------------------------------------------------------------------------------------------
INLINE = re.compile(r'(\*\*[^*]+?\*\*|\*[^*]+\*|`[^`]+`)')


def runs(par, texto, negrito=False):
    for pedaço in INLINE.split(texto):
        if not pedaço:
            continue
        if pedaço.startswith('**'):
            r = par.add_run(pedaço[2:-2].replace('`', '')); r.bold = True
        elif pedaço.startswith('`'):
            r = par.add_run(pedaço[1:-1]); r.font.name = 'Courier New'
        elif pedaço.startswith('*') and len(pedaço) > 2:
            r = par.add_run(pedaço[1:-1]); r.italic = True
        else:
            r = par.add_run(pedaço)
        if negrito:
            r.bold = True


def sombra(cell, cor):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), cor)
    tcpr.append(shd)


def linha_embaixo(par):
    ppr = par._p.get_or_add_pPr()
    b = OxmlElement('w:pBdr')
    e = OxmlElement('w:bottom')
    e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '6'); e.set(qn('w:space'), '1'); e.set(qn('w:color'), '999999')
    b.append(e); ppr.append(b)


def tabela(doc, linhas):
    cel = [[c.strip() for c in l.strip().strip('|').split('|')] for l in linhas]
    cel = [r for r in cel if not all(re.fullmatch(r':?-{3,}:?', c) for c in r)]
    n = max(len(r) for r in cel)
    tam = [max(len(re.sub(r'[*`]', '', r[i])) if i < len(r) else 0 for r in cel) for i in range(n)]
    tam = [max(8, min(t, 60)) for t in tam]
    larg = [LARG * t / sum(tam) for t in tam]
    t = doc.add_table(rows=len(cel), cols=n)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, r in enumerate(cel):
        for j in range(n):
            c = t.cell(i, j)
            c.width = Inches(larg[j])
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            runs(p, r[j] if j < len(r) else '', negrito=(i == 0))
            if i == 0:
                sombra(c, 'D9E2F3')
    doc.add_paragraph()


def numerado(doc, num, texto):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.paragraph_format.space_after = Pt(3)
    runs(p, '%s\t%s' % (num, texto))
    p.paragraph_format.tab_stops.add_tab_stop(Inches(0.35))


def docx(txt, saida):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)      # A4
    for m in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(sec, m, Inches(1))
    st = doc.styles['Normal']
    st.font.name = 'Arial'; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Arial')
    st.paragraph_format.space_after = Pt(6)
    for nome, tam in (('Title', 24), ('Heading 1', 20), ('Heading 2', 15), ('Heading 3', 12)):
        h = doc.styles[nome]
        h.font.name = 'Arial'; h.font.size = Pt(tam); h.font.bold = True
        h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
        h.paragraph_format.space_before = Pt(14); h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
    ls = txt.split('\n')
    i, par, primeiro_h1 = 0, [], True

    def fecha():
        if par:
            runs(doc.add_paragraph(), ' '.join(s.strip() for s in par))
            par.clear()

    while i < len(ls):
        l = ls[i]
        s = l.strip()
        if not s:
            fecha(); i += 1; continue
        m = re.match(r'(#{1,3}) (.*)', s)
        if m:
            fecha()
            nivel = len(m.group(1))
            if nivel == 1:
                if not primeiro_h1:
                    from docx.enum.text import WD_BREAK
                    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                doc.add_heading(m.group(2), 0 if primeiro_h1 else 1)
                primeiro_h1 = False
            else:
                doc.add_heading(m.group(2), nivel)
            i += 1; continue
        if s == '---':
            fecha(); linha_embaixo(doc.add_paragraph()); i += 1; continue
        m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
        if m:
            fecha()
            caminho = os.path.join(MAN, m.group(2))
            doc.add_picture(caminho, width=Inches(4.6))
            doc.paragraphs[-1].alignment = 1
            leg = doc.add_paragraph(); runs(leg, '*%s*' % m.group(1)); leg.alignment = 1
            i += 1; continue
        if s.startswith('|'):
            fecha()
            bloco = []
            while i < len(ls) and ls[i].strip().startswith('|'):
                bloco.append(ls[i]); i += 1
            tabela(doc, bloco); continue
        if s.startswith('>'):
            fecha()
            q = []
            while i < len(ls) and ls[i].strip().startswith('>'):
                q.append(ls[i].strip()[1:].strip()); i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            sombra_p = p._p.get_or_add_pPr()
            shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:fill'), 'F2F2F2')
            sombra_p.append(shd)
            runs(p, ' '.join(q)); continue
        m = re.match(r'(- |\d+\. )(.*)', s)
        if m:
            fecha()
            item = [m.group(2)]
            i += 1
            while i < len(ls) and ls[i].startswith('  ') and ls[i].strip() and not re.match(r'(- |\d+\. )', ls[i].strip()):
                item.append(ls[i].strip()); i += 1
            texto = ' '.join(item)
            if m.group(1) == '- ':
                p = doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after = Pt(3); runs(p, texto)
            else:
                numerado(doc, m.group(1).strip(), texto)
            continue
        par.append(l); i += 1
    fecha()
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    doc.save(saida)


def main():
    txt = junta()
    d = os.path.join(ROOT, 'dist')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'INSTRUCOES.md'), 'w').write(markdown_repo(txt))
    saida = sys.argv[1] if len(sys.argv) > 1 else DOCX
    docx(txt, saida)
    print('dist/INSTRUCOES.md e', saida)


if __name__ == '__main__':
    main()
