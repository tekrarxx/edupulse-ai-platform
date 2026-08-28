import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/login/page";
import { AuthApiError } from "@/lib/auth-context";

const pushMock = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

const loginMock = jest.fn();
jest.mock("@/lib/auth-context", () => {
  const actual = jest.requireActual("@/lib/auth-context");
  return {
    ...actual,
    useAuth: () => ({ login: loginMock }),
  };
});

describe("LoginPage", () => {
  beforeEach(() => {
    pushMock.mockReset();
    loginMock.mockReset();
  });

  it("submits the entered credentials and redirects to the dashboard", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "ogrenci@example.com" } });
    fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: "correct-horse-battery" } });
    fireEvent.click(screen.getByRole("button", { name: /giriş yap/i }));

    await waitFor(() => expect(loginMock).toHaveBeenCalledWith("ogrenci@example.com", "correct-horse-battery"));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/dashboard"));
  });

  it("shows a generic error message on invalid credentials without hinting which field was wrong", async () => {
    loginMock.mockRejectedValueOnce(new AuthApiError(401, "invalid_credentials"));
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "ogrenci@example.com" } });
    fireEvent.change(screen.getByLabelText("Şifre"), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: /giriş yap/i }));

    expect(await screen.findByText("E-posta veya şifre hatalı.")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
