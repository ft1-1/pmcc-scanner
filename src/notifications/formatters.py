"""
Formatters for converting PMCC opportunities into notification content.
"""

from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from src.models.pmcc_models import PMCCCandidate
from src.notifications.models import NotificationTemplate


class WhatsAppFormatter:
    """Formats PMCC opportunities for WhatsApp messages."""
    
    @staticmethod
    def format_opportunity(candidate: PMCCCandidate) -> NotificationTemplate:
        """
        Format a single PMCC opportunity for WhatsApp.
        
        WhatsApp messages should be concise and scannable for quick decision-making.
        """
        symbol = candidate.symbol
        underlying_price = candidate.underlying_price
        analysis = candidate.analysis
        
        # Get key metrics
        net_debit = analysis.net_debit
        max_profit = analysis.risk_metrics.max_profit if analysis.risk_metrics else None
        max_loss = analysis.risk_metrics.max_loss if analysis.risk_metrics else None
        risk_reward = candidate.risk_reward_ratio
        
        # Format profit/loss as percentages
        profit_pct = ""
        if max_profit and net_debit > 0:
            profit_pct = f" ({(max_profit / net_debit * 100):.1f}%)"
        
        # Build message
        message_lines = [
            f"🎯 *PMCC Opportunity: {symbol}*",
            f"💰 Current Price: ${underlying_price:.2f}",
            "",
            f"📈 *Long LEAPS*",
            f"Strike: ${analysis.long_call.strike:.2f}",
            f"Exp: {analysis.long_call.expiration.strftime('%b %d, %Y')}",
            f"Cost: ${analysis.long_call.ask:.2f}" if analysis.long_call.ask else "Cost: N/A",
            "",
            f"📉 *Short Call*",
            f"Strike: ${analysis.short_call.strike:.2f}",
            f"Exp: {analysis.short_call.expiration.strftime('%b %d, %Y')}",
            f"Credit: ${analysis.short_call.bid:.2f}" if analysis.short_call.bid else "Credit: N/A",
            "",
            f"💳 *Position Summary*",
            f"Net Cost: ${net_debit:.2f}",
        ]
        
        if max_profit:
            message_lines.append(f"Max Profit: ${max_profit:.2f}{profit_pct}")
        
        if max_loss:
            message_lines.append(f"Max Loss: ${max_loss:.2f}")
        
        if risk_reward:
            message_lines.append(f"Risk/Reward: 1:{risk_reward:.2f}")
        
        # Add liquidity score
        message_lines.extend([
            "",
            f"📊 Liquidity Score: {candidate.liquidity_score:.0f}/100"
        ])
        
        # Add time-sensitive note
        message_lines.extend([
            "",
            f"⏰ Scanned at {datetime.now().strftime('%I:%M %p')}"
        ])
        
        return NotificationTemplate(
            text_content="\n".join(message_lines)
        )
    
    @staticmethod
    def format_multiple_opportunities(candidates: List[PMCCCandidate], limit: int = 5) -> NotificationTemplate:
        """
        Format multiple PMCC opportunities for WhatsApp.
        
        For multiple opportunities, provide a summary with top picks.
        """
        if not candidates:
            return NotificationTemplate(
                text_content="🔍 No profitable PMCC opportunities found in today's scan."
            )
        
        # Sort by total score (best first)
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: x.total_score or 0, 
            reverse=True
        )
        
        top_candidates = sorted_candidates[:limit]
        
        message_lines = [
            f"🎯 *PMCC Daily Scan Results*",
            f"Found opportunities in {len(candidates)} stocks",
            f"Showing top {len(top_candidates)}:",
            ""
        ]
        
        for i, candidate in enumerate(top_candidates, 1):
            profit_pct = ""
            if (candidate.analysis.risk_metrics and 
                candidate.analysis.risk_metrics.max_profit and 
                candidate.analysis.net_debit > 0):
                profit_pct = f" ({(candidate.analysis.risk_metrics.max_profit / candidate.analysis.net_debit * 100):.1f}%)"
            
            message_lines.extend([
                f"*{i}. {candidate.symbol}* - ${candidate.underlying_price:.2f}",
                f"   Net Cost: ${candidate.analysis.net_debit:.2f}",
                f"   Max Profit: ${candidate.analysis.risk_metrics.max_profit:.2f}{profit_pct}" if candidate.analysis.risk_metrics and candidate.analysis.risk_metrics.max_profit else "   Max Profit: N/A",
                f"   Score: {candidate.total_score:.0f}/100" if candidate.total_score else "   Score: N/A",
                ""
            ])
        
        message_lines.extend([
            f"⏰ Scan completed at {datetime.now().strftime('%I:%M %p')}",
            "",
            "Reply with symbol for detailed analysis"
        ])
        
        return NotificationTemplate(
            text_content="\n".join(message_lines)
        )


class EmailFormatter:
    """Formats PMCC opportunities for email notifications."""
    
    @staticmethod
    def format_opportunity(candidate: PMCCCandidate) -> NotificationTemplate:
        """
        Format a single PMCC opportunity for email.
        
        Email format includes comprehensive analysis and detailed metrics.
        """
        symbol = candidate.symbol
        underlying_price = candidate.underlying_price
        analysis = candidate.analysis
        
        # Subject line
        subject = f"PMCC Opportunity Alert: {symbol} - Potential "
        if analysis.risk_metrics and analysis.risk_metrics.max_profit:
            profit_pct = (analysis.risk_metrics.max_profit / analysis.net_debit * 100)
            subject += f"{profit_pct:.1f}% Return"
        else:
            subject += "Profitable Setup"
        
        # HTML content
        html_content = EmailFormatter._generate_html_content(candidate)
        
        # Plain text content
        text_content = EmailFormatter._generate_text_content(candidate)
        
        return NotificationTemplate(
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    @staticmethod
    def format_multiple_opportunities(candidates: List[PMCCCandidate]) -> NotificationTemplate:
        """Format multiple PMCC opportunities for email."""
        if not candidates:
            return NotificationTemplate(
                subject="PMCC Daily Scan - No Opportunities Found",
                text_content="No profitable PMCC opportunities were found in today's market scan.",
                html_content="<p>No profitable PMCC opportunities were found in today's market scan.</p>"
            )
        
        # Sort by total score
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: x.total_score or 0, 
            reverse=True
        )
        
        subject = f"PMCC Daily Scan - {len(candidates)} Opportunities Found"
        
        # Generate summary email
        html_content = EmailFormatter._generate_summary_html(sorted_candidates)
        text_content = EmailFormatter._generate_summary_text(sorted_candidates)
        
        return NotificationTemplate(
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    @staticmethod
    def format_daily_summary(
        candidates: List[PMCCCandidate], 
        scan_metadata: Optional[dict] = None
    ) -> NotificationTemplate:
        """
        Format comprehensive daily summary email with all PMCC opportunities.
        
        Args:
            candidates: List of all PMCC opportunities found
            scan_metadata: Optional metadata about the scan (duration, stocks screened, etc.)
        
        Returns:
            NotificationTemplate with professional HTML email format
        """
        scan_date = datetime.now().strftime('%B %d, %Y')
        scan_time = datetime.now().strftime('%I:%M %p %Z')
        
        # Create subject line
        if not candidates:
            subject = f"PMCC Daily Summary - {scan_date} - No Opportunities"
        else:
            subject = f"PMCC Daily Summary - {scan_date} - {len(candidates)} Opportunities"
        
        # Sort opportunities by score (highest first)
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: x.total_score or 0, 
            reverse=True
        )
        
        # Generate content
        html_content = EmailFormatter._generate_daily_summary_html(
            sorted_candidates, scan_metadata, scan_date, scan_time
        )
        text_content = EmailFormatter._generate_daily_summary_text(
            sorted_candidates, scan_metadata, scan_date, scan_time
        )
        
        return NotificationTemplate(
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    @staticmethod
    def _generate_html_content(candidate: PMCCCandidate) -> str:
        """Generate HTML content for a single opportunity."""
        symbol = candidate.symbol
        underlying_price = candidate.underlying_price
        analysis = candidate.analysis
        
        # Calculate metrics
        profit_pct = ""
        if (analysis.risk_metrics and 
            analysis.risk_metrics.max_profit and 
            analysis.net_debit > 0):
            profit_pct = f" ({(analysis.risk_metrics.max_profit / analysis.net_debit * 100):.1f}%)"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h2 style="color: #2E8B57;">PMCC Opportunity: {symbol}</h2>
            
            <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📊 Current Market Data</h3>
                <p><strong>Underlying Price:</strong> ${underlying_price:.2f}</p>
                <p><strong>Analysis Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📈 Long LEAPS Position</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td><strong>Option Symbol:</strong></td><td>{analysis.long_call.option_symbol}</td></tr>
                    <tr><td><strong>Strike Price:</strong></td><td>${analysis.long_call.strike:.2f}</td></tr>
                    <tr><td><strong>Expiration:</strong></td><td>{analysis.long_call.expiration.strftime('%B %d, %Y')}</td></tr>
                    <tr><td><strong>Days to Expiration:</strong></td><td>{analysis.long_call.dte} days</td></tr>
                    <tr><td><strong>Bid/Ask:</strong></td><td>${analysis.long_call.bid:.2f} / ${analysis.long_call.ask:.2f}</td></tr>
                    <tr><td><strong>Delta:</strong></td><td>{analysis.long_call.delta:.3f}</td></tr>
                </table>
            </div>
            
            <div style="background-color: #fff5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📉 Short Call Position</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td><strong>Option Symbol:</strong></td><td>{analysis.short_call.option_symbol}</td></tr>
                    <tr><td><strong>Strike Price:</strong></td><td>${analysis.short_call.strike:.2f}</td></tr>
                    <tr><td><strong>Expiration:</strong></td><td>{analysis.short_call.expiration.strftime('%B %d, %Y')}</td></tr>
                    <tr><td><strong>Days to Expiration:</strong></td><td>{analysis.short_call.dte} days</td></tr>
                    <tr><td><strong>Bid/Ask:</strong></td><td>${analysis.short_call.bid:.2f} / ${analysis.short_call.ask:.2f}</td></tr>
                    <tr><td><strong>Delta:</strong></td><td>{analysis.short_call.delta:.3f}</td></tr>
                </table>
            </div>
            
            <div style="background-color: #f0fff0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>💰 Position Analysis</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td><strong>Net Debit (Cost):</strong></td><td>${analysis.net_debit:.2f}</td></tr>"""
        
        if analysis.risk_metrics:
            if analysis.risk_metrics.max_profit:
                html += f'<tr><td><strong>Maximum Profit:</strong></td><td>${analysis.risk_metrics.max_profit:.2f}{profit_pct}</td></tr>'
            if analysis.risk_metrics.max_loss:
                html += f'<tr><td><strong>Maximum Loss:</strong></td><td>${analysis.risk_metrics.max_loss:.2f}</td></tr>'
            if analysis.risk_metrics.breakeven:
                html += f'<tr><td><strong>Breakeven Price:</strong></td><td>${analysis.risk_metrics.breakeven:.2f}</td></tr>'
            if candidate.risk_reward_ratio:
                html += f'<tr><td><strong>Risk/Reward Ratio:</strong></td><td>1:{candidate.risk_reward_ratio:.2f}</td></tr>'
        
        html += f"""
                </table>
            </div>
            
            <div style="background-color: #fafafa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📋 Additional Metrics</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td><strong>Liquidity Score:</strong></td><td>{candidate.liquidity_score:.0f}/100</td></tr>
                    <tr><td><strong>Total Score:</strong></td><td>{candidate.total_score:.0f}/100</td></tr>
                    <tr><td><strong>Strike Width:</strong></td><td>${analysis.strike_width:.2f}</td></tr>
                </table>
            </div>
            
            <div style="background-color: #fffacd; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>⚠️ Important Considerations</h3>
                <ul>
                    <li>Verify option liquidity before placing orders</li>
                    <li>Monitor for early assignment risk on short calls</li>
                    <li>Consider dividend dates and ex-dividend impacts</li>
                    <li>Set profit targets and exit strategies before entering</li>
                    <li>This is not financial advice - conduct your own analysis</li>
                </ul>
            </div>
            
            <hr>
            <p style="font-size: 12px; color: #666;">
                Generated by PMCC Scanner on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
                This analysis is for educational purposes only and should not be considered financial advice.
            </p>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def _generate_text_content(candidate: PMCCCandidate) -> str:
        """Generate plain text content for a single opportunity."""
        symbol = candidate.symbol
        underlying_price = candidate.underlying_price
        analysis = candidate.analysis
        
        lines = [
            f"PMCC Opportunity Alert: {symbol}",
            "=" * 40,
            "",
            f"Current Market Data:",
            f"Underlying Price: ${underlying_price:.2f}",
            f"Analysis Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            "",
            f"Long LEAPS Position:",
            f"Option Symbol: {analysis.long_call.option_symbol}",
            f"Strike Price: ${analysis.long_call.strike:.2f}",
            f"Expiration: {analysis.long_call.expiration.strftime('%B %d, %Y')}",
            f"Days to Expiration: {analysis.long_call.dte} days",
            f"Bid/Ask: ${analysis.long_call.bid:.2f} / ${analysis.long_call.ask:.2f}",
            f"Delta: {analysis.long_call.delta:.3f}",
            "",
            f"Short Call Position:",
            f"Option Symbol: {analysis.short_call.option_symbol}",
            f"Strike Price: ${analysis.short_call.strike:.2f}",
            f"Expiration: {analysis.short_call.expiration.strftime('%B %d, %Y')}",
            f"Days to Expiration: {analysis.short_call.dte} days",
            f"Bid/Ask: ${analysis.short_call.bid:.2f} / ${analysis.short_call.ask:.2f}",
            f"Delta: {analysis.short_call.delta:.3f}",
            "",
            f"Position Analysis:",
            f"Net Debit (Cost): ${analysis.net_debit:.2f}",
        ]
        
        if analysis.risk_metrics:
            if analysis.risk_metrics.max_profit:
                profit_pct = (analysis.risk_metrics.max_profit / analysis.net_debit * 100)
                lines.append(f"Maximum Profit: ${analysis.risk_metrics.max_profit:.2f} ({profit_pct:.1f}%)")
            if analysis.risk_metrics.max_loss:
                lines.append(f"Maximum Loss: ${analysis.risk_metrics.max_loss:.2f}")
            if analysis.risk_metrics.breakeven:
                lines.append(f"Breakeven Price: ${analysis.risk_metrics.breakeven:.2f}")
            if candidate.risk_reward_ratio:
                lines.append(f"Risk/Reward Ratio: 1:{candidate.risk_reward_ratio:.2f}")
        
        lines.extend([
            "",
            f"Additional Metrics:",
            f"Liquidity Score: {candidate.liquidity_score:.0f}/100",
            f"Total Score: {candidate.total_score:.0f}/100",
            f"Strike Width: ${analysis.strike_width:.2f}",
            "",
            "Important Considerations:",
            "- Verify option liquidity before placing orders",
            "- Monitor for early assignment risk on short calls",
            "- Consider dividend dates and ex-dividend impacts",
            "- Set profit targets and exit strategies before entering",
            "- This is not financial advice - conduct your own analysis",
            "",
            f"Generated by PMCC Scanner on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            "This analysis is for educational purposes only."
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def _generate_summary_html(candidates: List[PMCCCandidate]) -> str:
        """Generate HTML summary for multiple opportunities."""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <h2 style="color: #2E8B57;">PMCC Daily Scan Results</h2>
            <p>Scan completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><strong>Total Opportunities Found: {len(candidates)}</strong></p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <thead>
                    <tr style="background-color: #f0f8ff;">
                        <th style="border: 1px solid #ddd; padding: 8px;">Rank</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Symbol</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Price</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Net Cost</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Max Profit</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Return %</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Score</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, candidate in enumerate(candidates, 1):
            profit_pct = ""
            if (candidate.analysis.risk_metrics and 
                candidate.analysis.risk_metrics.max_profit and 
                candidate.analysis.net_debit > 0):
                profit_pct = f"{(candidate.analysis.risk_metrics.max_profit / candidate.analysis.net_debit * 100):.1f}%"
            
            max_profit = candidate.analysis.risk_metrics.max_profit if candidate.analysis.risk_metrics else None
            
            html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{i}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{candidate.symbol}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${candidate.underlying_price:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${candidate.analysis.net_debit:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">${max_profit:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; color: green;">{profit_pct}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{candidate.total_score:.0f}/100</td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
            
            <p style="font-size: 12px; color: #666;">
                This analysis is for educational purposes only and should not be considered financial advice.<br>
                Always verify option liquidity and conduct your own due diligence before trading.
            </p>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def _generate_summary_text(candidates: List[PMCCCandidate]) -> str:
        """Generate plain text summary for multiple opportunities."""
        lines = [
            "PMCC Daily Scan Results",
            "=" * 40,
            f"Scan completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            f"Total Opportunities Found: {len(candidates)}",
            "",
            "Top Opportunities:"
        ]
        
        for i, candidate in enumerate(candidates, 1):
            profit_pct = ""
            if (candidate.analysis.risk_metrics and 
                candidate.analysis.risk_metrics.max_profit and 
                candidate.analysis.net_debit > 0):
                profit_pct = f" ({(candidate.analysis.risk_metrics.max_profit / candidate.analysis.net_debit * 100):.1f}%)"
            
            max_profit = candidate.analysis.risk_metrics.max_profit if candidate.analysis.risk_metrics else None
            
            lines.extend([
                f"{i}. {candidate.symbol} - ${candidate.underlying_price:.2f}",
                f"   Net Cost: ${candidate.analysis.net_debit:.2f}",
                f"   Max Profit: ${max_profit:.2f}{profit_pct}" if max_profit else "   Max Profit: N/A",
                f"   Score: {candidate.total_score:.0f}/100" if candidate.total_score else "   Score: N/A",
                ""
            ])
        
        lines.extend([
            "This analysis is for educational purposes only.",
            "Always verify option liquidity and conduct your own due diligence."
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def _generate_daily_summary_html(
        candidates: List[PMCCCandidate], 
        scan_metadata: Optional[dict],
        scan_date: str,
        scan_time: str
    ) -> str:
        """Generate comprehensive HTML email for daily summary with detailed options information."""
        
        # Extract metadata
        scan_duration = scan_metadata.get('duration_seconds', 0) if scan_metadata else 0
        stocks_screened = scan_metadata.get('stocks_screened', 0) if scan_metadata else 0
        
        # Format duration
        if scan_duration > 60:
            duration_str = f"{scan_duration // 60:.0f}m {scan_duration % 60:.0f}s"
        else:
            duration_str = f"{scan_duration:.1f}s"
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PMCC Daily Summary - {scan_date}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            color: #333;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        
        .header .subtitle {{
            margin: 8px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .metadata {{
            background-color: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 0;
        }}
        
        .metadata-item {{
            background-color: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #2E8B57;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .metadata-label {{
            font-size: 12px;
            font-weight: 600;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        
        .metadata-value {{
            font-size: 18px;
            font-weight: 700;
            color: #2E8B57;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .opportunity-card {{
            background-color: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .opportunity-header {{
            background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .opportunity-title {{
            font-size: 20px;
            font-weight: 700;
            margin: 0;
        }}
        
        .opportunity-rank {{
            background-color: rgba(255,255,255,0.2);
            padding: 8px 12px;
            border-radius: 20px;
            font-weight: 600;
        }}
        
        .opportunity-content {{
            padding: 25px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .metric-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            border-left: 4px solid #2E8B57;
        }}
        
        .metric-label {{
            font-size: 12px;
            font-weight: 600;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .metric-value {{
            font-size: 16px;
            font-weight: 700;
            color: #2E8B57;
        }}
        
        .options-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin: 25px 0;
        }}
        
        .option-details {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
        }}
        
        .leaps-option {{
            border-left: 4px solid #28a745;
        }}
        
        .short-option {{
            border-left: 4px solid #dc3545;
        }}
        
        .option-header {{
            font-size: 16px;
            font-weight: 700;
            margin: 0 0 15px 0;
            color: #333;
        }}
        
        .leaps-option .option-header {{
            color: #28a745;
        }}
        
        .short-option .option-header {{
            color: #dc3545;
        }}
        
        .option-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .option-table td {{
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .option-table td:first-child {{
            font-weight: 600;
            color: #6c757d;
            width: 50%;
        }}
        
        .option-table td:last-child {{
            font-family: 'Courier New', monospace;
            text-align: right;
        }}
        
        .greeks-section {{
            background-color: #fff3cd;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
        }}
        
        .greeks-title {{
            font-size: 14px;
            font-weight: 700;
            color: #856404;
            margin: 0 0 10px 0;
        }}
        
        .greeks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
        }}
        
        .greek-item {{
            text-align: center;
        }}
        
        .greek-label {{
            font-size: 11px;
            color: #856404;
            text-transform: uppercase;
            margin-bottom: 2px;
        }}
        
        .greek-value {{
            font-size: 13px;
            font-weight: 600;
            color: #856404;
            font-family: 'Courier New', monospace;
        }}
        
        .no-opportunities {{
            text-align: center;
            padding: 60px 30px;
            color: #6c757d;
        }}
        
        .no-opportunities h3 {{
            margin: 0 0 10px 0;
            color: #495057;
        }}
        
        .footer {{
            background-color: #f8f9fa;
            padding: 20px 30px;
            border-top: 1px solid #e9ecef;
            font-size: 12px;
            color: #6c757d;
            line-height: 1.5;
        }}
        
        .disclaimer {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
        }}
        
        .disclaimer h4 {{
            margin: 0 0 8px 0;
            color: #856404;
            font-size: 14px;
        }}
        
        .disclaimer p {{
            margin: 0;
            font-size: 12px;
            color: #856404;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 0;
                border-radius: 0;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 24px;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            .metadata-grid {{
                grid-template-columns: 1fr;
            }}
            
            .options-section {{
                grid-template-columns: 1fr;
            }}
            
            .metrics-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .opportunity-header {{
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PMCC Daily Summary</h1>
            <div class="subtitle">{scan_date} • Scan completed at {scan_time}</div>
        </div>
        
        <div class="metadata">
            <div class="metadata-grid">
                <div class="metadata-item">
                    <div class="metadata-label">Scan Duration</div>
                    <div class="metadata-value">{duration_str}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Stocks Screened</div>
                    <div class="metadata-value">{stocks_screened:,}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Opportunities Found</div>
                    <div class="metadata-value">{len(candidates)}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Success Rate</div>
                    <div class="metadata-value">{(len(candidates) / max(stocks_screened, 1) * 100):.2f}%</div>
                </div>
            </div>
        </div>
        
        <div class="content">"""
        
        if not candidates:
            html += """
            <div class="no-opportunities">
                <h3>No PMCC Opportunities Found</h3>
                <p>The market scan completed successfully, but no profitable Poor Man's Covered Call opportunities met our criteria today.</p>
                <p>This is normal during periods of low volatility or when option premiums are insufficient for profitable PMCC setups.</p>
            </div>"""
        else:
            html += f"""
            <h2 style="margin: 0 0 20px 0; color: #2E8B57;">Today's Top PMCC Opportunities ({len(candidates)} stocks)</h2>
            <p style="margin: 0 0 20px 0; color: #6c757d;">
                Best Poor Man's Covered Call opportunity for each stock, sorted by total score. 
                Each entry shows the highest-scoring PMCC combination found for that symbol.
            </p>"""
            
            for i, candidate in enumerate(candidates, 1):
                # Calculate key metrics
                profit_pct = ""
                if (candidate.analysis.risk_metrics and 
                    candidate.analysis.risk_metrics.max_profit and 
                    candidate.analysis.net_debit > 0):
                    pct_value = (candidate.analysis.risk_metrics.max_profit / candidate.analysis.net_debit * 100)
                    profit_pct = f"{pct_value:.1f}%"
                
                max_profit = candidate.analysis.risk_metrics.max_profit if candidate.analysis.risk_metrics else 0
                max_loss = candidate.analysis.risk_metrics.max_loss if candidate.analysis.risk_metrics else 0
                breakeven = candidate.analysis.risk_metrics.breakeven if candidate.analysis.risk_metrics else 0
                score_value = candidate.total_score or 0
                
                html += f"""
            <div class="opportunity-card">
                <div class="opportunity-header">
                    <h3 class="opportunity-title">{candidate.symbol} - ${candidate.underlying_price:.2f}</h3>
                    <div class="opportunity-rank">#{i} • Score: {score_value:.0f}/100</div>
                </div>
                
                <div class="opportunity-content">
                    <!-- Key Strategy Metrics -->
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">Net Cost</div>
                            <div class="metric-value">${candidate.analysis.net_debit:.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Max Profit</div>
                            <div class="metric-value">${max_profit:.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Return %</div>
                            <div class="metric-value" style="color: #28a745;">{profit_pct}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Max Loss</div>
                            <div class="metric-value" style="color: #dc3545;">${max_loss:.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Breakeven</div>
                            <div class="metric-value">${breakeven:.2f}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Risk/Reward</div>
                            <div class="metric-value">1:{candidate.risk_reward_ratio:.2f}</div>
                        </div>
                    </div>
                    
                    <!-- Detailed Options Information -->
                    <div class="options-section">
                        <div class="option-details leaps-option">
                            <h4 class="option-header">📈 Long LEAPS Call</h4>
                            <table class="option-table">
                                <tr><td>Option Symbol:</td><td>{candidate.analysis.long_call.option_symbol}</td></tr>
                                <tr><td>Strike Price:</td><td>${candidate.analysis.long_call.strike:.2f}</td></tr>
                                <tr><td>Expiration:</td><td>{candidate.analysis.long_call.expiration.strftime('%b %d, %Y')}</td></tr>
                                <tr><td>Days to Expiration:</td><td>{candidate.analysis.long_call.dte} days</td></tr>
                                <tr><td>Premium (Bid/Ask):</td><td>${candidate.analysis.long_call.bid:.2f} / ${candidate.analysis.long_call.ask:.2f}</td></tr>
                                <tr><td>Mid Price:</td><td>${candidate.analysis.long_call.mid:.2f}</td></tr>"""
                
                # Add volume and open interest if available
                if candidate.analysis.long_call.volume:
                    html += f'<tr><td>Volume:</td><td>{candidate.analysis.long_call.volume:,}</td></tr>'
                if candidate.analysis.long_call.open_interest:
                    html += f'<tr><td>Open Interest:</td><td>{candidate.analysis.long_call.open_interest:,}</td></tr>'
                
                html += """
                            </table>
                        </div>
                        
                        <div class="option-details short-option">
                            <h4 class="option-header">📉 Short Call</h4>
                            <table class="option-table">"""
                
                html += f"""
                                <tr><td>Option Symbol:</td><td>{candidate.analysis.short_call.option_symbol}</td></tr>
                                <tr><td>Strike Price:</td><td>${candidate.analysis.short_call.strike:.2f}</td></tr>
                                <tr><td>Expiration:</td><td>{candidate.analysis.short_call.expiration.strftime('%b %d, %Y')}</td></tr>
                                <tr><td>Days to Expiration:</td><td>{candidate.analysis.short_call.dte} days</td></tr>
                                <tr><td>Premium (Bid/Ask):</td><td>${candidate.analysis.short_call.bid:.2f} / ${candidate.analysis.short_call.ask:.2f}</td></tr>
                                <tr><td>Mid Price:</td><td>${candidate.analysis.short_call.mid:.2f}</td></tr>"""
                
                # Add volume and open interest if available
                if candidate.analysis.short_call.volume:
                    html += f'<tr><td>Volume:</td><td>{candidate.analysis.short_call.volume:,}</td></tr>'
                if candidate.analysis.short_call.open_interest:
                    html += f'<tr><td>Open Interest:</td><td>{candidate.analysis.short_call.open_interest:,}</td></tr>'
                
                html += """
                            </table>
                        </div>
                    </div>
                    
                    <!-- Greeks Information -->"""
                
                # Add Greeks section if available
                if (candidate.analysis.long_call.delta is not None or 
                    candidate.analysis.short_call.delta is not None):
                    html += """
                    <div class="greeks-section">
                        <h4 class="greeks-title">Option Greeks</h4>
                        <div class="greeks-grid">"""
                    
                    # LEAPS Greeks
                    if candidate.analysis.long_call.delta is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">LEAPS Delta</div>
                                <div class="greek-value">{candidate.analysis.long_call.delta:.3f}</div>
                            </div>"""
                    
                    if candidate.analysis.long_call.gamma is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">LEAPS Gamma</div>
                                <div class="greek-value">{candidate.analysis.long_call.gamma:.3f}</div>
                            </div>"""
                    
                    if candidate.analysis.long_call.theta is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">LEAPS Theta</div>
                                <div class="greek-value">{candidate.analysis.long_call.theta:.3f}</div>
                            </div>"""
                    
                    if candidate.analysis.long_call.vega is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">LEAPS Vega</div>
                                <div class="greek-value">{candidate.analysis.long_call.vega:.3f}</div>
                            </div>"""
                    
                    # Short Call Greeks
                    if candidate.analysis.short_call.delta is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">Short Delta</div>
                                <div class="greek-value">{candidate.analysis.short_call.delta:.3f}</div>
                            </div>"""
                    
                    if candidate.analysis.short_call.gamma is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">Short Gamma</div>
                                <div class="greek-value">{candidate.analysis.short_call.gamma:.3f}</div>
                            </div>"""
                    
                    if candidate.analysis.short_call.theta is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">Short Theta</div>
                                <div class="greek-value">{candidate.analysis.short_call.theta:.3f}</div>
                            </div>"""
                    
                    if candidate.analysis.short_call.vega is not None:
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">Short Vega</div>
                                <div class="greek-value">{candidate.analysis.short_call.vega:.3f}</div>
                            </div>"""
                    
                    # Net Greeks if available
                    if (candidate.analysis.risk_metrics and 
                        candidate.analysis.risk_metrics.net_delta is not None):
                        html += f"""
                            <div class="greek-item">
                                <div class="greek-label">Net Delta</div>
                                <div class="greek-value" style="font-weight: 700;">{candidate.analysis.risk_metrics.net_delta:.3f}</div>
                            </div>"""
                    
                    html += """
                        </div>
                    </div>"""
                
                html += """
                </div>
            </div>"""
        
        html += f"""
            <div class="disclaimer">
                <h4>⚠️ Important Disclaimer</h4>
                <p>
                    This analysis is for educational purposes only and does not constitute financial advice. 
                    Always verify option liquidity, conduct your own due diligence, and consider your risk tolerance 
                    before entering any options positions. Past performance does not guarantee future results.
                    Monitor for early assignment risk and dividend dates before entering PMCC positions.
                </p>
            </div>
        </div>
        
        <div class="footer">
            <strong>PMCC Scanner</strong><br>
            Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p %Z')}<br>
            <br>
            Poor Man's Covered Call (PMCC) Strategy Analysis System<br>
            This system identifies potential diagonal spread opportunities using deep ITM LEAPS and short-term OTM calls.<br>
            For support or questions, review the application documentation or contact your system administrator.
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    @staticmethod
    def _generate_daily_summary_text(
        candidates: List[PMCCCandidate], 
        scan_metadata: Optional[dict],
        scan_date: str,
        scan_time: str
    ) -> str:
        """Generate comprehensive plain text version of daily summary with detailed options information."""
        
        # Extract metadata
        scan_duration = scan_metadata.get('duration_seconds', 0) if scan_metadata else 0
        stocks_screened = scan_metadata.get('stocks_screened', 0) if scan_metadata else 0
        
        # Format duration
        if scan_duration > 60:
            duration_str = f"{scan_duration // 60:.0f}m {scan_duration % 60:.0f}s"
        else:
            duration_str = f"{scan_duration:.1f}s"
        
        lines = [
            "PMCC DAILY SUMMARY",
            "=" * 80,
            f"Date: {scan_date}",
            f"Scan completed at: {scan_time}",
            "",
            "SCAN METADATA",
            "-" * 40,
            f"Duration: {duration_str}",
            f"Stocks Screened: {stocks_screened:,}",
            f"Opportunities Found: {len(candidates)}",
            f"Success Rate: {(len(candidates) / max(stocks_screened, 1) * 100):.2f}%",
            ""
        ]
        
        if not candidates:
            lines.extend([
                "NO OPPORTUNITIES FOUND",
                "-" * 30,
                "The market scan completed successfully, but no profitable",
                "Poor Man's Covered Call opportunities met our criteria today.",
                "",
                "This is normal during periods of low volatility or when",
                "option premiums are insufficient for profitable PMCC setups.",
                ""
            ])
        else:
            lines.extend([
                f"TODAY'S PMCC OPPORTUNITIES ({len(candidates)} found)",
                "=" * 80,
                "Detailed analysis of profitable Poor Man's Covered Call opportunities,",
                "sorted by total score. Each opportunity includes comprehensive LEAPS",
                "and short call option details.",
                ""
            ])
            
            for i, candidate in enumerate(candidates, 1):
                # Calculate key metrics
                profit_pct = "N/A"
                if (candidate.analysis.risk_metrics and 
                    candidate.analysis.risk_metrics.max_profit and 
                    candidate.analysis.net_debit > 0):
                    pct_value = (candidate.analysis.risk_metrics.max_profit / candidate.analysis.net_debit * 100)
                    profit_pct = f"{pct_value:.1f}%"
                
                max_profit = candidate.analysis.risk_metrics.max_profit if candidate.analysis.risk_metrics else 0
                max_loss = candidate.analysis.risk_metrics.max_loss if candidate.analysis.risk_metrics else 0
                breakeven = candidate.analysis.risk_metrics.breakeven if candidate.analysis.risk_metrics else 0
                score_value = candidate.total_score or 0
                risk_reward = candidate.risk_reward_ratio or 0
                
                lines.extend([
                    f"#{i}: {candidate.symbol} - ${candidate.underlying_price:.2f} (Score: {score_value:.0f}/100)",
                    "-" * 80,
                    "",
                    "STRATEGY METRICS:",
                    f"  Net Cost (Debit):     ${candidate.analysis.net_debit:.2f}",
                    f"  Maximum Profit:       ${max_profit:.2f} ({profit_pct})",
                    f"  Maximum Loss:         ${max_loss:.2f}",
                    f"  Breakeven Price:      ${breakeven:.2f}",
                    f"  Risk/Reward Ratio:    1:{risk_reward:.2f}",
                    f"  Liquidity Score:      {candidate.liquidity_score:.0f}/100",
                    "",
                    "LONG LEAPS CALL (Buy):",
                    f"  Option Symbol:        {candidate.analysis.long_call.option_symbol}",
                    f"  Strike Price:         ${candidate.analysis.long_call.strike:.2f}",
                    f"  Expiration:           {candidate.analysis.long_call.expiration.strftime('%b %d, %Y')}",
                    f"  Days to Expiration:   {candidate.analysis.long_call.dte} days",
                    f"  Premium (Bid/Ask):    ${candidate.analysis.long_call.bid:.2f} / ${candidate.analysis.long_call.ask:.2f}",
                    f"  Mid Price:            ${candidate.analysis.long_call.mid:.2f}",
                ])
                
                # Add volume and open interest if available
                if candidate.analysis.long_call.volume:
                    lines.append(f"  Volume:               {candidate.analysis.long_call.volume:,}")
                if candidate.analysis.long_call.open_interest:
                    lines.append(f"  Open Interest:        {candidate.analysis.long_call.open_interest:,}")
                
                # Add LEAPS Greeks if available
                if candidate.analysis.long_call.delta is not None:
                    lines.append(f"  Delta:                {candidate.analysis.long_call.delta:.3f}")
                if candidate.analysis.long_call.gamma is not None:
                    lines.append(f"  Gamma:                {candidate.analysis.long_call.gamma:.3f}")
                if candidate.analysis.long_call.theta is not None:
                    lines.append(f"  Theta:                {candidate.analysis.long_call.theta:.3f}")
                if candidate.analysis.long_call.vega is not None:
                    lines.append(f"  Vega:                 {candidate.analysis.long_call.vega:.3f}")
                
                lines.extend([
                    "",
                    "SHORT CALL (Sell):",
                    f"  Option Symbol:        {candidate.analysis.short_call.option_symbol}",
                    f"  Strike Price:         ${candidate.analysis.short_call.strike:.2f}",
                    f"  Expiration:           {candidate.analysis.short_call.expiration.strftime('%b %d, %Y')}",
                    f"  Days to Expiration:   {candidate.analysis.short_call.dte} days",
                    f"  Premium (Bid/Ask):    ${candidate.analysis.short_call.bid:.2f} / ${candidate.analysis.short_call.ask:.2f}",
                    f"  Mid Price:            ${candidate.analysis.short_call.mid:.2f}",
                ])
                
                # Add volume and open interest if available
                if candidate.analysis.short_call.volume:
                    lines.append(f"  Volume:               {candidate.analysis.short_call.volume:,}")
                if candidate.analysis.short_call.open_interest:
                    lines.append(f"  Open Interest:        {candidate.analysis.short_call.open_interest:,}")
                
                # Add Short Call Greeks if available
                if candidate.analysis.short_call.delta is not None:
                    lines.append(f"  Delta:                {candidate.analysis.short_call.delta:.3f}")
                if candidate.analysis.short_call.gamma is not None:
                    lines.append(f"  Gamma:                {candidate.analysis.short_call.gamma:.3f}")
                if candidate.analysis.short_call.theta is not None:
                    lines.append(f"  Theta:                {candidate.analysis.short_call.theta:.3f}")
                if candidate.analysis.short_call.vega is not None:
                    lines.append(f"  Vega:                 {candidate.analysis.short_call.vega:.3f}")
                
                # Add Net Greeks if available
                if (candidate.analysis.risk_metrics and 
                    candidate.analysis.risk_metrics.net_delta is not None):
                    lines.extend([
                        "",
                        "NET POSITION GREEKS:",
                        f"  Net Delta:            {candidate.analysis.risk_metrics.net_delta:.3f}",
                    ])
                    
                    if candidate.analysis.risk_metrics.net_gamma is not None:
                        lines.append(f"  Net Gamma:            {candidate.analysis.risk_metrics.net_gamma:.3f}")
                    if candidate.analysis.risk_metrics.net_theta is not None:
                        lines.append(f"  Net Theta:            {candidate.analysis.risk_metrics.net_theta:.3f}")
                    if candidate.analysis.risk_metrics.net_vega is not None:
                        lines.append(f"  Net Vega:             {candidate.analysis.risk_metrics.net_vega:.3f}")
                
                lines.extend([
                    "",
                    "IMPORTANT CONSIDERATIONS:",
                    "- Verify option liquidity before placing orders",
                    "- Monitor for early assignment risk on short calls",  
                    "- Consider dividend dates and ex-dividend impacts",
                    "- Set profit targets and exit strategies before entering",
                    "",
                    ""
                ])
            
            lines.extend([
                "LEGEND:",
                "- Opportunities are sorted by total score (highest first)",
                "- Scores above 80 indicate premium setups with excellent metrics",
                "- Scores above 70 meet minimum profitability criteria",
                "- Net Greeks show the combined exposure of the PMCC position",
                "- Higher volume and open interest indicate better liquidity",
                ""
            ])
        
        lines.extend([
            "IMPORTANT DISCLAIMER",
            "-" * 40,
            "This analysis is for educational purposes only and does not",
            "constitute financial advice. Always verify option liquidity,",
            "conduct your own due diligence, and consider your risk tolerance",
            "before entering any options positions. Past performance does not",
            "guarantee future results. Monitor for early assignment risk and",
            "dividend dates before entering PMCC positions.",
            "",
            f"Generated by PMCC Scanner on {datetime.now().strftime('%B %d, %Y at %I:%M %p %Z')}",
            "Poor Man's Covered Call (PMCC) Strategy Analysis System",
            "",
            "This system identifies potential diagonal spread opportunities using",
            "deep ITM LEAPS and short-term OTM calls. For support or questions,",
            "review the application documentation or contact your system administrator."
        ])
        
        return "\n".join(lines)