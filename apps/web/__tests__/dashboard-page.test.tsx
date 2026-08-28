import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "@/app/dashboard/page";

const replaceMock = jest.fn();
const pushMock = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: pushMock }),
}));

const logoutMock = jest.fn();
const useAuthMock = jest.fn(() => ({
  user: { id: "u1", tenant_id: "t1", email: "a@example.com", display_name: "Ayşe", role: "STUDENT", is_active: true },
  accessToken: "fake-token",
  status: "authenticated",
  logout: logoutMock,
}));
jest.mock("@/lib/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

const fetchStudentDashboardMock = jest.fn();
jest.mock("@/lib/dashboard", () => ({
  fetchStudentDashboard: (...args: unknown[]) => fetchStudentDashboardMock(...args),
}));

describe("DashboardPage", () => {
  beforeEach(() => {
    fetchStudentDashboardMock.mockReset();
    replaceMock.mockReset();
    useAuthMock.mockReturnValue({
      user: { id: "u1", tenant_id: "t1", email: "a@example.com", display_name: "Ayşe", role: "STUDENT", is_active: true },
      accessToken: "fake-token",
      status: "authenticated",
      logout: logoutMock,
    });
  });

  it("redirects a TEACHER to the teacher dashboard instead of rendering the student view", () => {
    useAuthMock.mockReturnValue({
      user: { id: "t1", tenant_id: "t1", email: "t@example.com", display_name: "Öğretmen", role: "TEACHER", is_active: true },
      accessToken: "fake-token",
      status: "authenticated",
      logout: logoutMock,
    });

    render(<DashboardPage />);

    expect(replaceMock).toHaveBeenCalledWith("/dashboard/teacher");
    expect(fetchStudentDashboardMock).not.toHaveBeenCalled();
  });

  it("renders skill progress using only plain-language labels, never a raw score", async () => {
    fetchStudentDashboardMock.mockResolvedValueOnce({
      student_user_id: "u1",
      skills: [
        {
          skill_id: "s1",
          skill_name: "Newton'un İkinci Yasası",
          mastery_label: "İyi öğreniyorsun",
          is_weak: false,
          is_strong: true,
          next_action_label: "Bildiğini farklı bir bağlamda uygula",
          pending_retention_checkpoints: 1,
        },
      ],
      weak_skill_count: 0,
      strong_skill_count: 1,
      upcoming_retention_count: 1,
    });

    render(<DashboardPage />);

    expect(await screen.findByText("Newton'un İkinci Yasası")).toBeInTheDocument();
    expect(screen.getByText("İyi öğreniyorsun")).toBeInTheDocument();
    expect(screen.getByText("Bildiğini farklı bir bağlamda uygula")).toBeInTheDocument();

    // §26/§75: nothing that looks like a raw posterior float (e.g. "0.857")
    // is ever rendered.
    expect(document.body.textContent).not.toMatch(/0\.\d+/);
  });

  it("shows an empty-state message when the student has no skill activity yet", async () => {
    fetchStudentDashboardMock.mockResolvedValueOnce({
      student_user_id: "u1",
      skills: [],
      weak_skill_count: 0,
      strong_skill_count: 0,
      upcoming_retention_count: 0,
    });

    render(<DashboardPage />);

    expect(await screen.findByText(/Henüz bir konu üzerinde çalışmadın/)).toBeInTheDocument();
  });

  it("shows an error message if the dashboard request fails", async () => {
    fetchStudentDashboardMock.mockRejectedValueOnce(new Error("network error"));

    render(<DashboardPage />);

    await waitFor(() => expect(screen.getByText("Panonuz yüklenirken bir sorun oluştu.")).toBeInTheDocument());
  });
});
