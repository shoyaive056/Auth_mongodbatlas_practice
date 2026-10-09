import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { refreshAccessToken, setSessionExpiredHandler } from "../services/api.js";
import { authService, userService } from "../services/authService.js";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while we check for an existing session

  // On page load the access token is gone (it lives in memory only).
  // Try to get a new one with the refresh cookie to restore the session.
  useEffect(() => {
    let cancelled = false;
    refreshAccessToken()
      .then((data) => {
        if (!cancelled) setUser(data.user);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // If a refresh fails while the app is open, drop the user back to the login page.
  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
  }, []);

  const login = useCallback(async (email, password) => {
    const loggedInUser = await authService.login(email, password);
    setUser(loggedInUser);
    return loggedInUser;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const reloadUser = useCallback(async () => {
    const fresh = await userService.getMe();
    setUser(fresh);
    return fresh;
  }, []);

  const value = useMemo(
    () => ({ user, loading, isAuthenticated: !!user, isAdmin: user?.role === "admin", login, logout, reloadUser, setUser }),
    [user, loading, login, logout, reloadUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
