#!/usr/bin/env python3
"""Render an audience-specific guide from reviewed JSON; never reads evaluation data."""
import argparse
import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

GREEN=colors.HexColor('#173c31'); LIME=colors.HexColor('#d8edab'); INK=colors.HexColor('#24372f')
MUTED=colors.HexColor('#5d6e65'); PALE=colors.HexColor('#f0f5ed'); WHITE=colors.white


def render(content, output):
    font_root=Path('/usr/share/fonts/truetype/dejavu')
    for name, filename in [('Nature','DejaVuSans.ttf'),('NatureBold','DejaVuSans-Bold.ttf'),('NatureItalic','DejaVuSans-Oblique.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(font_root/filename)))
    pdfmetrics.registerFontFamily('Nature',normal='Nature',bold='NatureBold',italic='NatureItalic',boldItalic='NatureBold')
    styles={
        'title':ParagraphStyle('title',fontName='NatureBold',fontSize=23,leading=28,textColor=GREEN,spaceAfter=12),
        'h2':ParagraphStyle('h2',fontName='NatureBold',fontSize=12.2,leading=16,textColor=GREEN,spaceBefore=9,spaceAfter=6,keepWithNext=True),
        'p':ParagraphStyle('p',fontName='Nature',fontSize=10.5,leading=15.2,textColor=INK,spaceAfter=8),
        'lead':ParagraphStyle('lead',fontName='Nature',fontSize=11.8,leading=17.2,textColor=INK,spaceAfter=12),
        'small':ParagraphStyle('small',fontName='Nature',fontSize=9.3,leading=13.2,textColor=MUTED,spaceAfter=7),
        'cell':ParagraphStyle('cell',fontName='Nature',fontSize=9.3,leading=12.7,textColor=INK),
        'head':ParagraphStyle('head',fontName='NatureBold',fontSize=9.3,leading=12.7,textColor=WHITE),
        'bullet':ParagraphStyle('bullet',fontName='Nature',fontSize=10.5,leading=15.2,textColor=INK,leftIndent=12,firstLineIndent=-10,spaceAfter=7),
        'step':ParagraphStyle('step',fontName='Nature',fontSize=10.5,leading=15.2,textColor=INK,leftIndent=17,firstLineIndent=-17,spaceAfter=9),
    }
    def p(text, kind='p'):
        # The reviewed JSON may use <b>, <i> and <a> for native PDF styling/links.
        text=text.replace('\u2011','-').replace('\u2013','-').replace('\u2014',' - ')
        return Paragraph(text,styles[kind])
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,
        topMargin=25*mm,bottomMargin=20*mm,title=content['title'],author='Hula Earth / AI for Nature',
        subject=content['audience']+' guide for the AI for Nature bird habitat challenge')
    total=len(content['pages'])
    def furniture(canvas, document):
        w,h=document.pagesize;canvas.saveState()
        canvas.setFillColor(GREEN);canvas.rect(0,h-12*mm,w,12*mm,fill=1,stroke=0)
        canvas.setFillColor(LIME);canvas.setFont('NatureBold',8)
        canvas.drawString(18*mm,h-8*mm,'HULA EARTH  /  AI FOR NATURE')
        canvas.setFont('Nature',7.3);canvas.setFillColor(WHITE)
        canvas.drawRightString(w-18*mm,h-8*mm,content['audience'].upper())
        canvas.setStrokeColor(colors.HexColor('#d8e3d7'));canvas.line(18*mm,15*mm,w-18*mm,15*mm)
        canvas.setFillColor(MUTED);canvas.setFont('Nature',7)
        canvas.drawString(18*mm,10*mm,'AI for Nature  |  '+content.get('edition','Guide edition 20 October 2026'))
        canvas.drawRightString(w-18*mm,10*mm,f'{document.page} / {total}')
        canvas.restoreState()
    story=[]
    for index,page in enumerate(content['pages']):
        if index:story.append(PageBreak())
        story.append(p(f'{index+1:02d} / '+page['kicker'],'small'))
        story.append(p(page['title'],'title'))
        if page.get('intro'):story.append(p(page['intro'],'lead'))
        for item in page['blocks']:
            kind=item['type']
            if kind in {'p','small','h2','lead'}:story.append(p(item['text'],kind))
            elif kind=='bullets':
                story.extend(p('- '+text,'bullet') for text in item['items'])
            elif kind=='steps':
                story.extend(p(f'<b>{number}.</b> '+text,'step') for number,text in enumerate(item['items'],1))
            elif kind=='callout':
                box=Table([[p(item['text'])]],colWidths=[doc.width],hAlign='LEFT')
                box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#ccdcca')),('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
                story.extend([box,Spacer(1,9)])
            elif kind=='table':
                widths=item.get('widths',[1]*len(item['rows'][0]));scale=doc.width/sum(widths)
                table=Table([[p(str(cell),'head' if rownum==0 else 'cell') for cell in row] for rownum,row in enumerate(item['rows'])],colWidths=[x*scale for x in widths],repeatRows=1,hAlign='LEFT')
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREEN),('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,PALE]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5.5),('BOTTOMPADDING',(0,0),(-1,-1),5.5),('LINEBELOW',(0,0),(-1,0),0.5,GREEN)]))
                story.extend([table,Spacer(1,9)])
            else:raise ValueError('Unknown content block: '+kind)
    doc.build(story,onFirstPage=furniture,onLaterPages=furniture)
    if doc.page != total:
        raise ValueError(f'Layout overflow: expected {total} pages, rendered {doc.page}; repair before delivery')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--content',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(render(json.loads(args.content.read_text()),args.output))
