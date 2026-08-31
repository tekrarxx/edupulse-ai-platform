import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ResetPasswordPage from "@/app/reset-password/page";
import { AuthApiError, confirmPasswordReset } from "@/lib/auth";

const pushMock = jest.fn();
let searchParamsToken: string | null = "a-real-reset-token";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => ({ get: (key: string) => (key === "token" ? searchParamsToken : null) }),
}));

jest.mock("@/lib/auth", () => ({
  ...jest.requireActual("@/lib/auth"),
  confirmPasswordReset: jest.fn(),
}));

const confirmPasswordResetMock = confirmPasswordReset as jest.Mock;

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    pushMock.mockReset();
    confirmPasswordResetMock.mockReset();
    searchParamsToken = "a-real-reset-token";
  });

  it("shows an invalid-link message when there is no token in the URL", () => {
    searchParamsToken = null;
    render(<ResetPasswordPage />);

    expect(screen.getByText("Geçersiz bağlantı")).toBeInTheDocument();
  });

  it("submits the new password with the token from the URL", async () => {
    confirmPasswordResetMock.mockResolvedValueOnce(undefined);
    render(<ResetPasswordPage />);

    fireEvent.change(screen.getByLabelText(/yeni şifre/i), { target: { value: "brand-new-password-2" } });
    fireEvent.click(screen.getByRole("button", { name: /şifreyi güncelle/i }));

    await waitFor(() =>
      expect(confirmPasswordResetMock).toHaveBeenCalledWith({
        token: "a-real-reset-token",
        new_password: "brand-new-password-2",
      })
    );
    expect(await screen.findByText("Şifren güncellendi")).toBeInTheDocument();
  });

  it("shows a generic error for an expired or already-used token", async () => {
    confirmPasswordResetMock.mockRejectedValueOnce(new AuthApiError(400, "invalid_or_expired_token"));
    render(<ResetPasswordPage />);

    fireEvent.change(screen.getByLabelText(/yeni şifre/i), { target: { value: "brand-new-password-2" } });
    fireEvent.click(screen.getByRole("button", { name: /şifreyi güncelle/i }));

    expect(await screen.findByText(/geçersiz veya süresi dolmuş/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
