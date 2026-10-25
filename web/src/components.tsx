import type { ReactNode } from "react";
import { formatFixed } from "./format";

export function DataTable({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: string[][];
}) {
  return (
    <div className="table-wrap">
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row[0]}-${index}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${headerKey(headers, cellIndex)}-${cell}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function headerKey(headers: string[], index: number): string {
  return headers[index] ?? String(index);
}

export function ChartPatterns() {
  return (
    <svg className="pattern-source" aria-hidden="true">
      <defs>
        <pattern id="solid" width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="#0f2744" />
        </pattern>
        <pattern id="diag" width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="#1f4e79" />
          <path d="M0 8 L8 0" stroke="#f4e2c4" strokeWidth="2" />
        </pattern>
        <pattern id="dots" width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="#b86e00" />
          <circle cx="2" cy="2" r="1.2" fill="#fff8ea" />
        </pattern>
        <pattern id="horiz" width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="#2f6fad" />
          <path d="M0 4 H8" stroke="#ffffff" strokeWidth="1.5" />
        </pattern>
        <pattern id="cross" width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="#5c3b16" />
          <path d="M0 0 L8 8 M8 0 L0 8" stroke="#f4e2c4" strokeWidth="1.2" />
        </pattern>
        <pattern id="vert" width="8" height="8" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="#3d5a40" />
          <path d="M4 0 V8" stroke="#ffffff" strokeWidth="1.6" />
        </pattern>
      </defs>
    </svg>
  );
}

const PATTERN_IDS = ["solid", "diag", "dots", "horiz", "cross", "vert"];

export function patternFor(index: number): string {
  return `url(#${PATTERN_IDS[index % PATTERN_IDS.length]})`;
}

export function Legend({ items }: { items: { label: string; index: number }[] }) {
  return (
    <ul className="legend">
      {items.map((item) => (
        <li key={item.label}>
          <svg width="22" height="14" aria-hidden="true">
            <rect width="22" height="14" fill={patternFor(item.index)} stroke="#0f2744" />
          </svg>
          <span>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}

export function HorizontalBars({
  title,
  unit,
  rows,
}: {
  title: string;
  unit: string;
  rows: { label: string; value: number; digits: number; index: number }[];
}) {
  const max = Math.max(...rows.map((row) => row.value), 0.0001);
  const width = 640;
  const rowHeight = 36;
  const labelWidth = 210;
  const height = rows.length * rowHeight + 8;
  const summary = rows.map((row) => `${row.label} ${formatFixed(row.value, row.digits)} ${unit}`).join(". ");
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}. ${summary}`}>
        {rows.map((row, index) => {
          const y = index * rowHeight + 6;
          const barWidth = ((width - labelWidth - 90) * row.value) / max;
          return (
            <g key={row.label}>
              <text x="0" y={y + 16} className="chart-label">
                {row.label}
              </text>
              <rect x={labelWidth} y={y} width={Math.max(barWidth, 1)} height="18" fill={patternFor(row.index)} stroke="#0f2744" />
              <text x={labelWidth + barWidth + 8} y={y + 14} className="chart-value">
                {formatFixed(row.value, row.digits)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export function ScatterPlot({
  title,
  points,
}: {
  title: string;
  points: { label: string; x: number; y: number; index: number }[];
}) {
  const width = 640;
  const height = 320;
  const pad = { left: 48, right: 16, top: 16, bottom: 36 };
  const maxX = Math.max(...points.map((point) => point.x), 1);
  const minY = Math.min(...points.map((point) => point.y), 0);
  const maxY = Math.max(...points.map((point) => point.y), 1);
  const spanY = Math.max(maxY - minY, 0.01);
  const sx = (value: number) => pad.left + ((width - pad.left - pad.right) * value) / maxX;
  const sy = (value: number) => pad.top + (height - pad.top - pad.bottom) * (1 - (value - minY) / spanY);
  const summary = points.map((point) => `${point.label}: nDCG ${formatFixed(point.y, 3)}, p50 ${formatFixed(point.x, 2)} ms`).join(". ");
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}. ${summary}`}>
        <line x1={pad.left} y1={height - pad.bottom} x2={width - pad.right} y2={height - pad.bottom} stroke="#5c6b7a" />
        <line x1={pad.left} y1={pad.top} x2={pad.left} y2={height - pad.bottom} stroke="#5c6b7a" />
        <text x={width / 2} y={height - 8} textAnchor="middle" className="chart-axis">
          p50-latenssi (ms)
        </text>
        <text x="16" y={height / 2} transform={`rotate(-90 16 ${height / 2})`} textAnchor="middle" className="chart-axis">
          nDCG@5
        </text>
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={sx(point.x)} cy={sy(point.y)} r="7" fill={patternFor(point.index)} stroke="#0f2744" />
            <text x={sx(point.x) + 10} y={sy(point.y) + 4} className="chart-label">
              {point.label}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}

export function NoticeList({ notices }: { notices: string[] }) {
  if (notices.length === 0) {
    return null;
  }
  return (
    <div className="notice" role="status">
      {notices.map((notice) => (
        <p key={notice}>{notice}</p>
      ))}
    </div>
  );
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
