"""HTML formatter for human-readable security reports."""

from typing import Dict, Any
from datetime import datetime
from ...domain.models.security import SecurityReview, SecurityFinding, Severity
from .base_formatter import OutputFormatter


class HTMLFormatter(OutputFormatter):
    """
    Format security review results as HTML.
    
    Provides a rich, interactive HTML report with:
    - Executive summary with statistics
    - Severity-based filtering
    - Code snippets with syntax highlighting
    - Detailed finding information
    """

    def format_review(self, review: SecurityReview) -> str:
        """
        Format complete security review as HTML.

        Args:
            review: SecurityReview to format

        Returns:
            HTML string
        """
        stats = self._calculate_statistics(review)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FalconEYE Security Report - {review.codebase_path}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .logo {{
            font-size: 1.2em;
        }}
        
        header .meta {{
            opacity: 0.9;
            font-size: 0.95em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        
        .stat-card.critical {{
            border-left-color: #dc2626;
        }}
        
        .stat-card.high {{
            border-left-color: #ea580c;
        }}
        
        .stat-card.medium {{
            border-left-color: #f59e0b;
        }}
        
        .stat-card.low {{
            border-left-color: #3b82f6;
        }}
        
        .stat-card .label {{
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}
        
        .filters {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .filters h3 {{
            margin-bottom: 15px;
            color: #333;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #e5e7eb;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9em;
            font-weight: 500;
        }}
        
        .filter-btn:hover {{
            border-color: #667eea;
            color: #667eea;
        }}
        
        .filter-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .findings {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .finding {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }}
        
        .finding.critical {{
            border-left-color: #dc2626;
        }}
        
        .finding.high {{
            border-left-color: #ea580c;
        }}
        
        .finding.medium {{
            border-left-color: #f59e0b;
        }}
        
        .finding.low {{
            border-left-color: #3b82f6;
        }}
        
        .finding.info {{
            border-left-color: #6b7280;
        }}
        
        .finding-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .finding-title {{
            font-size: 1.4em;
            font-weight: 600;
            color: #1f2937;
            flex: 1;
        }}
        
        .badges {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        
        .badge {{
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .badge.critical {{
            background: #fee2e2;
            color: #dc2626;
        }}
        
        .badge.high {{
            background: #ffedd5;
            color: #ea580c;
        }}
        
        .badge.medium {{
            background: #fef3c7;
            color: #d97706;
        }}
        
        .badge.low {{
            background: #dbeafe;
            color: #2563eb;
        }}
        
        .badge.info {{
            background: #f3f4f6;
            color: #6b7280;
        }}
        
        .badge.confidence {{
            background: #f0fdf4;
            color: #16a34a;
        }}
        
        .finding-location {{
            color: #6b7280;
            font-size: 0.9em;
            margin-bottom: 15px;
            font-family: 'Monaco', 'Courier New', monospace;
        }}
        
        .finding-section {{
            margin-bottom: 20px;
        }}
        
        .finding-section h4 {{
            color: #4b5563;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .finding-section p {{
            color: #374151;
            line-height: 1.7;
        }}
        
        .code-snippet {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            margin-top: 10px;
        }}
        
        .code-snippet pre {{
            margin: 0;
            white-space: pre;
        }}
        
        .code-line {{
            display: block;
        }}
        
        .code-line.highlight {{
            background: rgba(251, 191, 36, 0.1);
            border-left: 3px solid #fbbf24;
            padding-left: 5px;
            margin-left: -8px;
        }}
        
        .mitigation {{
            background: #f0fdf4;
            border-left: 4px solid #16a34a;
            padding: 15px;
            border-radius: 6px;
            color: #166534;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 40px;
        }}
        
        .no-findings {{
            background: white;
            padding: 60px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .no-findings h2 {{
            color: #16a34a;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .no-findings p {{
            color: #6b7280;
            font-size: 1.1em;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .filters {{
                display: none;
            }}
            
            .finding {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><span class="logo">🦅</span> FalconEYE Security Report</h1>
            <div class="meta">
                <div><strong>Project:</strong> {review.codebase_path}</div>
                <div><strong>Language:</strong> {review.language}</div>
                <div><strong>Scan Date:</strong> {review.started_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
                <div><strong>Files Analyzed:</strong> {review.files_analyzed}</div>
                <div><strong>Duration:</strong> {self._format_duration(review)}</div>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Findings</div>
                <div class="value">{stats['total']}</div>
            </div>
            <div class="stat-card critical">
                <div class="label">Critical</div>
                <div class="value">{stats['critical']}</div>
            </div>
            <div class="stat-card high">
                <div class="label">High</div>
                <div class="value">{stats['high']}</div>
            </div>
            <div class="stat-card medium">
                <div class="label">Medium</div>
                <div class="value">{stats['medium']}</div>
            </div>
            <div class="stat-card low">
                <div class="label">Low</div>
                <div class="value">{stats['low']}</div>
            </div>
        </div>
        
        {self._render_filters() if stats['total'] > 0 else ''}
        
        <div class="findings">
            {self._render_findings(review) if stats['total'] > 0 else self._render_no_findings()}
        </div>
        
        <footer>
            <p>Generated by <strong>FalconEYE</strong> - AI-Powered Security Analysis</p>
            <p>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
    
    <script>
        // Filter functionality
        document.addEventListener('DOMContentLoaded', function() {{
            const filterButtons = document.querySelectorAll('.filter-btn');
            const findings = document.querySelectorAll('.finding');
            
            filterButtons.forEach(button => {{
                button.addEventListener('click', function() {{
                    const filter = this.dataset.filter;
                    
                    // Update active state
                    filterButtons.forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Filter findings
                    findings.forEach(finding => {{
                        if (filter === 'all' || finding.classList.contains(filter)) {{
                            finding.style.display = 'block';
                        }} else {{
                            finding.style.display = 'none';
                        }}
                    }});
                }});
            }});
        }});
    </script>
</body>
</html>"""
        
        return html

    def format_finding(self, finding: SecurityFinding) -> str:
        """
        Format single security finding as HTML.

        Args:
            finding: SecurityFinding to format

        Returns:
            HTML string
        """
        return self._render_finding(finding)

    def get_file_extension(self) -> str:
        """Get file extension for HTML format."""
        return ".html"

    def _calculate_statistics(self, review: SecurityReview) -> Dict[str, int]:
        """Calculate statistics from review."""
        return {
            'total': len(review.findings),
            'critical': review.get_critical_count(),
            'high': review.get_high_count(),
            'medium': review.get_medium_count(),
            'low': review.get_low_count(),
        }

    def _format_duration(self, review: SecurityReview) -> str:
        """Format duration in human-readable format."""
        if not review.completed_at:
            return "In progress"
        
        duration = (review.completed_at - review.started_at).total_seconds()
        
        if duration < 60:
            return f"{int(duration)}s"
        elif duration < 3600:
            minutes = int(duration / 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration / 3600)
            minutes = int((duration % 3600) / 60)
            return f"{hours}h {minutes}m"

    def _render_filters(self) -> str:
        """Render filter buttons."""
        return """
        <div class="filters">
            <h3>Filter by Severity</h3>
            <div class="filter-buttons">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="critical">Critical</button>
                <button class="filter-btn" data-filter="high">High</button>
                <button class="filter-btn" data-filter="medium">Medium</button>
                <button class="filter-btn" data-filter="low">Low</button>
                <button class="filter-btn" data-filter="info">Info</button>
            </div>
        </div>
        """

    def _render_findings(self, review: SecurityReview) -> str:
        """Render all findings."""
        # Sort by severity (critical first)
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        sorted_findings = sorted(
            review.findings,
            key=lambda f: severity_order.get(f.severity, 999)
        )
        
        return '\n'.join(self._render_finding(f) for f in sorted_findings)

    def _render_finding(self, finding: SecurityFinding) -> str:
        """Render a single finding."""
        severity = finding.severity.value.lower()
        confidence = finding.confidence.value
        
        # Format location
        location = finding.file_path
        if finding.line_start:
            if finding.line_end and finding.line_end != finding.line_start:
                location += f" (lines {finding.line_start}-{finding.line_end})"
            else:
                location += f" (line {finding.line_start})"
        
        # Format code snippet with line highlighting
        code_html = self._format_code_snippet(finding.code_snippet, finding.line_start, finding.line_end)
        
        return f"""
        <div class="finding {severity}" data-severity="{severity}">
            <div class="finding-header">
                <div class="finding-title">{self._escape_html(finding.issue)}</div>
                <div class="badges">
                    <span class="badge {severity}">{severity}</span>
                    <span class="badge confidence">{confidence}</span>
                </div>
            </div>
            
            <div class="finding-location">📍 {self._escape_html(location)}</div>
            
            <div class="finding-section">
                <h4>Description</h4>
                <p>{self._escape_html(finding.reasoning)}</p>
            </div>
            
            {f'<div class="finding-section"><h4>Code Snippet</h4>{code_html}</div>' if finding.code_snippet else ''}
            
            <div class="finding-section">
                <h4>Recommendation</h4>
                <div class="mitigation">
                    {self._escape_html(finding.mitigation)}
                </div>
            </div>
            
            {f'<div class="finding-section"><h4>CWE ID</h4><p>{finding.cwe_id}</p></div>' if finding.cwe_id else ''}
            {f'<div class="finding-section"><h4>Tags</h4><p>{", ".join(finding.tags)}</p></div>' if finding.tags else ''}
        </div>
        """

    def _format_code_snippet(self, snippet: str, line_start: int = None, line_end: int = None) -> str:
        """Format code snippet with syntax highlighting."""
        if not snippet:
            return ""
        
        lines = snippet.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Check if line should be highlighted (contains > marker)
            is_highlight = '>' in line[:10]  # Check first 10 chars for line number marker
            css_class = ' class="code-line highlight"' if is_highlight else ' class="code-line"'
            formatted_lines.append(f'<span{css_class}>{self._escape_html(line)}</span>')
        
        code_content = '\n'.join(formatted_lines)
        
        return f'<div class="code-snippet"><pre>{code_content}</pre></div>'

    def _render_no_findings(self) -> str:
        """Render message when no findings."""
        return """
        <div class="no-findings">
            <h2>✅ No Security Issues Found</h2>
            <p>The security analysis did not identify any vulnerabilities in the scanned code.</p>
        </div>
        """

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
