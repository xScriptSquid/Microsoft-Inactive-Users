

REPORT_CSS = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        :root {
            --ink: #ececec;
            --ink-soft: #c4c4c4;
            --steel: #9a9ea6;
            --line: #2e2e33;
            --paper: #0f0f11;
            --card: #191a1d;
            --field: #222327;
            --field-border: #3a3b40;
            --orange: #f2913a;
            --orange-deep: #e0700f;
            --critical: #f0584c;
            --focus: #5b8def;
            --success: #3ecf8e;
            --radius: 4px;
        }

        @page {
            size: landscape;
            margin: 0.25in;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--paper);
            color: var(--ink);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .masthead {
            background: #000;
            color: #fff;
            border-radius: var(--radius) var(--radius) 0 0;
            padding: 24px 28px;
            border-bottom: 5px solid var(--orange);
        }

        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 20px;
        }

        .kicker {
            font-size: 11px;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--orange);
            font-weight: 700;
            margin: 0 0 8px;
        }

        h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.01em;
            line-height: 1.15;
            color: #fff;
        }

        .subtitle {
            margin: 10px 0 0;
            color: #c9c9c9;
            font-size: 14px;
        }

        .mode-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: var(--radius);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            white-space: nowrap;
        }

        .mode-badge.dry-run {
            background: #241d14;
            color: var(--orange);
            border: 1px solid var(--orange-deep);
        }

        .mode-badge.live {
            background: #142219;
            color: var(--success);
            border: 1px solid var(--success);
        }

        .report-body {
            background: var(--card);
            border: 1px solid var(--line);
            border-top: none;
            border-radius: 0 0 var(--radius) var(--radius);
            padding: 24px 28px 28px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--field);
            border: 1px solid var(--field-border);
            border-radius: var(--radius);
            padding: 16px 18px;
        }

        .stat-label {
            font-size: 11px;
            color: var(--steel);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: var(--ink);
        }

        .stat-value.inactive {
            color: var(--orange);
        }

        .stat-value.active {
            color: var(--success);
        }

        .table-container {
            background: var(--field);
            border: 1px solid var(--field-border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            padding: 12px 16px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--steel);
            background: #1a1b1f;
            border-bottom: 1px solid var(--line);
        }

        td {
            padding: 10px 16px;
            border-bottom: 1px solid var(--line);
            font-size: 13px;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .email {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 12px;
            color: var(--ink-soft);
        }

        .name {
            color: var(--ink);
            font-weight: 600;
        }

        .date {
            color: var(--steel);
        }

        .status {
            display: inline-flex;
            align-items: center;
            padding: 5px 10px;
            border-radius: var(--radius);
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            white-space: nowrap;
            border: 1px solid transparent;
        }

        .status-warning {
            background: #241d14;
            color: var(--orange);
            border-color: var(--orange-deep);
        }

        .status-success {
            background: #142219;
            color: var(--success);
            border-color: var(--success);
        }

        .status-error {
            background: #2a1818;
            color: #ffb4ae;
            border-color: var(--critical);
        }

        footer {
            margin-top: 24px;
            padding-top: 18px;
            border-top: 2px solid var(--line);
            text-align: center;
            color: var(--steel);
            font-size: 12px;
        }
"""
