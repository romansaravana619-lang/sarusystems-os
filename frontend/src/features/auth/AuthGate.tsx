import { useEffect, useState, type ReactNode } from "react";

import { getMe, logout, type MeResponse } from "../../services/api";
import LoginPage from "./LoginPage";

type AuthGateProps = {
  children: (user: MeResponse, signOut: () => Promise<void>) => ReactNode;
};

const TOKEN_KEY = "saru_access_token";

function AuthGate({ children }: AuthGateProps) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<MeResponse | null>(null);
  const [checking, setChecking] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;

    getMe(token)
      .then(setUser)
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => setChecking(false));
  }, [token]);

  function handleAuthenticated(nextToken: string) {
    sessionStorage.setItem(TOKEN_KEY, nextToken);
    setUser(null);
    setChecking(true);
    setToken(nextToken);
  }

  async function signOut() {
    if (token) await logout(token).catch(() => undefined);
    sessionStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setToken(null);
  }

  if (!token) return <LoginPage onAuthenticated={handleAuthenticated} />;
  if (checking || !user) return <main className="loading-shell">Authenticating…</main>;

  return <>{children(user, signOut)}</>;
}

export default AuthGate;
