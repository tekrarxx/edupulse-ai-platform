import { render, screen } from "@testing-library/react";
import { StatusBadge } from "@/components/status-badge";

describe("StatusBadge", () => {
  it("renders the label and status text", () => {
    render(<StatusBadge label="Veritabanı" status="ok" />);

    expect(screen.getByText("Veritabanı")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();
  });

  it("renders an unavailable status distinctly from ok", () => {
    render(<StatusBadge label="Redis" status="unavailable" />);

    const status = screen.getByText("unavailable");
    expect(status.className).toContain("text-red-800");
  });
});
