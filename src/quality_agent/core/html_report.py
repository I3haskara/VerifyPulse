"""
HTML report generation module.
Renders a clean, professional failure analysis report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def generate_html_report(
    run_id: str,
    diagnosis: Dict[str, Any],
    raw_log: Dict[str, Any] | None = None,
) -> str:
    """
    Generate a comprehensive HTML report from the diagnosis.
    
    Args:
        run_id: Unique run identifier
        diagnosis: LLM diagnosis with category, summary, steps, fix
        raw_log: Optional raw failure log for debugging section
        
    Returns:
        Path to the generated HTML report
    """
    category = diagnosis.get("FailureCategory", "Unknown")
    summary = diagnosis.get("RootCauseSummary", "No summary available.")
    steps = diagnosis.get("ReproductionSteps", [])
    suggested_fix = diagnosis.get("SuggestedFix", "No fix suggested.")

    # Extract metadata from raw_log if available
    commit_hash = raw_log.get("commit_hash", "unknown") if raw_log else "unknown"
    test_name = raw_log.get("test_name", "unknown") if raw_log else "unknown"
    timestamp = raw_log.get("timestamp", "") if raw_log else ""
    success = raw_log.get("success", False) if raw_log else False

    html_steps = "".join(f"<li><code>{step}</code></li>" for step in steps)
    
    # Different styling for success vs failure
    if success:
        badge_class = "badge-success"
        card_border = "border-success"
    else:
        badge_class = "badge-failure"
        card_border = "border-failure"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>VerifyPulse – Autonomous Diagnostic Report</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 2rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #1d1d1f;
      min-height: 100vh;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.15);
      padding: 2rem 2.5rem;
      margin-bottom: 1.5rem;
    }}
    .card.{card_border} {{
      border-left: 4px solid {"#10b981" if success else "#ef4444"};
    }}
    h1, h2, h3 {{
      margin-top: 0;
    }}
    h1 {{
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 1rem;
    }}
    h2 {{
      font-size: 1.5rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: #4b5563;
    }}
    code {{
      background: #f1f3f5;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-family: "JetBrains Mono", "Fira Code", "Courier New", monospace;
      font-size: 0.9em;
    }}
    pre {{
      background: #1e293b;
      color: #e2e8f0;
      padding: 1.25rem;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 0.9rem;
      line-height: 1.6;
    }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .badge-success {{
      background: #d1fae5;
      color: #065f46;
    }}
    .badge-failure {{
      background: #fee2e2;
      color: #991b1b;
    }}
    .meta {{
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
      margin-top: 1rem;
      font-size: 0.9rem;
      color: #6b7280;
    }}
    .meta-item {{
      display: flex;
      flex-direction: column;
    }}
    .meta-label {{
      font-weight: 600;
      color: #374151;
      margin-bottom: 0.25rem;
    }}
    ol {{
      padding-left: 1.5rem;
    }}
    ol li {{
      margin-bottom: 0.75rem;
    }}
    .summary-text {{
      font-size: 1.05rem;
      line-height: 1.7;
      color: #374151;
    }}
    .footer {{
      text-align: center;
      color: #ffffff;
      margin-top: 3rem;
      font-size: 0.9rem;
      opacity: 0.9;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card {card_border}">
      <h1>🔍 VerifyPulse – Autonomous Diagnostic Report</h1>
      <p>
        <span class="badge {badge_class}">{category}</span>
      </p>
      <div class="meta">
        <div class="meta-item">
          <div class="meta-label">Run ID</div>
          <code>{run_id}</code>
        </div>
        <div class="meta-item">
          <div class="meta-label">Commit</div>
          <code>{commit_hash}</code>
        </div>
        <div class="meta-item">
          <div class="meta-label">Test</div>
          <code>{test_name}</code>
        </div>
        <div class="meta-item">
          <div class="meta-label">Timestamp</div>
          <span>{timestamp}</span>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>📋 Root Cause Summary</h2>
      <p class="summary-text">{summary}</p>
    </div>

    {"" if not steps else f'''<div class="card">
      <h2>🔄 Reproduction Steps</h2>
      <ol>
        {html_steps}
      </ol>
    </div>'''}

    {"" if not suggested_fix or suggested_fix == "No fixes needed." else f'''<div class="card">
      <h2>🛠️ Suggested Fix</h2>
      <pre>{suggested_fix}</pre>
    </div>'''}

    {"" if not raw_log else f'''<div class="card">
      <h3>🐛 Raw Failure Log (for debugging)</h3>
      <pre>{json.dumps(raw_log, indent=2)}</pre>
    </div>'''}

    <div class="footer">
      <p>Generated by VerifyPulse Agentic AI Quality Coach</p>
      <p>Autonomous · RAG-Enhanced · LLM-Powered</p>
    </div>
  </div>
</body>
</html>
"""
    
    # Save report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    report_path = reports_dir / f"{run_id}_diagnostic_report.html"
    report_path.write_text(html, encoding="utf-8")
    
    print(f"[HTML] Report generated: {report_path}")
    
    return str(report_path.absolute())
