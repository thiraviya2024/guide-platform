# app/services/pdf_service.py
"""
PDF Report Generation Service
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional  # ← Add Optional here
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import logging

logger = logging.getLogger(__name__)


class PDFService:
    """Generates PDF reports for lab results."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        os.makedirs("reports", exist_ok=True)
    
    def _setup_styles(self):
        """Setup custom styles."""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#0d47a1'),
            spaceAfter=12
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6
        )
    
    def generate_report(
        self, 
        patient_info: Dict[str, Any],
        results: Dict[str, Any],
        disease_risks: List[Dict[str, Any]],
        overall_status: str,
        ai_explanation: Optional[str] = None
    ) -> str:
        """Generate PDF report."""
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/Health_Report_{timestamp}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build story
        story = []
        
        # Header
        story.append(Paragraph("<b>LifeSaver Health Report</b>", self.title_style))
        story.append(Spacer(1, 20))
        
        # Patient Info
        story.append(Paragraph("<b>Patient Information</b>", self.heading_style))
        info_text = f"""
        Name: {patient_info.get('name', 'N/A')}<br/>
        Age: {patient_info.get('age', 'N/A')}<br/>
        Gender: {patient_info.get('gender', 'N/A')}<br/>
        Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        story.append(Paragraph(info_text, self.normal_style))
        story.append(Spacer(1, 20))
        
        # Overall Status
        story.append(Paragraph("<b>Overall Health Status</b>", self.heading_style))
        color = "green" if "Normal" in overall_status else "orange" if "Minor" in overall_status else "red"
        story.append(Paragraph(f'<font color="{color}"><b>{overall_status}</b></font>', self.normal_style))
        story.append(Spacer(1, 20))
        
        # Results
        story.append(Paragraph("<b>Test Results</b>", self.heading_style))
        data = [['Parameter', 'Value', 'Status']]
        
        for category, params in results.items():
            if isinstance(params, list):
                for param in params:
                    if isinstance(param, dict):
                        data.append([
                            param.get('parameter', 'N/A'),
                            str(param.get('value', 'N/A')),
                            param.get('status', 'N/A')
                        ])
            elif isinstance(params, dict):
                for param_name, param_data in params.items():
                    if isinstance(param_data, dict):
                        data.append([
                            param_name,
                            str(param_data.get('value', 'N/A')),
                            param_data.get('status', 'N/A')
                        ])
        
        if len(data) > 1:  # Only create table if there's data
            table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(table)
            story.append(Spacer(1, 20))
        
        # Disease Risks
        if disease_risks:
            story.append(Paragraph("<b>Disease Risks Detected</b>", self.heading_style))
            for risk in disease_risks:
                risk_text = f"""
                <b>{risk.get('disease', 'N/A')}</b><br/>
                Confidence: {risk.get('confidence', 'N/A')}<br/>
                Reason: {risk.get('reason', 'N/A')}
                """
                story.append(Paragraph(risk_text, self.normal_style))
                story.append(Spacer(1, 10))
        
        # AI Explanation
        if ai_explanation:
            story.append(PageBreak())
            story.append(Paragraph("<b>AI-Powered Health Insights</b>", self.heading_style))
            story.append(Spacer(1, 10))
            # Replace newlines with <br/> for PDF
            explanation_text = ai_explanation.replace('\n', '<br/>')
            story.append(Paragraph(explanation_text, self.normal_style))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>",
            self.normal_style
        ))
        story.append(Paragraph(
            "<i>Disclaimer: This report is for informational purposes only. Please consult a healthcare professional.</i>",
            self.normal_style
        ))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"✅ PDF report generated: {filename}")
        return filename