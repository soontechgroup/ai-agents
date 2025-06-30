import { createContext } from "react";

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  resetMessages: () => void;
  error: string | null;
  success: string | null;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | null>(null); 