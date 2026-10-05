import type { PropsWithChildren, ReactNode } from "react";
import "./Card.css";

export function Card({
  children,
  title,
  headerExtra,
}: PropsWithChildren<{ title?: string; headerExtra?: ReactNode }>) {
  return (
    <section className="card">
      {(title || headerExtra) && (
        <div className="card-header">
          {title && <h2 className="card-title">{title}</h2>}
          {headerExtra && <span className="card-header-extra">{headerExtra}</span>}
        </div>
      )}
      {children}
    </section>
  );
}
