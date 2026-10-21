"""Render the saved report source; optional dependency: reportlab."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Flowable
from reportlab.lib.enums import TA_LEFT

NAVY=colors.HexColor('#102c42'); TEAL=colors.HexColor('#087e8b'); GREY=colors.HexColor('#526b7e')

class FlowDiagram(Flowable):
    def __init__(self, labels):
        Flowable.__init__(self); self.labels=labels; self.width=480;self.height=75
    def draw(self):
        c=self.canv; gap=14;w=(480-gap*(len(self.labels)-1))/len(self.labels)
        for i,label in enumerate(self.labels):
            x=i*(w+gap);c.setFillColor(colors.HexColor('#e9f4f4'));c.setStrokeColor(TEAL);c.roundRect(x,20,w,45,6,fill=1,stroke=0)
            c.setFillColor(NAVY);c.setFont('Helvetica-Bold',9)
            lines=label.split('|')
            for j,line in enumerate(lines):c.drawCentredString(x+w/2,47-j*12,line)
            if i<len(self.labels)-1:
                c.setStrokeColor(TEAL);c.line(x+w+2,42,x+w+gap-2,42);c.line(x+w+gap-5,45,x+w+gap-2,42);c.line(x+w+gap-5,39,x+w+gap-2,42)

def render(root):
    data=json.loads((root/'docs'/'report-source.json').read_text(encoding='utf-8'))
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=10.4,leading=15.2,textColor=NAVY,spaceAfter=10))
    styles.add(ParagraphStyle(name='SmallCustom',fontName='Helvetica',fontSize=8.7,leading=12,textColor=GREY,spaceAfter=7))
    styles.add(ParagraphStyle(name='TitleCustom',fontName='Helvetica-Bold',fontSize=36,leading=41,textColor=NAVY,spaceAfter=22))
    styles.add(ParagraphStyle(name='SectionCustom',fontName='Helvetica-Bold',fontSize=23,leading=28,textColor=NAVY,spaceAfter=20))
    styles.add(ParagraphStyle(name='SubCustom',fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=TEAL,spaceBefore=8,spaceAfter=7))
    p=lambda t:Paragraph(t,styles['BodyCustom'])
    story=[Spacer(1,56),Paragraph('ENGINEERING PORTFOLIO / '+data['number'],styles['SubCustom']),Spacer(1,20),Paragraph(data['title'],styles['TitleCustom']),p(data['subtitle']),Spacer(1,28),FlowDiagram(data['flow']),Spacer(1,30),p('<b>Technical explanation &amp; discussion guide</b>'),p('Prepared for Mridul Batra<br/>21 October 2026'),Spacer(1,24),p('A tested, local simulation project with reproducible evidence. Built with AI assistance; intended for learning, demonstration, and honest portfolio discussion.'),p('<b>Scope:</b> No physical hardware validation, industrial deployment, or safety-system certification.'),PageBreak()]
    story+=[Paragraph('Guide to this report',styles['SectionCustom']),p('Start with the overview, run the default experiment, and then compare the code with the model and test sections. The questions at the end help you explain both what works and where the evidence stops.')]
    for i,section in enumerate(data['sections']):
        story.append(p(f'<link href="#section{i}" color="#087e8b">{i+1:02d} &nbsp; {section["title"]}</link>'))
    story += [Spacer(1,18),Paragraph('Quick start',styles['SubCustom']),p('Install Python 3.10+ and double-click <b>Launch.cmd</b>. Or run <font name="Courier">python src/server.py</font> from the project folder. No pip install is required for the application.'),p('Run checks with <font name="Courier">python -m unittest discover -s tests -v</font>. Regenerate the default CSV and JSON with <font name="Courier">python evaluate.py</font>.'),p('Optional PDF rebuild: install ReportLab, then run <font name="Courier">python docs/build_report.py</font>. This renders the saved report source and chart; it does not refresh numerical claims automatically.'),PageBreak()]
    for i,section in enumerate(data['sections']):
        story.append(Paragraph(f'<a name="section{i}"/>{i+1:02d} / {section["title"]}',styles['SectionCustom']))
        for block in section['blocks']:
            if block[0]=='p':story.append(p(block[1]))
            elif block[0]=='h':story.append(Paragraph(block[1],styles['SubCustom']))
            elif block[0]=='flow':story.append(FlowDiagram(block[1]))
            elif block[0]=='image':story.append(Image(str(root/'docs'/block[1]),width=480,height=245));story.append(Spacer(1,10))
            elif block[0]=='table':
                rows=[[Paragraph('N/A' if cell is None else str(cell),styles['SmallCustom']) for cell in row] for row in block[1]]
                widths=[480/len(rows[0])]*len(rows[0]);table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f2f3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d6e2e8')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.append(table);story.append(Spacer(1,12))
        if i<len(data['sections'])-1:story.append(PageBreak())
    def footer(c,doc):
        c.setStrokeColor(colors.HexColor('#d6e2e8'));c.line(54,43,541,43);c.setFont('Helvetica',8);c.setFillColor(GREY);c.drawString(54,29,data['title']+' | Simulation study');c.drawRightString(541,29,str(doc.page))
    path=root/(root.name+'-Explanation.pdf')
    SimpleDocTemplate(str(path),pagesize=(595,842),rightMargin=54,leftMargin=54,topMargin=50,bottomMargin=59,title=data['title']+' - Technical Explanation',author='Prepared for Mridul Batra with AI assistance').build(story,onFirstPage=footer,onLaterPages=footer)
    return path

if __name__=='__main__':print(render(Path(__file__).resolve().parents[1]))
