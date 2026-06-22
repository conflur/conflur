import "next-auth";
import "next-auth/jwt";

interface Principal {
  user: {
    id: string;
    email: string;
    full_name: string | null;
    is_platform_admin: boolean;
  };
  tenant_id: string;
  role: string;
}

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    principal?: Principal;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    principal?: Principal;
  }
}
