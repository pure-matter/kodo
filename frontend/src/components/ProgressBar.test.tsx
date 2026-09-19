import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProgressBar } from "./ProgressBar";

describe("ProgressBar", () => {
  it("renders the label and value", () => {
    render(
      <ProgressBar label="Groceries" value={200} target={400} fillColor="green" valueLabel="$200 / $400" />,
    );
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("$200 / $400")).toBeInTheDocument();
  });

  it("fills proportionally to value/target", () => {
    const { container } = render(
      <ProgressBar label="Groceries" value={200} target={400} fillColor="green" valueLabel="" />,
    );
    const fill = container.querySelector(".progress-fill") as HTMLElement;
    expect(fill.style.width).toBe("50%");
  });

  it("caps the fill at 100% even when over target", () => {
    const { container } = render(
      <ProgressBar label="Groceries" value={500} target={400} fillColor="red" valueLabel="" />,
    );
    const fill = container.querySelector(".progress-fill") as HTMLElement;
    expect(fill.style.width).toBe("100%");
  });

  it("renders an empty bar when there's no target", () => {
    const { container } = render(
      <ProgressBar label="Misc" value={50} target={null} fillColor="gray" valueLabel="$50" />,
    );
    const fill = container.querySelector(".progress-fill") as HTMLElement;
    expect(fill.style.width).toBe("0%");
  });
});
