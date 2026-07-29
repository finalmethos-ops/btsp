"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  downloadAnalyticsExport,
  ExecutiveEntitySpendMetric,
  ExecutiveSpendDashboard,
  getExecutiveSpendDashboard,
} from "@/lib/analytics-api";

function money(value: string, currency: string) {
  const amount = Number(value);
  try {
    return new Intl.NumberFormat("en-US", {
      currency,
      maximumFractionDigits: 0,
      style: "currency",
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString("en-US")}`;
  }
}

function groupedByCurrency(items: ExecutiveEntitySpendMetric[]) {
  return Object.entries(
    items.reduce<Record<string, ExecutiveEntitySpendMetric[]>>(
      (groups, item) => ({
        ...groups,
        [item.currency]: [...(groups[item.currency] ?? []), item],
      }),
      {},
    ),
  ).sort(([left], [right]) => left.localeCompare(right));
}

function EntitySpendPanel({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: ExecutiveEntitySpendMetric[];
}) {
  const groups = groupedByCurrency(items);
  return (
    <article className="executive-spend-card">
      <header>
        <div>
          <p className="brand-eyebrow">{subtitle}</p>
          <h3>{title}</h3>
        </div>
      </header>
      {groups.length ? (
        <div className="executive-entity-groups">
          {groups.map(([currency, metrics]) => {
            const maximum = Math.max(
              ...metrics.map((metric) => Number(metric.amount)),
              1,
            );
            const total = metrics.reduce(
              (sum, metric) => sum + Number(metric.amount),
              0,
            );
            return (
              <section key={currency}>
                <div className="executive-currency-total">
                  <span>{currency}</span>
                  <strong>{money(String(total), currency)}</strong>
                </div>
                <div className="executive-entity-bars">
                  {metrics.map((metric) => (
                    <div key={`${currency}-${metric.entity_code}`}>
                      <div>
                        <span>{metric.entity_code}</span>
                        <strong>{money(metric.amount, currency)}</strong>
                      </div>
                      <i>
                        <span
                          style={{
                            width: `${Math.max(
                              3,
                              (Number(metric.amount) / maximum) * 100,
                            )}%`,
                          }}
                        />
                      </i>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <p className="executive-spend-empty">
          No spend has posted in this period.
        </p>
      )}
    </article>
  );
}

export function ExecutiveSpendCommandCenter() {
  const [dashboard, setDashboard] = useState<ExecutiveSpendDashboard | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState<string | null>(null);

  async function downloadExecutivePack() {
    setDownloading(true);
    setDownloadMessage(null);
    try {
      const blob = await downloadAnalyticsExport("executive_pack");
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "btsp-executive-report-pack.xlsx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setDownloadMessage("Executive report pack downloaded.");
    } catch (reason) {
      setDownloadMessage(
        reason instanceof Error
          ? reason.message
          : "Executive report download failed.",
      );
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const result = await getExecutiveSpendDashboard();
        if (active) {
          setDashboard(result);
          setError(null);
        }
      } catch (reason) {
        if (active) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Spend tracking is temporarily unavailable.",
          );
        }
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  if (error && !dashboard) {
    return (
      <section className="executive-spend-dashboard">
        <p className="executive-spend-error">{error}</p>
      </section>
    );
  }
  if (!dashboard) {
    return (
      <section className="executive-spend-dashboard">
        <p className="executive-spend-empty">
          Loading executive spend tracking…
        </p>
      </section>
    );
  }

  const sellers = Object.entries(
    dashboard.top_sellers_mtd.reduce<
      Record<string, ExecutiveSpendDashboard["top_sellers_mtd"]>
    >(
      (groups, item) => ({
        ...groups,
        [item.currency]: [...(groups[item.currency] ?? []), item],
      }),
      {},
    ),
  ).sort(([left], [right]) => left.localeCompare(right));

  return (
    <section className="executive-spend-dashboard">
      <header className="executive-spend-heading">
        <div>
          <p className="brand-eyebrow">Executive spend intelligence</p>
          <h2>Current purchasing performance</h2>
        </div>
        <div className="executive-spend-actions">
          <span>
            Updated {new Date(dashboard.as_of).toLocaleString()} · refreshes
            every minute
          </span>
          <div>
            <Link className="brand-button" href="/analytics">
              View detailed analytics
            </Link>
            <button
              className="brand-button"
              disabled={downloading}
              onClick={() => void downloadExecutivePack()}
              type="button"
            >
              {downloading ? "Preparing Excel…" : "Download executive report"}
            </button>
          </div>
          {downloadMessage ? (
            <output className="executive-download-message">
              {downloadMessage}
            </output>
          ) : null}
        </div>
      </header>
      <div className="executive-spend-grid">
        <EntitySpendPanel
          items={dashboard.mtd_by_entity}
          subtitle={new Date(dashboard.month_start).toLocaleDateString(
            "en-US",
            { month: "long", year: "numeric" },
          )}
          title="MTD Spend by Entity"
        />
        <EntitySpendPanel
          items={dashboard.ytd_by_entity}
          subtitle={new Date(dashboard.year_start).getFullYear().toString()}
          title="YTD Spend by Entity"
        />
        <article className="executive-spend-card executive-best-sellers">
          <header>
            <div>
              <p className="brand-eyebrow">Month to date</p>
              <h3>Top 10 Best Sellers MTD</h3>
            </div>
          </header>
          {sellers.length ? (
            sellers.map(([currency, items]) => (
              <section key={currency}>
                <p className="executive-best-seller-currency">{currency}</p>
                <div>
                  {items.map((item) => (
                    <div
                      className="executive-best-seller-row"
                      key={`${currency}-${item.rank}-${item.product_code}`}
                    >
                      <b>{item.rank}</b>
                      <span>
                        <strong>{item.product_code}</strong>
                        <small>{item.product_name}</small>
                      </span>
                      <span>
                        <strong>{money(item.amount, currency)}</strong>
                        <small>
                          {Number(item.quantity).toLocaleString()} units
                        </small>
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            ))
          ) : (
            <p className="executive-spend-empty">
              No product sales have posted this month.
            </p>
          )}
        </article>
      </div>
    </section>
  );
}
