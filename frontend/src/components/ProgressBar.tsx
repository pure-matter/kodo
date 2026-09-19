import "./ProgressBar.css";

interface ProgressBarProps {
  label: string;
  value: number;
  target: number | null;
  fillColor: string;
  valueLabel: string;
}

export function ProgressBar({ label, value, target, fillColor, valueLabel }: ProgressBarProps) {
  const percent = target ? Math.min((value / target) * 100, 100) : 0;

  return (
    <div className="progress-row">
      <div className="progress-row-header">
        <span className="progress-label">{label}</span>
        <span className="progress-value">{valueLabel}</span>
      </div>
      <div className="progress-track">
        <div
          className="progress-fill"
          style={{ width: `${percent}%`, background: fillColor }}
        />
      </div>
    </div>
  );
}
