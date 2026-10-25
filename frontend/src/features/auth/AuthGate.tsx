import { useEffect, useState } from "react";

import { getMe, logout, type MeResponse } from "../../services/api";
import LoginPage from "./LoginPage";

type AuthGateProps = {
  children: (user: MeResponse, signOut: () => Promise<void>) => React.ReactNode;
};

function AuthGate({ children }: AuthGateProps) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("saru_access_token"));
  const [user, setUser] = useState<MeResponse | null>(null);
  const [checking, setChecking] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;

    getMe(token)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("saru_access_token");
        setToken(null);
      })
      .finally(() => setChecking(false));
  }, [token]);

  function handleAuthenticated(nextToken: string) {
    localStorage.setItem("saru_access_token", nextToken);
    setChecking(true);
    setToken(nextToken);
  }

  async function signOut() {
    if (token) await logout(token).catch(() => undefined);
    localStorage.removeItem("saru_access_token");
    setUser(null);
    setToken(null);
  }

  if (!token) return <LoginPage onAuthenticated={handleAuthenticated} />;
  if (checking || !user) return <main className="loading-shell">Authenticating…</main>;

  return <>{children(user, signOut)}</>;
}

export default AuthGate;
