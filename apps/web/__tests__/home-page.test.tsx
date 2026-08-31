import { render, screen } from "@testing-library/react";
import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders the marketing hero with calls to action", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /sıradaki adımı söyleyen öğrenme sistemi/i
    );
    expect(screen.getAllByRole("link", { name: /ücretsiz/i })[0]).toHaveAttribute("href", "/register");
    expect(screen.getAllByRole("link", { name: /giriş yap/i })[0]).toHaveAttribute("href", "/login");
  });

  it("does not fetch health-check data on the public homepage", () => {
    // The homepage is a static server component with no data dependency —
    // health-check status lives at /status instead (dev/ops tool, not a
    // sales-facing page).
    expect(HomePage.constructor.name).not.toBe("AsyncFunction");
  });
});
