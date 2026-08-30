import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AddUserForm } from "@/components/add-user-form";

const createTenantUserMock = jest.fn();
jest.mock("@/lib/auth", () => ({
  createTenantUser: (...args: unknown[]) => createTenantUserMock(...args),
}));

describe("AddUserForm", () => {
  beforeEach(() => {
    createTenantUserMock.mockReset();
  });

  it("submits the form and reports success, then clears the form", async () => {
    createTenantUserMock.mockResolvedValueOnce({
      id: "u1",
      tenant_id: "t1",
      email: "yeni@example.com",
      display_name: "Yeni Öğrenci",
      role: "STUDENT",
      is_active: true,
    });
    const onCreated = jest.fn();

    render(<AddUserForm accessToken="fake-token" onCreated={onCreated} />);

    fireEvent.change(screen.getByLabelText("Ad Soyad"), { target: { value: "Yeni Öğrenci" } });
    fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "yeni@example.com" } });
    fireEvent.change(screen.getByLabelText("Geçici Şifre"), { target: { value: "correct-horse-battery" } });
    fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));

    await waitFor(() =>
      expect(createTenantUserMock).toHaveBeenCalledWith("fake-token", {
        email: "yeni@example.com",
        password: "correct-horse-battery",
        display_name: "Yeni Öğrenci",
        role: "STUDENT",
      })
    );
    expect(onCreated).toHaveBeenCalled();
    await screen.findByText(/hesabı oluşturuldu/);
    expect((screen.getByLabelText("E-posta") as HTMLInputElement).value).toBe("");
  });

  it("shows a generic error message on failure, never the raw backend detail", async () => {
    createTenantUserMock.mockRejectedValueOnce(new Error("email_already_registered"));

    render(<AddUserForm accessToken="fake-token" onCreated={jest.fn()} />);

    fireEvent.change(screen.getByLabelText("Ad Soyad"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("E-posta"), { target: { value: "x@example.com" } });
    fireEvent.change(screen.getByLabelText("Geçici Şifre"), { target: { value: "correct-horse-battery" } });
    fireEvent.click(screen.getByRole("button", { name: "Oluştur" }));

    expect(await screen.findByText(/Kullanıcı oluşturulamadı/)).toBeInTheDocument();
    expect(screen.queryByText("email_already_registered")).not.toBeInTheDocument();
  });
});
