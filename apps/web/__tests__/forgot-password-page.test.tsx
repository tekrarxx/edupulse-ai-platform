import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ForgotPasswordPage from "@/app/forgot-password/page";
import { AuthApiError, requestPasswordReset } from "@/lib/auth";

jest.mock("@/lib/auth", () => ({
  ...jest.requireActual("@/lib/auth"),
  requestPasswordReset: jest.fn(),
}));

const requestPasswordResetMock = requestPasswordReset as jest.Mock;

describe("ForgotPasswordPage", () => {
  beforeEach(() => {
    requestPasswordResetMock.mockReset();
  });

  it("shows the same generic confirmation whether or not the email exists", async () => {
    requestPasswordResetMock.mockResolvedValueOnce(undefined);
    render(<ForgotPasswordPage />);

    fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "ogrenci@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /sıfırlama bağlantısı gönder/i }));

    await waitFor(() => expect(screen.getByText("E-postanı kontrol et")).toBeInTheDocument());
    expect(requestPasswordResetMock).toHaveBeenCalledWith("ogrenci@example.com");
  });

  it("still shows the generic confirmation even if the request fails", async () => {
    requestPasswordResetMock.mockRejectedValueOnce(new AuthApiError(500, "server_error"));
    render(<ForgotPasswordPage />);

    fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "ogrenci@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: /sıfırlama bağlantısı gönder/i }));

    await waitFor(() => expect(screen.getByText("E-postanı kontrol et")).toBeInTheDocument());
  });
});
