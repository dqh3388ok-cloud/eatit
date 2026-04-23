import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Loader2 } from "lucide-react";
import type { MetaReportListResponse } from "@eatit/shared-types";
import { getMetaReportList } from "@/api/metaReports";

const STATUS_LABEL: Record<string, string> = {
  generating: "生成中",
  ready: "就绪",
  failed: "失败",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function MetaReportListPage(): JSX.Element {
  const navigate = useNavigate();
  const query = useQuery<MetaReportListResponse>({
    queryKey: ["meta-reports", "list"],
    queryFn: () => getMetaReportList({ page: 1, page_size: 50 }),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <div className="eyebrow">07 · 综合分析</div>
        <h1
          className="h-serif"
          style={{
            fontSize: 42,
            lineHeight: 1.1,
            fontWeight: 400,
            margin: "10px 0 6px",
            color: "var(--ink-900)",
          }}
        >
          跨场综合分析
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "var(--ink-500)",
            maxWidth: 620,
            lineHeight: 1.6,
          }}
        >
          把多场面试合在一起看趋势、反复出现的短板与已经取得的进步。可以在「面试记录」页面触发生成。
        </p>
      </div>

      {query.isLoading ? (
        <div
          className="ds-card"
          style={{
            padding: 22,
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "var(--ink-500)",
            fontSize: 13.5,
          }}
        >
          <Loader2 size={14} className="spin" />
          加载中...
        </div>
      ) : null}

      {query.isError ? (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "var(--r-md)",
            background: "var(--warn-soft)",
            color: "var(--warn)",
            border: "1px solid var(--warn)",
            fontSize: 13,
          }}
        >
          加载失败:
          {query.error instanceof Error ? query.error.message : "请检查后端连接"}
        </div>
      ) : null}

      {query.data && query.data.items.length === 0 ? (
        <div
          className="ds-card"
          style={{
            padding: 22,
            textAlign: "center",
            color: "var(--ink-500)",
            fontSize: 13.5,
          }}
        >
          还没有生成过综合分析。去「面试记录」页点击「生成综合分析」。
        </div>
      ) : null}

      {query.data && query.data.items.length > 0 ? (
        <ul
          className="ds-card"
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {query.data.items.map((item, index) => (
            <li
              key={item.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/meta-report/${item.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`/meta-report/${item.id}`);
                }
              }}
              style={{
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                gap: 16,
                cursor: "pointer",
                borderTop: index === 0 ? "none" : "1px solid var(--line)",
                transition: "background 120ms ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--bg-sunken)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: "var(--ink-900)",
                  }}
                >
                  {formatDate(item.created_at)}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--ink-500)",
                    marginTop: 4,
                  }}
                >
                  <span className="mono">{item.id.slice(0, 8)}</span>
                  <span style={{ margin: "0 6px", color: "var(--ink-300)" }}>
                    ·
                  </span>
                  覆盖 {item.session_count} 场
                </div>
              </div>
              <span className="ds-tag">
                {STATUS_LABEL[item.status] ?? item.status}
              </span>
              <ChevronRight size={16} color="var(--ink-400)" />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
