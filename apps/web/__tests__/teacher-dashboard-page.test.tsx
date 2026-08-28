import { render, screen, waitFor } from "@testing-library/react";
import TeacherDashboardPage from "@/app/dashboard/teacher/page";

const replaceMock = jest.fn();
const pushMock = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: pushMock }),
}));

const logoutMock = jest.fn();
// A stable object reference — useAuth() must return the same `user`
// identity across re-renders, or a useEffect depending on `user` re-fires
// on every render and re-triggers the fetch.
const teacherUser = { id: "t1", tenant_id: "tenant1", email: "t@example.com", display_name: "Öğretmen", role: "TEACHER", is_active: true };
jest.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: teacherUser,
    accessToken: "fake-token",
    status: "authenticated",
    logout: logoutMock,
  }),
}));

const fetchTeacherDashboardMock = jest.fn();
jest.mock("@/lib/dashboard", () => ({
  fetchTeacherDashboard: (...args: unknown[]) => fetchTeacherDashboardMock(...args),
}));

describe("TeacherDashboardPage", () => {
  beforeEach(() => {
    fetchTeacherDashboardMock.mockReset();
    replaceMock.mockReset();
  });

  it("renders students needing attention with their reasons, in plain language", async () => {
    fetchTeacherDashboardMock.mockResolvedValueOnce({
      students: [
        {
          student_user_id: "s1",
          student_name: "Ayşe Yılmaz",
          needs_attention: true,
          attention_reasons: ["Zayıf beceriler var"],
          weak_skill_names: ["Newton'un İkinci Yasası"],
          improving_skill_names: [],
          forgetting_skill_names: [],
          misconception_skill_names: [],
          next_action_label: "Daha kolay bir görevle devam et",
        },
      ],
      students_needing_attention_count: 1,
    });

    render(<TeacherDashboardPage />);

    expect(await screen.findByText("Ayşe Yılmaz")).toBeInTheDocument();
    expect(screen.getByText("İlgi gerekiyor")).toBeInTheDocument();
    expect(screen.getByText("Zayıf beceriler var")).toBeInTheDocument();
    expect(screen.getByText("1 öğrenci ilgi gerektiriyor.")).toBeInTheDocument();

    // §26/§75 discipline extended to the teacher UI too.
    expect(document.body.textContent).not.toMatch(/0\.\d+/);
  });

  it("shows an empty-state message for a teacher with no linked students", async () => {
    fetchTeacherDashboardMock.mockResolvedValueOnce({ students: [], students_needing_attention_count: 0 });

    render(<TeacherDashboardPage />);

    expect(await screen.findByText("Henüz size bağlı bir öğrenci yok.")).toBeInTheDocument();
  });

  it("shows an error message if the request fails", async () => {
    fetchTeacherDashboardMock.mockRejectedValueOnce(new Error("network error"));

    render(<TeacherDashboardPage />);

    await waitFor(() => expect(screen.getByText("Pano yüklenirken bir sorun oluştu.")).toBeInTheDocument());
  });
});
