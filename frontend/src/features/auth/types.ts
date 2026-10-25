import type { ReactNode } from "react";

import type { MeResponse } from "../../services/api";

export type AuthenticatedAppProps = {
  user: MeResponse;
  signOut: () => Promise<void>;
};

export type AuthGateChildren = (
  user: MeResponse,
  signOut: () => Promise<void>,
) => ReactNode;
