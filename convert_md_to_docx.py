"""
FlowGrid - Markdown to DOCX Converter
Converts FlowGrid_Proposal.md into a formatted Word Document (.docx)
using python-docx with professional styling, tables, callout blocks, and code blocks.
"""

import os
import re
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    """Sets background color for a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell margins (padding) in dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_formatted_text(paragraph, text, is_bold=False, is_italic=False, is_code=False, color=None):
    """Parses inline bold, italic, and code formatting within a paragraph."""
    # Pattern to match bold-italic, bold, italic, inline code
    # Simple regex tokenizer
    tokens = re.split(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))', text)
    
    for token in tokens:
        if not token:
            continue
        
        run_bold = is_bold
        run_italic = is_italic
        run_code = is_code
        run_text = token
        
        if token.startswith('***') and token.endswith('***') and len(token) >= 6:
            run_text = token[3:-3]
            run_bold = True
            run_italic = True
        elif token.startswith('**') and token.endswith('**') and len(token) >= 4:
            run_text = token[2:-2]
            run_bold = True
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            run_text = token[1:-1]
            run_italic = True
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            run_text = token[1:-1]
            run_code = True
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            # Link markdown [text](url) -> render as text
            m = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if m:
                run_text = m.group(1)
        
        run = paragraph.add_run(run_text)
        run.bold = run_bold
        run.italic = run_italic
        
        if run_code:
            run.font.name = 'Consolas'
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(180, 40, 40)
        elif color:
            run.font.color.rgb = color

def convert_markdown_to_docx(md_path, docx_path):
    print(f"[*] Reading Markdown from: {md_path}")
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    doc = Document()
    
    # Page Setup (Standard Letter / A4 with 1 inch margins)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        # Add Page Numbering / Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("FlowGrid | Adaptive Traffic Signal Control System — Team Jam Breakers")
        hrun.font.name = 'Segoe UI'
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(128, 128, 128)

    # Styles
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Segoe UI'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(33, 37, 41)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(4)

    i = 0
    in_code_block = False
    code_block_lines = []
    
    while i < len(lines):
        line = lines[i].rstrip('\r\n')
        
        # 1. Code Block Fence
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block -> write table or callout with monospace font
                code_text = "\n".join(code_block_lines)
                table = doc.add_table(rows=1, cols=1)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = table.cell(0, 0)
                set_cell_background(cell, "F3F4F6")
                set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
                
                cp = cell.paragraphs[0]
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                cp.paragraph_format.line_spacing = 1.05
                crun = cp.add_run(code_text)
                crun.font.name = 'Consolas'
                crun.font.size = Pt(8.5)
                crun.font.color.rgb = RGBColor(30, 41, 59)
                
                # Add spacing after table
                sp = doc.add_paragraph()
                sp.paragraph_format.space_before = Pt(0)
                sp.paragraph_format.space_after = Pt(4)
                
                in_code_block = False
                code_block_lines = []
            else:
                in_code_block = True
                code_block_lines = []
            i += 1
            continue
            
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # 2. Markdown Table
        if line.strip().startswith('|') and line.strip().endswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Parse table rows
            rows_data = []
            for tl in table_lines:
                # check if separator row |---|---|
                if re.match(r'^\|(\s*:?-+:?\s*\|)+$', tl):
                    continue
                cells = [c.strip() for c in tl.split('|')[1:-1]]
                rows_data.append(cells)
            
            if rows_data:
                num_cols = max(len(r) for r in rows_data)
                num_rows = len(rows_data)
                
                table = doc.add_table(rows=num_rows, cols=num_cols)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                
                for r_idx, row in enumerate(rows_data):
                    is_header = (r_idx == 0)
                    for c_idx in range(num_cols):
                        cell_text = row[c_idx] if c_idx < len(row) else ""
                        cell = table.cell(r_idx, c_idx)
                        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
                        
                        if is_header:
                            set_cell_background(cell, "1E3A8A") # Navy header
                            p = cell.paragraphs[0]
                            p.paragraph_format.space_before = Pt(2)
                            p.paragraph_format.space_after = Pt(2)
                            add_formatted_text(p, cell_text, is_bold=True, color=RGBColor(255, 255, 255))
                        else:
                            bg = "F9FAFB" if (r_idx % 2 == 1) else "FFFFFF"
                            set_cell_background(cell, bg)
                            p = cell.paragraphs[0]
                            p.paragraph_format.space_before = Pt(2)
                            p.paragraph_format.space_after = Pt(2)
                            add_formatted_text(p, cell_text)
                
                # Add spacing after table
                sp = doc.add_paragraph()
                sp.paragraph_format.space_before = Pt(0)
                sp.paragraph_format.space_after = Pt(6)
            continue
        
        # 3. Horizontal Rule
        if line.strip() in ['---', '***', '___']:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(8)
            run = p.add_run("―" * 45)
            run.font.color.rgb = RGBColor(200, 205, 215)
            run.font.size = Pt(8)
            i += 1
            continue

        # 4. Headings
        if line.startswith('# '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            add_formatted_text(p, line[2:].strip(), is_bold=True, color=RGBColor(15, 23, 42))
            p.runs[0].font.size = Pt(24)
            i += 1
            continue
        elif line.startswith('## '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(16)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            add_formatted_text(p, line[3:].strip(), is_bold=True, color=RGBColor(30, 58, 138))
            for r in p.runs:
                r.font.size = Pt(16)
            i += 1
            continue
        elif line.startswith('### '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            add_formatted_text(p, line[4:].strip(), is_bold=True, color=RGBColor(14, 116, 144))
            for r in p.runs:
                r.font.size = Pt(13)
            i += 1
            continue
        elif line.startswith('#### '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            add_formatted_text(p, line[5:].strip(), is_bold=True, color=RGBColor(51, 65, 85))
            for r in p.runs:
                r.font.size = Pt(11)
            i += 1
            continue

        # 5. Blockquotes (Callout boxes for Design Choices)
        if line.startswith('> '):
            quote_lines = []
            while i < len(lines) and (lines[i].startswith('> ') or lines[i].strip() == '>'):
                quote_lines.append(lines[i][2:].strip() if lines[i].startswith('> ') else "")
                i += 1
            
            quote_text = "\n".join(quote_lines)
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = table.cell(0, 0)
            set_cell_background(cell, "EFF6FF") # Light blue callout
            set_cell_margins(cell, top=100, bottom=100, left=180, right=140)
            
            # Left border styling
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="36" w:space="0" w:color="0284C7"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
            tcPr.append(tcBorders)
            
            for q_idx, q_line in enumerate(quote_lines):
                if q_idx == 0:
                    p = cell.paragraphs[0]
                else:
                    p = cell.add_paragraph()
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.15
                add_formatted_text(p, q_line)
                for r in p.runs:
                    r.font.size = Pt(9.5)
            
            sp = doc.add_paragraph()
            sp.paragraph_format.space_before = Pt(0)
            sp.paragraph_format.space_after = Pt(4)
            continue

        # 6. Bullet Lists
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            bullet_text = line.strip()[2:].strip()
            add_formatted_text(p, bullet_text)
            i += 1
            continue

        # 7. Numbered Lists
        num_match = re.match(r'^\s*(\d+)\.\s+(.*)$', line)
        if num_match:
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            list_text = num_match.group(2)
            add_formatted_text(p, list_text)
            i += 1
            continue

        # 8. Regular Paragraph
        if line.strip():
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_text(p, line.strip())
        
        i += 1

    try:
        doc.save(docx_path)
        print(f"[+] DOCX successfully generated: {docx_path}")
    except PermissionError:
        fallback_path = docx_path.replace(".docx", "_Updated.docx")
        doc.save(fallback_path)
        print(f"[!] Warning: {docx_path} is currently open in Word. Saved to: {fallback_path}")

if __name__ == '__main__':
    src_md = r"e:\GitHub\DataForLife Smart Traffic Lights\FlowGrid_Proposal.md"
    dst_docx = r"e:\GitHub\DataForLife Smart Traffic Lights\FlowGrid_Proposal.docx"
    convert_markdown_to_docx(src_md, dst_docx)
