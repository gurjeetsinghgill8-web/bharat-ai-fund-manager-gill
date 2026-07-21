import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import tempfile

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Detect if the local repository directory is writeable
_is_writeable = False
try:
    _test_path = os.path.join(LOCAL_DIR, ".report_write_test")
    with open(_test_path, "w") as _f:
        _f.write("1")
    os.remove(_test_path)
    _is_writeable = True
except Exception:
    _is_writeable = False

if _is_writeable:
    REPORTS_DIR = os.path.join(LOCAL_DIR, "reports")
else:
    REPORTS_DIR = os.path.join(tempfile.gettempdir(), "reports")

os.makedirs(REPORTS_DIR, exist_ok=True)


def _resolve_path(filename):
    """Resolve filename to reports/ directory."""
    return os.path.join(REPORTS_DIR, filename)


def generate_excel_report(df, latest_highs, continuous, red_alerts, filename):
    """
    Saves the dataframes to a beautifully formatted multi-tab Excel file.
    """
    try:
        filepath = _resolve_path(filename)
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            # Write sheets
            df.to_excel(writer, sheet_name='All Ranked Stocks', index=False)
            latest_highs.to_excel(writer, sheet_name='Latest Breakouts', index=False)
            continuous.to_excel(writer, sheet_name='Sustained Momentum', index=False)
            red_alerts.to_excel(writer, sheet_name='Red Alert Blacklist', index=False)
            
            # Format workbook
            workbook  = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#0B192C',
                'font_color': '#FFFFFF',
                'border': 1
            })
            
            highlight_format = workbook.add_format({
                'fg_color': '#E8F1F5',
                'border': 1
            })
            
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.freeze_panes(1, 0)
                
                # Format headers
                # We overwrite the headers with formatting
                if sheet_name == 'All Ranked Stocks':
                    cols = df.columns
                elif sheet_name == 'Latest Breakouts':
                    cols = latest_highs.columns
                elif sheet_name == 'Sustained Momentum':
                    cols = continuous.columns
                else:
                    cols = red_alerts.columns
                    
                for col_num, value in enumerate(cols):
                    worksheet.write(0, col_num, value, header_format)
                    # Auto-fit columns
                    worksheet.set_column(col_num, col_num, max(len(str(value)) + 4, 12))
                    
        return True
    except Exception as e:
        print(f"Error generating Excel report: {str(e)}")
        return False

def generate_stock_narrative(ticker, row_data):
    """
    Generates a simple, engaging, 10th-grade reading level profile narrative.
    """
    company_name = ticker.replace(".NS", "")
    price = row_data["Price"]
    score = row_data["Total Score"]
    pe = row_data["PE"]
    eps = row_data["EPS"]
    debt = row_data["Debt/Equity"]
    reserves = row_data["Reserves"]
    promoters = row_data["Promoter %"]
    inst = row_data["Institution %"]
    public = row_data["Public %"]
    sales_cagr = row_data.get("Sales CAGR", 0)
    profit_cagr = row_data.get("Profit CAGR", 0)
    cagr_accel = row_data.get("CAGR Accelerating", False)
    
    # Financial health status
    debt_msg = "debt-free / very low debt" if debt < 0.3 else ("manageable debt" if debt < 1.0 else "high debt leverage")
    reserves_msg = f"strong reserves of {reserves} Cr" if reserves > 10 else f"reserves of {reserves} Cr"
    cagr_msg = ""
    if cagr_accel:
        cagr_msg = f" Moreover, the company's growth is accelerating — Sales CAGR is {sales_cagr}% and Profit CAGR is {profit_cagr}%, with the 3-year CAGR outpacing the 5-year CAGR, indicating strong recent momentum. "
    elif sales_cagr > 0 or profit_cagr > 0:
        cagr_msg = f" The company shows sales CAGR of {sales_cagr}% and profit CAGR of {profit_cagr}%. "
    
    story = (
        f"<b>{company_name}</b> is currently trading at ₹{price}. "
        f"It has achieved a spectacular performance rating of <b>{score}/20</b> on the Bharat AI scale. "
        f"The company has exceptionally strong fundamentals: it has a {debt_msg} (D/E: {debt}) and {reserves_msg}. "
        f"Institutions (FII & DII) hold {inst}%, showing strong institutional confidence, while Promoters hold {promoters}%. "
        f"With an EPS of {eps} and PE of {pe}, this stock displays classic high-velocity growth."
        f"{cagr_msg}"
        f"At a 10th-grade level, you can think of {company_name} as a fast-growing, highly profitable shop that has zero trouble paying its bills, "
        f"is backed by heavy-pocket investors, and is breaking historical sales records. It is a prime candidate for momentum buying."
    )
    return story

def generate_pdf_report(ranked_df, filename):
    """
    Generates a beautiful PDF report containing the ranked stock leaderboard and detailed narratives of top picks.
    """
    try:
        filepath = _resolve_path(filename)
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=45,
            leftMargin=45,
            topMargin=45,
            bottomMargin=45
        )
        
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0B192C")
        accent_color = colors.HexColor("#008DDA")
        text_color = colors.HexColor("#1E2022")
        light_bg = colors.HexColor("#F5F7F8")
        
        # Styles
        title_style = ParagraphStyle(
            'PdfTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=primary_color,
            alignment=1,
            spaceAfter=5
        )
        
        subtitle_style = ParagraphStyle(
            'PdfSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=accent_color,
            alignment=1,
            spaceAfter=25
        )
        
        h1_style = ParagraphStyle(
            'Heading1_Pdf',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            textColor=primary_color,
            spaceBefore=15,
            spaceAfter=10,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'Body_Pdf',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=text_color,
            spaceAfter=10
        )
        
        table_hdr = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.whitesmoke)
        table_body = ParagraphStyle('TblBdy', fontName='Helvetica', fontSize=8, leading=10, textColor=text_color)
        table_body_bold = ParagraphStyle('TblBdyBld', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=primary_color)
        
        story = []
        
        # Header
        story.append(Paragraph("BHARAT AI FUND MANAGER GILL", title_style))
        story.append(Paragraph("Weekly Momentum Strategy & Fund Ranking Report", subtitle_style))
        
        # Overview Text
        story.append(Paragraph(
            "This report highlights the top momentum breakout candidates in the Nifty space. "
            "Stocks are scored out of 20 points based on their current price breakout, sales ATH, profit ATH, "
            "latest quarter profit performance, and PE/EPS evaluation. We focus on riding trends in the strongest companies "
            "and exiting when fundamentals drop.",
            body_style
        ))
        story.append(Spacer(1, 10))
        
        # Leaderboard Table
        story.append(Paragraph("Top Performing Stock Leaderboard", h1_style))
        
        # Select top 15 stocks to display in the main PDF table
        top_df = ranked_df.head(15)
        
        table_data = [[
            Paragraph("Ticker", table_hdr),
            Paragraph("Cap", table_hdr),
            Paragraph("Price (₹)", table_hdr),
            Paragraph("Score", table_hdr),
            Paragraph("Debt/Eq", table_hdr),
            Paragraph("Promoter %", table_hdr),
            Paragraph("Inst %", table_hdr),
            Paragraph("Status", table_hdr)
        ]]
        
        for idx, row in top_df.iterrows():
            table_data.append([
                Paragraph(row["Ticker"].replace(".NS", ""), table_body_bold),
                Paragraph(row["Category"], table_body),
                Paragraph(str(row["Price"]), table_body),
                Paragraph(f"<b>{row['Total Score']}/20</b>", table_body),
                Paragraph(str(row["Debt/Equity"]), table_body),
                Paragraph(str(row["Promoter %"]), table_body),
                Paragraph(str(row["Institution %"]), table_body),
                Paragraph(row["Momentum Status"], table_body)
            ])
            
        t = Table(table_data, colWidths=[80, 65, 60, 50, 50, 65, 55, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0E0")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg])
        ]))
        story.append(t)
        
        story.append(PageBreak())
        
        # Narrative Reports for Top Picks (Score == 10)
        top_picks = ranked_df[ranked_df["Total Score"] == 10]
        if not top_picks.empty:
            story.append(Paragraph("Detailed Projections & Business Stories (Top Picks)", h1_style))
            story.append(Paragraph(
                "The following stocks scored 10/10 (All-Time High Sales and Profits). Below are their simplified profiles, structural momentum stories, "
                "and balance sheet setups.",
                body_style
            ))
            story.append(Spacer(1, 10))
            
            for idx, row in top_picks.head(6).iterrows(): # Max 6 picks in narrative list to save pages
                story.append(Paragraph(f"♦ {row['Ticker'].replace('.NS', '')} — Score: {row['Total Score']}/10", h1_style))
                narrative_text = generate_stock_narrative(row["Ticker"], row)
                story.append(Paragraph(narrative_text, body_style))
                story.append(Spacer(1, 5))
                
        # Build document
        doc.build(story)
        return True
    except Exception as e:
        print(f"Error generating PDF report: {str(e)}")
        return False

def generate_stock_narrative_v2(ticker, row_data):
    """
    Generates a simple, engaging, 10th-grade reading level profile narrative for Page 2.
    """
    company_name = ticker.replace(".NS", "")
    price = row_data.get("Price", 0)
    score = row_data.get("Total Score", 0)
    pe = row_data.get("PE", 0)
    eps = row_data.get("EPS", 0)
    debt = row_data.get("Debt/Equity", 0)
    reserves = row_data.get("Reserves", 0)
    promoters = row_data.get("Promoter %", 0)
    inst = row_data.get("Institution %", 0)
    sales_cagr = row_data.get("Sales CAGR", 0)
    profit_cagr = row_data.get("Profit CAGR", 0)
    sma_200 = row_data.get("200 SMA", 0)
    dist_pct = row_data.get("200 SMA Dist %", 0)
    value_fit = row_data.get("Value Fit", row_data.get("PE vs EPS Score", 0) > 0)
    cagr_accel = row_data.get("CAGR Accelerating", False)
    
    debt_msg = "debt-free / very low debt" if debt < 0.3 else ("manageable debt" if debt < 1.0 else "high debt leverage")
    reserves_msg = f"strong reserves of {reserves} Cr" if reserves > 10 else f"reserves of {reserves} Cr"
    value_fit_msg = "It has a great value-momentum fit (PE is less than EPS)." if value_fit else "PE is higher than EPS."
    cagr_msg = ""
    if cagr_accel:
        cagr_msg = f" Best of all, the growth trajectory is accelerating — the 3-year CAGR is outpacing the 5-year CAGR, meaning the company is growing faster now than it did in the past. "
    
    story = (
        f"<b>{company_name}</b> is currently trading at ₹{price}. "
        f"It has achieved a value-momentum rating of <b>{score}/16</b> on the Bharat AI scale. "
        f"The price is sitting just {dist_pct}% away from its 200-day average price (₹{sma_200}), which is an attractive consolidation point. "
        f"The company has strong growth fundamentals, growing its annual sales at a CAGR of {sales_cagr}% and net profits at a CAGR of {profit_cagr}%. "
        f"{cagr_msg}"
        f"It has a {debt_msg} (D/E: {debt}) and {reserves_msg}. Promoter group holds {promoters}% and institutional investors hold {inst}%. "
        f"{value_fit_msg} At a 10th-grade level, this is like buying a healthy, fast-growing franchise at a very reasonable average price instead of chasing it at all-time highs."
    )
    return story

def generate_excel_report_v2(df, continuous, red_alerts, filename):
    """
    Saves the Page 2 dataframes to a beautifully formatted multi-tab Excel file.
    """
    try:
        filepath = _resolve_path(filename)
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='All Value Stocks', index=False)
            continuous.to_excel(writer, sheet_name='Sustained Momentum', index=False)
            red_alerts.to_excel(writer, sheet_name='Red Alert Blacklist', index=False)
            
            workbook  = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#0B192C',
                'font_color': '#FFFFFF',
                'border': 1
            })
            
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.freeze_panes(1, 0)
                
                if sheet_name == 'All Value Stocks':
                    cols = df.columns
                elif sheet_name == 'Sustained Momentum':
                    cols = continuous.columns
                else:
                    cols = red_alerts.columns
                    
                for col_num, value in enumerate(cols):
                    worksheet.write(0, col_num, value, header_format)
                    worksheet.set_column(col_num, col_num, max(len(str(value)) + 4, 12))
                    
        return True
    except Exception as e:
        print(f"Error generating Excel report: {str(e)}")
        return False

def generate_pdf_report_v2(ranked_df, filename):
    """
    Generates a PDF report containing the Page 2 Value & SMA leaderboard and detailed narratives of top picks.
    """
    try:
        filepath = _resolve_path(filename)
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=45,
            leftMargin=45,
            topMargin=45,
            bottomMargin=45
        )
        
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0B192C")
        accent_color = colors.HexColor("#008DDA")
        text_color = colors.HexColor("#1E2022")
        light_bg = colors.HexColor("#F5F7F8")
        
        title_style = ParagraphStyle(
            'PdfTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=primary_color,
            alignment=1,
            spaceAfter=5
        )
        
        subtitle_style = ParagraphStyle(
            'PdfSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=accent_color,
            alignment=1,
            spaceAfter=25
        )
        
        h1_style = ParagraphStyle(
            'Heading1_Pdf',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            textColor=primary_color,
            spaceBefore=15,
            spaceAfter=10,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'Body_Pdf',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=text_color,
            spaceAfter=10
        )
        
        table_hdr = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.whitesmoke)
        table_body = ParagraphStyle('TblBdy', fontName='Helvetica', fontSize=7.5, leading=9, textColor=text_color)
        table_body_bold = ParagraphStyle('TblBdyBld', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=primary_color)
        
        story = []
        
        story.append(Paragraph("BHARAT AI FUND MANAGER GILL", title_style))
        story.append(Paragraph("Value & 200 SMA Investment Strategy Report", subtitle_style))
        
        story.append(Paragraph(
            "This report details the top value-momentum entries in the Indian equities space. "
            "Stocks shown are priced above their 200-day simple moving average (200 SMA), scored out of 16 points "
            "(based on Peak annual sales, Peak annual profits, sales growth CAGR, and profit growth CAGR), "
            "and sorted by proximity to the 200 SMA. The goal is to purchase fundamentally strong companies close to their "
            "long-term moving averages.",
            body_style
        ))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("Value & 200 SMA Leaderboard (Closest to 200 SMA First)", h1_style))
        
        top_df = ranked_df.head(15)
        
        table_data = [[
            Paragraph("Ticker", table_hdr),
            Paragraph("Price (₹)", table_hdr),
            Paragraph("Score", table_hdr),
            Paragraph("200 SMA", table_hdr),
            Paragraph("Dist %", table_hdr),
            Paragraph("Sales CAGR", table_hdr),
            Paragraph("Profit CAGR", table_hdr),
            Paragraph("Fit", table_hdr)
        ]]
        
        for idx, row in top_df.iterrows():
            fit_text = "Yes" if row["Value Fit"] else "No"
            table_data.append([
                Paragraph(row["Ticker"].replace(".NS", ""), table_body_bold),
                Paragraph(str(row["Price"]), table_body),
                Paragraph(f"<b>{row['Total Score']}/16</b>", table_body),
                Paragraph(str(row["200 SMA"]), table_body),
                Paragraph(f"{row['200 SMA Dist %']}%", table_body),
                Paragraph(f"{row['Sales CAGR']}%", table_body),
                Paragraph(f"{row['Profit CAGR']}%", table_body),
                Paragraph(fit_text, table_body)
            ])
            
        t = Table(table_data, colWidths=[85, 60, 50, 60, 50, 75, 75, 45])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0E0")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg])
        ]))
        story.append(t)
        
        story.append(PageBreak())
        
        # Narrative Reports for Top Picks (Score >= 11/16)
        top_picks = ranked_df[ranked_df["Total Score"] >= 11]
        if not top_picks.empty:
            story.append(Paragraph("Detailed Projections & Business Stories (Top Picks)", h1_style))
            story.append(Paragraph(
                "The following stocks scored 11/16 or higher on our Value & 200 SMA Engine. Below are their simplified profiles, "
                "growth metrics, and balance sheet configurations.",
                body_style
            ))
            story.append(Spacer(1, 10))
            
            for idx, row in top_picks.head(6).iterrows():
                story.append(Paragraph(f"♦ {row['Ticker'].replace('.NS', '')} — Score: {row['Total Score']}/16", h1_style))
                narrative_text = generate_stock_narrative_v2(row["Ticker"], row)
                story.append(Paragraph(narrative_text, body_style))
                story.append(Spacer(1, 5))
                
        doc.build(story)
        return True
    except Exception as e:
        print(f"Error generating PDF report: {str(e)}")
        return False


def generate_user_manual_pdf(filename="user_manual.pdf"):
    """
    Generates a beautifully formatted User & Setup Manual PDF using ReportLab.
    Save it to reports/ directory and return filepath.
    """
    try:
        filepath = _resolve_path(filename)
        doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        
        # Color System
        primary_color = colors.HexColor("#0B192C")
        accent_color = colors.HexColor("#008DDA")
        text_color = colors.HexColor("#333333")
        light_bg = colors.HexColor("#F5F7F8")
        
        # Styles
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'ManualTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color,
            alignment=1,
            spaceAfter=15
        )
        
        h1_style = ParagraphStyle(
            'ManualH1',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'ManualBody',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=text_color,
            spaceAfter=8
        )
        
        bullet_style = ParagraphStyle(
            'ManualBullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=text_color,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=5
        )
        
        code_style = ParagraphStyle(
            'ManualCode',
            parent=styles['Code'],
            fontName='Courier',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2C3E50"),
            backColor=colors.HexColor("#ECF0F1"),
            borderPadding=6,
            spaceAfter=10
        )
        
        # Header / Cover Info
        story.append(Paragraph("BHARAT AI FUND MANAGER GILL — USER MANUAL & SETUP GUIDE", title_style))
        story.append(Paragraph("Complete Technical Documentation, Twice-Daily Background Sync Setup, and Email Settings", ParagraphStyle('ManualSub', fontName='Helvetica-Oblique', fontSize=10, textColor=accent_color, alignment=1, spaceAfter=20)))
        story.append(Spacer(1, 10))
        
        # Section 1: Overview
        story.append(Paragraph("1. System Overview", h1_style))
        story.append(Paragraph(
            "The Bharat AI Fund Manager is a persistent, multi-user portfolio tracking and autonomous option/equity momentum screening tool "
            "designed specifically for Indian equities (NSE & BSE). It tracks and ranks stocks using a multi-factor scoring engine, matches them "
            "against their 200-day Simple Moving Average (SMA), and issues automated siren and email alerts if any stock slips into a bearish zone.",
            body_style
        ))
        
        # Section 2: How Email Alerts Work
        story.append(Paragraph("2. How Automated Email Alerts Work (100% Free!)", h1_style))
        story.append(Paragraph(
            "The system uses the standard Simple Mail Transfer Protocol (SMTP) to send outgoing emails. This process is **completely free** "
            "and does not require paying for any external services like SendGrid or Mailchimp. You can configure it to send alerts via your regular "
            "free Gmail account.",
            body_style
        ))
        story.append(Paragraph(
            "<b>How to set up SMTP with a Free Gmail account:</b>", body_style
        ))
        story.append(Paragraph(
            "• Step 1: Open your Google Account Settings (myaccount.google.com).<br/>"
            "• Step 2: Go to Security -> 2-Step Verification and enable it.<br/>"
            "• Step 3: Scroll down to the bottom of the 2-step verification page and click on 'App passwords'.<br/>"
            "• Step 4: Create a new app password (select App='Other' and name it 'BharatAI'). Copy the 16-character code generated.<br/>"
            "• Step 5: Put this 16-character code as the SMTP_PASSWORD in your <code>.env</code> file (spaces removed).",
            bullet_style
        ))
        story.append(Spacer(1, 5))
        
        # Section 3: Configuration Variables (.env)
        story.append(Paragraph("3. Configuration Settings (.env file)", h1_style))
        story.append(Paragraph(
            "To activate emails and options, create or edit the <code>.env</code> file in the repository root directory with the following variables:",
            body_style
        ))
        story.append(Paragraph(
            "SMTP_SERVER=smtp.gmail.com<br/>"
            "SMTP_PORT=587<br/>"
            "SMTP_USER=your_gmail@gmail.com<br/>"
            "SMTP_PASSWORD=your_16_char_app_password<br/>"
            "EMAIL_RECIPIENTS=recipient1@gmail.com,recipient2@gmail.com (global fallback list)<br/>"
            "GEMINI_API_KEY=AIzaSy... (for Jarvis Gen AI consultation stories)",
            code_style
        ))
        
        # Section 4: Twice-Daily Scans Setup
        story.append(Paragraph("4. Setting Up Twice-Daily Automatic Background Scans", h1_style))
        story.append(Paragraph(
            "To enable fully hands-free background updates on your system:",
            body_style
        ))
        story.append(Paragraph(
            "1. Locate the file <b><code>setup_task_scheduler.bat</code></b> in your folder.<br/>"
            "2. Right-click on it and select <b>'Run as Administrator'</b>.<br/>"
            "3. This will instantly install two Windows Tasks to run silently in the background:<br/>"
            "   - <b>Morning Scan (10:00 AM IST)</b>: Runs as market opens to check pre-opening and early momentum.<br/>"
            "   - <b>Closing Scan (04:00 PM IST)</b>: Runs after market closes to capture closing prices and check 200 SMA breaches.<br/>"
            "4. If any stock triggers a breach, you will receive an instant Email Alert, a Windows Desktop Notification, and a siren sound beep.",
            bullet_style
        ))
        
        # Section 5: Multi-User Isolation & Database
        story.append(Paragraph("5. Multi-User Isolation & SQLite Database", h1_style))
        story.append(Paragraph(
            "All settings, user accounts, and portfolios are stored locally inside the persistent SQLite database file (<code>bharat_ai_fund.db</code>). "
            "This ensures that your holdings are completely separated from other users. You can switch between users (e.g. Gurjas, Sister, Dost) or edit "
            "user email addresses directly in the sidebar panel.",
            body_style
        ))
        
        # Section 6: Scoring System Details
        story.append(Paragraph("6. Simplified Page 1 Scoring & Bull Status", h1_style))
        story.append(Paragraph(
            "The Page 1 Leaderboard score is simplified to focus purely on business growth peak metrics, out of a maximum of <b>10 marks</b>:",
            body_style
        ))
        story.append(Paragraph(
            "• <b>Sales ATH (5 Marks)</b>: 5 points if the latest annual sales value is at an all-time high.<br/>"
            "• <b>Profit ATH (5 Marks)</b>: 5 points if the latest annual profit value is at an all-time high.<br/>"
            "• <b>Bull Badge (🐂)</b>: Awarded if the stock has a 10/10 score OR both Sales and Profit CAGRs are above 20%.<br/>"
            "• <b>Double Bull Badge (🐂🐂)</b>: Awarded if the stock has a 10/10 score AND both CAGRs are above 20% (indicating supercharged breakout setup).",
            bullet_style
        ))
        
        doc.build(story)
        return True
    except Exception as e:
        print(f"Error generating User Manual PDF: {str(e)}")
        return False
