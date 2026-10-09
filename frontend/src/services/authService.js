import { api, setAccessToken } from "./api.js";

export const authService = {
  register: (payload) => api.post("/auth/register", payload).then((r) => r.data),

  async login(email, password) {
    const { data } = await api.post("/auth/login", { email, password });
    setAccessToken(data.data.access_token);
    return data.data.user;
  },

  async logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      setAccessToken(null); // always clear local state, even if the request failed
    }
  },

  verifyEmail: (token) => api.get("/auth/verify-email", { params: { token } }).then((r) => r.data),
  resendVerification: (email) => api.post("/auth/resend-verification", { email }).then((r) => r.data),
  forgotPassword: (email) => api.post("/auth/forgot-password", { email }).then((r) => r.data),
  resetPassword: (payload) => api.post("/auth/reset-password", payload).then((r) => r.data),
};

export const userService = {
  getMe: () => api.get("/users/me").then((r) => r.data.data.user),
  updateMe: (payload) => api.patch("/users/me", payload).then((r) => r.data.data.user),
  changePassword: (payload) => api.post("/users/change-password", payload).then((r) => r.data),
};

export const adminService = {
  listUsers: (page = 1, pageSize = 10) =>
    api.get("/admin/users", { params: { page, page_size: pageSize } }).then((r) => r.data.data),
  activate: (id) => api.patch(`/admin/users/${id}/activate`).then((r) => r.data.data.user),
  deactivate: (id) => api.patch(`/admin/users/${id}/deactivate`).then((r) => r.data.data.user),
  setRole: (id, role) => api.patch(`/admin/users/${id}/role`, { role }).then((r) => r.data.data.user),
};
