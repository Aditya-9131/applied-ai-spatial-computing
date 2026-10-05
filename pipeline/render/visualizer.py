"""Professional 2D Vector SVG & Interactive HTML Floor Plan Visualizer."""

import os
from typing import Dict, List, Any

class FloorPlanVisualizer:
    """Renders polycam/magicplan-grade dimensioned floor plans with damage overlays and scopes."""

    def __init__(self):
        pass

    def render_svg(self, contract: Dict[str, Any], output_svg_path: str) -> str:
        """Generates a high-precision architectural vector SVG floor plan."""
        stitched = contract.get("stitched_plan", {})
        rooms = stitched.get("stitched_rooms", {})
        env = stitched.get("property_envelope", {"min_x": -1, "min_y": -1, "max_x": 12, "max_y": 10})
        damages = contract.get("damage_assessment", {}).get("damage_regions", [])
        flags = contract.get("concealed_damage_flags", [])

        min_x = env.get("min_x", 0.0) - 1.0
        min_y = env.get("min_y", 0.0) - 1.0
        max_x = env.get("max_x", 10.0) + 1.0
        max_y = env.get("max_y", 8.0) + 1.0

        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)

        # SVG coordinate system: 1000px width
        svg_w = 1100
        svg_h = int(svg_w * (span_y / span_x)) + 120
        scale = (svg_w - 120) / span_x

        def tx(x: float) -> float:
            return 60 + (x - min_x) * scale

        def ty(y: float) -> float:
            # SVG y is inverted (top to bottom)
            return (svg_h - 60) - (y - min_y) * scale

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" height="100%" style="background-color: #0b0f19; font-family: Inter, system-ui, -apple-system, sans-serif;">',
            '<defs>',
            '  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">',
            '    <feGaussianBlur stdDeviation="3" result="blur" />',
            '    <feComposite in="SourceGraphic" in2="blur" operator="over" />',
            '  </filter>',
            '  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">',
            '    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.75"/>',
            '  </pattern>',
            '</defs>',
            f'<rect width="{svg_w}" height="{svg_h}" fill="url(#grid)" />',
            
            # Header
            f'<text x="40" y="45" fill="#f8fafc" font-size="20" font-weight="700" letter-spacing="0.5">WHOLE-PROPERTY AS-BUILT &amp; DAMAGE REPORT</text>',
            f'<text x="40" y="68" fill="#94a3b8" font-size="13">Tier: <tspan fill="#38bdf8" font-weight="600">{contract["capture_metadata"]["input_tier"].upper()}</tspan> | Device: {contract["capture_metadata"]["device_model"]} | Schema: {contract["schema_version"]}</text>',
            f'<rect x="{svg_w - 240}" y="25" width="200" height="42" rx="8" fill="#1e293b" stroke="#334155"/>',
            f'<text x="{svg_w - 140}" y="44" fill="#94a3b8" font-size="11" text-anchor="middle">TOTAL USABLE AREA</text>',
            f'<text x="{svg_w - 140}" y="61" fill="#38bdf8" font-size="14" font-weight="700" text-anchor="middle">{env.get("total_floor_area_m2", 0.0):.2f} m²</text>'
        ]

        # Render Rooms
        color_palette = ["#1e293b", "#0f172a", "#1e1b4b", "#172554", "#042f2e"]
        
        for idx, (rid, r) in enumerate(rooms.items()):
            walls = r.get("walls", [])
            if not walls:
                continue

            pts_str = " ".join([f"{tx(w['start_point'][0])},{ty(w['start_point'][1])}" for w in walls])
            bg_color = color_palette[idx % len(color_palette)]

            # Room fill
            svg_parts.append(f'<polygon points="{pts_str}" fill="{bg_color}" fill-opacity="0.7" stroke="#475569" stroke-width="1.5" stroke-dasharray="4,4"/>')

            # Room Center label
            cx = sum(w['start_point'][0] for w in walls) / len(walls)
            cy = sum(w['start_point'][1] for w in walls) / len(walls)
            svg_parts.append(f'<text x="{tx(cx)}" y="{ty(cy) - 10}" fill="#f1f5f9" font-size="15" font-weight="600" text-anchor="middle">{r.get("name", rid)}</text>')
            svg_parts.append(f'<text x="{tx(cx)}" y="{ty(cy) + 10}" fill="#38bdf8" font-size="12" text-anchor="middle">{r.get("floor_area_m2", 0.0):.2f} m² | H: {r.get("ceiling_height_m", 2.6):.2f}m</text>')

            # Wall lines & Dimension text
            for w in walls:
                x1, y1 = tx(w['start_point'][0]), ty(w['start_point'][1])
                x2, y2 = tx(w['end_point'][0]), ty(w['end_point'][1])

                svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#94a3b8" stroke-width="4" stroke-linecap="round"/>')

                # Wall length label
                mx = (x1 + x2) / 2
                my = (y1 + y2) / 2
                length_m = w.get("length_m", 0.0)
                svg_parts.append(f'<rect x="{mx - 24}" y="{my - 9}" width="48" height="18" rx="4" fill="#0f172a" stroke="#475569" stroke-width="1"/>')
                svg_parts.append(f'<text x="{mx}" y="{my + 4}" fill="#f8fafc" font-size="10" font-weight="600" text-anchor="middle">{length_m:.2f}m</text>')

        # Render Damage Overlays
        for dmg in damages:
            dclass = dmg.get("damage_class", "water_damage")
            dcolor = "#ef4444" if dclass == "water_damage" else ("#f59e0b" if dclass == "wall_crack" else "#a855f7")
            area = dmg.get("metric_extent", {}).get("area_m2", 1.0)

            # Find matching room center for location anchor
            rid = dmg.get("room_id")
            r_info = rooms.get(rid, {})
            walls = r_info.get("walls", [])
            if walls:
                cx = sum(w['start_point'][0] for w in walls) / len(walls) + 0.6
                cy = sum(w['start_point'][1] for w in walls) / len(walls) - 0.5
                svg_parts.append(f'<circle cx="{tx(cx)}" cy="{ty(cy)}" r="22" fill="{dcolor}" fill-opacity="0.25" stroke="{dcolor}" stroke-width="2" filter="url(#glow)"/>')
                svg_parts.append(f'<text x="{tx(cx)}" y="{ty(cy) + 4}" fill="{dcolor}" font-size="11" font-weight="700" text-anchor="middle">{dclass[:4].upper()}</text>')
                svg_parts.append(f'<text x="{tx(cx)}" y="{ty(cy) + 32}" fill="#fca5a5" font-size="10" font-weight="600" text-anchor="middle">{area:.2f} m²</text>')

        # Footer Legend
        svg_parts.append(f'<rect x="40" y="{svg_h - 45}" width="{svg_w - 80}" height="32" rx="6" fill="#1e293b" stroke="#334155"/>')
        svg_parts.append(f'<text x="60" y="{svg_h - 25}" fill="#cbd5e1" font-size="11"><tspan fill="#38bdf8">■</tspan> Reconstructed Boundary  <tspan fill="#ef4444" dx="15">●</tspan> Water Damage  <tspan fill="#f59e0b" dx="15">●</tspan> Crack  <tspan fill="#a855f7" dx="15">●</tspan> Mold  <tspan dx="25" fill="#facc15">⚠ Concealed Flags Active: {len(flags)}</tspan></text>')

        svg_parts.append('</svg>')

        svg_content = "\n".join(svg_parts)
        os.makedirs(os.path.dirname(os.path.abspath(output_svg_path)), exist_ok=True)
        with open(output_svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        return svg_content

    def render_html_report(self, contract: Dict[str, Any], output_html_path: str, svg_content: str) -> str:
        """Generates an interactive HTML dashboard containing floor plan, damage scopes, and gates."""
        meta = contract["capture_metadata"]
        rooms = contract.get("rooms", [])
        damages = contract.get("damage_assessment", {}).get("damage_regions", [])
        flags = contract.get("concealed_damage_flags", [])
        scopes = contract.get("scope_of_work", [])
        total_cost = sum((s.get("total_cost_usd") or 0.0) for s in scopes)

        def _format_cost(val):
            return f"${val:.2f}" if val is not None else "N/A"

        def _format_qty(q, unit):
            return f"{q} {unit}" if q is not None else "N/A"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Property As-Built & Damage Assessment Report</title>
    <style>
        :root {{
            --bg-main: #090d16;
            --bg-card: #111827;
            --border-color: #1f2937;
            --accent: #38bdf8;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-main);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding: 32px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        .header {{
            display: flex; justify-content: space-between; align-items: center;
            padding-bottom: 24px; border-bottom: 1px solid var(--border-color); margin-bottom: 28px;
        }}
        .header h1 {{ font-size: 26px; font-weight: 700; color: #fff; }}
        .badge {{
            padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600;
            background: rgba(56, 189, 248, 0.15); color: var(--accent); border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        .grid-2 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 28px; }}
        .card {{
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 12px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        }}
        .card h2 {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary); border-bottom: 1px solid #273549; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #1f2937; }}
        th {{ color: var(--text-secondary); font-weight: 600; background: #0c1322; }}
        .flag-card {{
            background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px; padding: 14px; margin-bottom: 12px;
        }}
        .flag-title {{ color: var(--danger); font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px; }}
        .flag-desc {{ font-size: 12px; color: #e2e8f0; margin-top: 4px; }}
        .cost-total {{ font-size: 24px; font-weight: 700; color: #34d399; margin-top: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Property As-Built &amp; Damage Scope Report</h1>
                <p style="color: var(--text-secondary); font-size: 14px; margin-top: 4px;">Capture ID: <strong>{contract["property_id"]}</strong> | Input Tier: <strong>{meta["input_tier"].upper()}</strong> | Processed in {meta.get("timing", {}).get("processing_time_seconds", 0.0)}s</p>
            </div>
            <div>
                <span class="badge">SCHEMA COMPLIANT v{contract["schema_version"]}</span>
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>Stitched As-Built Floor Plan</h2>
                <div style="border-radius: 8px; overflow: hidden; border: 1px solid #1f2937;">
                    {svg_content}
                </div>
            </div>

            <div class="card">
                <h2>Concealed Damage Risk Flags ({len(flags)})</h2>
                {''.join([f'''
                <div class="flag-card">
                    <div class="flag-title">⚠️ {f['rule_fired']}: {f['rule_title']}</div>
                    <div class="flag-desc">{f['justification']}</div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;"><strong>Action:</strong> {f['recommended_investigation']}</div>
                </div>
                ''' for f in flags])}

                <h2 style="margin-top: 24px;">Repair Scope Estimate</h2>
                <p style="font-size: 13px; color: var(--text-secondary);">Xactimate / IICRC Line Items:</p>
                <div class="cost-total">${total_cost:,.2f} USD</div>
            </div>
        </div>

        <div class="card">
            <h2>Detailed Scope of Work Line Items Keyed to Surfaces</h2>
            <table>
                <thead>
                    <tr>
                        <th>Item ID</th>
                        <th>Surface ID</th>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Qty</th>
                        <th>Unit Cost</th>
                        <th>Total Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr>
                        <td><code>{s['item_id']}</code></td>
                        <td><code>{s['surface_id']}</code></td>
                        <td><strong>{s['code']}</strong></td>
                        <td>{_format_qty(s['quantity'], s['unit'])}</td>
                        <td>${s['unit_cost_usd']:.2f}</td>
                        <td><strong>{_format_cost(s['total_cost_usd'])}</strong></td>
                    </tr>
                    ''' for s in scopes])}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_html_path
