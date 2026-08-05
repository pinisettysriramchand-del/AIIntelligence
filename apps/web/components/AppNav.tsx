"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { setTokens } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
  { href: "/decisions", label: "Decisions" },
  { href: "/reports", label: "Reports" },
  { href: "/chat", label: "Chat" },
];

export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <header className="nav">
      <Link href="/dashboard" className="brand">
        StratIQ
      </Link>
      <nav className="nav-links">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={pathname === link.href ? "active" : undefined}
          >
            {link.label}
          </Link>
        ))}
        <button
          className="secondary"
          onClick={() => {
            setTokens(null);
            router.push("/login");
          }}
        >
          Sign out
        </button>
      </nav>
    </header>
  );
}
