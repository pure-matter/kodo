import type { PropsWithChildren } from "react";
import "./Card.css";

export function Card({ children, title }: PropsWithChildren<{ title?: string }>) {
  return (
    <section className="card">
      {title && <h2 className="card-title">{title}</h2>}
      {children}
    </section>
  );
}
