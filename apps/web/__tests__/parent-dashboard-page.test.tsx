import { render, screen, waitFor } from "@testing-library/react";
import ParentDashboardPage from "@/app/dashboard/parent/page";

const replaceMock = jest.fn();
const pushMock = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: pushMock }),
}));

const logoutMock = jest.fn();
const parentUser = { id: "p1", tenant_id: "t1", email: "veli@example.com", display_name: "Veli", role: "PARENT", is_active: true };
const useAuthMock = jest.fn(() => ({
  user: parentUser,
  accessToken: "fake-token",
  status: "authenticated",
  logout: logoutMock,
}));
jest.mock("@/lib/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

const fetchMyChildrenMock = jest.fn();
const fetchStudentDashboardMock = jest.fn();
jest.mock("@/lib/dashboard", () => ({
  fetchMyChildren: (...args: unknown[]) => fetchMyChildrenMock(...args),
  fetchStudentDashboard: (...args: unknown[]) => fetchStudentDashboardMock(...args),
}));

describe("ParentDashboardPage", () => {
  beforeEach(() => {
    fetchMyChildrenMock.mockReset();
    fetchStudentDashboardMock.mockReset();
    replaceMock.mockReset();
    useAuthMock.mockReturnValue({
      user: parentUser,
      accessToken: "fake-token",
      status: "authenticated",
      logout: logoutMock,
    });
  });

  it("redirects a non-PARENT away", () => {
    useAuthMock.mockReturnValue({
      user: { id: "s1", tenant_id: "t1", email: "s@example.com", display_name: "Öğrenci", role: "STUDENT", is_active: true },
      accessToken: "fake-token",
      status: "authenticated",
      logout: logoutMock,
    });

    render(<ParentDashboardPage />);

    expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    expect(fetchMyChildrenMock).not.toHaveBeenCalled();
  });

  it("shows an empty-state message for a parent with no linked children", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([]);

    render(<ParentDashboardPage />);

    expect(await screen.findByText("Hesabınıza bağlı bir öğrenci bulunmuyor.")).toBeInTheDocument();
  });

  it("auto-selects a single child and renders their dashboard directly", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([{ student_user_id: "c1", display_name: "Ayşe", consent_on_file: true }]);
    fetchStudentDashboardMock.mockResolvedValueOnce({
      student_user_id: "c1",
      skills: [],
      weak_skill_count: 0,
      strong_skill_count: 0,
      upcoming_retention_count: 0,
    });

    render(<ParentDashboardPage />);

    await waitFor(() => expect(fetchStudentDashboardMock).toHaveBeenCalledWith("fake-token", "c1"));
    expect(await screen.findByText("Ayşe")).toBeInTheDocument();
    // No picker buttons for a single child.
    expect(screen.queryAllByRole("button", { name: "Ayşe" })).toHaveLength(0);
  });

  it("shows a picker for multiple children and switches on click", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([
      { student_user_id: "c1", display_name: "Ayşe", consent_on_file: true },
      { student_user_id: "c2", display_name: "Mehmet", consent_on_file: false },
    ]);

    render(<ParentDashboardPage />);

    expect(await screen.findByRole("button", { name: "Ayşe" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mehmet" })).toBeInTheDocument();
    expect(fetchStudentDashboardMock).not.toHaveBeenCalled();
  });

  it("warns when the selected child has no consent on file", async () => {
    fetchMyChildrenMock.mockResolvedValueOnce([{ student_user_id: "c1", display_name: "Ayşe", consent_on_file: false }]);
    fetchStudentDashboardMock.mockResolvedValueOnce({
      student_user_id: "c1",
      skills: [],
      weak_skill_count: 0,
      strong_skill_count: 0,
      upcoming_retention_count: 0,
    });

    render(<ParentDashboardPage />);

    expect(await screen.findByText(/rıza onayı bulunmuyor/)).toBeInTheDocument();
  });
});
