"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

export function VendorAccountSelector() {
  const { user, selectVendor, signOut } = useAuth();
  const router = useRouter();
  const [pendingVendor, setPendingVendor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!user) return null;

  async function chooseVendor(vendorCode: string) {
    setPendingVendor(vendorCode);
    setError(null);
    try {
      await selectVendor(vendorCode);
      router.replace("/");
    } catch (selectionError) {
      setError(
        selectionError instanceof Error
          ? selectionError.message
          : "Unable to open that vendor account",
      );
      setPendingVendor(null);
    }
  }

  return (
    <main className="vendor-selection-page">
      <section className="vendor-selection-panel">
        <Image
          alt="Buddy's Home Furnishings"
          height={76}
          priority
          src="/brand/buddys-logo-compact.png"
          width={190}
        />
        <span className="brand-badge">Vendor workspace</span>
        <h1>Select a vendor account</h1>
        <p>
          Choose the company you are representing in this session. You can
          switch accounts later from the command center.
        </p>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="vendor-account-grid">
          {user.vendor_accounts.map((account) => {
            const isPending = pendingVendor === account.vendor_code;
            const isActive = user.active_vendor_code === account.vendor_code;
            return (
              <button
                className={`vendor-account-card${isActive ? " is-active" : ""}`}
                disabled={pendingVendor !== null}
                key={account.vendor_code}
                onClick={() => void chooseVendor(account.vendor_code)}
                type="button"
              >
                <strong>{account.name}</strong>
                <span>{account.vendor_code}</span>
                <small>
                  {isPending
                    ? "Opening…"
                    : isActive
                      ? "Current account"
                      : "Open account →"}
                </small>
              </button>
            );
          })}
        </div>

        <button
          className="module-home-link"
          onClick={() => {
            signOut();
            router.replace("/");
          }}
          type="button"
        >
          Sign out
        </button>
      </section>
    </main>
  );
}
