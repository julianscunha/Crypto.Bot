import { useState, useEffect } from "react";
import { usePolling } from "../hooks/usePolling";
import { api, ApiError } from "../api/client";
import { Panel } from "../components/Panel";
import { Badge } from "../components/Badge";

function useEstimate(type, days, symbolsKey = "", intervalKey = "") {
  const [estimate, setEstimate] = useState(null);

  useEffect(() => {
    api.getJobEstimate(type, days)
      .then(r => setEstimate(r))
      .catch(() => setEstimate(null));
  }, [type, days, symbolsKey, intervalKey]);

  return estimate;
}

// =====================================================
// PÁGINA DE FERRAMENTAS
// =====================================================

export function Tools() {
  const { data: settings, refresh: refreshSettings } = usePolling(api.getSettings, 15000);
  const [job, setJob] = useState(null);
  const [progress, setProgress] = useState(null);
  const [runnerRunning, setRunnerRunning] = useState(false);
  const [toast, setToast] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [optimizerDays, setOptimizerDays] = useState(90);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applyPreview, setApplyPreview] = useState(null);
  const [applyResult, setApplyResult] = useState(null);
  const [optimizerHistory, setOptimizerHistory] = useState([]);
  const [optimizerHistoryPage, setOptimizerHistoryPage] = useState(1);
  const [optimizerHistoryMeta, setOptimizerHistoryMeta] = useState({ total: 0, pages: 1 });
  const [backtestHistory, setBacktestHistory] = useState([]);
  const [backtestHistoryPage, setBacktestHistoryPage] = useState(1);
  const [backtestHistoryMeta, setBacktestHistoryMeta] = useState({ total: 0, pages: 1 });

  const settingsSignature = settings?.symbols ?? "";
  const intervalSignature = settings?.kline_interval ?? "";

  const estOptimizer30 = useEstimate("optimizer", 30, settingsSignature, intervalSignature);
  const estOptimizer60 = useEstimate("optimizer", 60, settingsSignature, intervalSignature);
  const estOptimizer90 = useEstimate("optimizer", 90, settingsSignature, intervalSignature);
  const estOptimizerSelected = useEstimate("optimizer", optimizerDays, settingsSignature, intervalSignature);
  const estBacktest = useEstimate("backtest", null, settingsSignature, intervalSignature);

  useEffect(() => {
    function handleSettingsUpdated() {
      refreshSettings();
    }

    window.addEventListener("crypto-bot-settings-updated", handleSettingsUpdated);
    return () => window.removeEventListener("crypto-bot-settings-updated", handleSettingsUpdated);
  }, [refreshSettings]);

  const optimizerEst = {
    30: estOptimizer30,
    60: estOptimizer60,
    90: estOptimizer90,
  };

  useEffect(() => {
    let interval;
    const isRunningJob = job?.status === "running";

    async function poll() {
      try {
        const [jobData, runnerData] = await Promise.all([
          api.getJobStatus(),
          api.getRunnerStatus(),
        ]);
        setJob(jobData);
        setRunnerRunning(runnerData.running);
        if (jobData.status === "running") {
          try {
            setProgress(await api.getJobProgress());
          } catch {}
        } else {
          setProgress(null);
        }
      } catch {}
    }

    poll();
    interval = setInterval(poll, isRunningJob ? 1500 : 5000);
    return () => clearInterval(interval);
  }, [job?.status, job?.type]);

  async function loadHistory(type, page) {
    try {
      const r = await api.getJobHistory(page, type);
      if (type === "optimizer") {
        setOptimizerHistory(r.items);
        setOptimizerHistoryMeta({ total: r.total, pages: r.pages });
        setOptimizerHistoryPage(page);
      } else {
        setBacktestHistory(r.items);
        setBacktestHistoryMeta({ total: r.total, pages: r.pages });
        setBacktestHistoryPage(page);
      }
    } catch {}
  }

  useEffect(() => {
    if (job?.status === "done" || job?.status === "error") {
      if (job.type === "optimizer") {
        loadHistory("optimizer", 1);
      } else if (job.type === "backtest") {
        loadHistory("backtest", 1);
      }
    }
  }, [job?.status, job?.type]);

  useEffect(() => {
    loadHistory("optimizer", 1);
    loadHistory("backtest", 1);
  }, []);

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  async function handleRun(type) {
    if (runnerRunning) {
      showToast("Pare o bot antes de rodar o optimizer ou backtest.");
      return;
    }

    setActionError(null);
    setApplyResult(null);
    setProgress(null);

    try {
      if (type === "optimizer") {
        await api.runOptimizer(optimizerDays);
      } else {
        await api.runBacktest();
      }
      setJob(await api.getJobStatus());
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Falha ao iniciar.");
    }
  }

  async function handleApplyClick() {
    try {
      const preview = await api.previewApply();
      setApplyPreview(preview);
      setShowApplyModal(true);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Falha ao carregar preview.");
    }
  }

  async function handleApplyConfirm() {
    setShowApplyModal(false);
    try {
      const result = await api.applyBestConfig();
      setApplyResult(result);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Falha ao aplicar.");
    }
  }

  const isRunningJob = job?.status === "running";
  const lastOptimizerHistory = optimizerHistory[0];
  const lastBacktestHistory = backtestHistory[0];

  return (
    <div className="settings">
      <header className="dashboard__header">
        <div>
          <span className="dashboard__eyebrow">Calibração</span>
          <h1 className="dashboard__title">Ferramentas</h1>
        </div>
      </header>

      {toast && <div className="tools-toast">{toast}</div>}

      <div className="settings__grid">
        {runnerRunning && !isRunningJob && (
          <div className="dashboard__span-2">
            <div className="tools-warning-bar">
              ⚠ O bot está em execução. Pare o bot antes de rodar o optimizer ou backtest.
            </div>
          </div>
        )}

        <Panel eyebrow="Calibração automática" title="Optimizer">
          <p className="settings__intro">
            Baixa dados reais da Binance, testa 24 combinações de TP/SL/trailing
            e salva a melhor configuração.
          </p>

          <div className="days-selector">
            <span className="days-selector__label">Período:</span>
            {[30, 60, 90].map(d => (
              <button
                key={d}
                className={`days-btn ${optimizerDays === d ? "days-btn--active" : ""}`}
                onClick={() => setOptimizerDays(d)}
                disabled={isRunningJob}
                title={optimizerEst[d]?.estimate_seconds ? formatElapsed(optimizerEst[d].estimate_seconds) : "Sem histórico"}
              >
                {d} dias
                {optimizerEst[d]?.estimate_seconds && (
                  <span className="days-btn__est">~{formatElapsed(optimizerEst[d].estimate_seconds)}</span>
                )}
              </button>
            ))}
          </div>

          {estOptimizerSelected?.estimate_seconds != null && (
            <p className="tool-est-time">
              Estimativa dinâmica: ~{formatElapsed(estOptimizerSelected.estimate_seconds)}
            </p>
          )}

          {estOptimizerSelected && (
            <p className="tool-est-meta">
              {estimateDescription(estOptimizerSelected)}
            </p>
          )}

          {lastOptimizerHistory && (
            <p className="tool-last-run">
              Última execução: {formatDate(lastOptimizerHistory.started_at)} — {formatElapsed(lastOptimizerHistory.elapsed_seconds)}
            </p>
          )}

          <div className="form-actions">
            <button
              className="button button--primary"
              disabled={isRunningJob || runnerRunning}
              onClick={() => handleRun("optimizer")}
            >
              {isRunningJob && job?.type === "optimizer" ? "Rodando…" : "▶ Executar Optimizer"}
            </button>
          </div>

          <JobHistoryBlock
            title="Histórico do optimizer"
            items={optimizerHistory}
            meta={optimizerHistoryMeta}
            page={optimizerHistoryPage}
            onPrev={() => loadHistory("optimizer", optimizerHistoryPage - 1)}
            onNext={() => loadHistory("optimizer", optimizerHistoryPage + 1)}
          />
        </Panel>

        <Panel eyebrow="Validação histórica" title="Backtest">
          <p className="settings__intro">
            Roda a estratégia atual sobre os datasets históricos e exibe métricas de desempenho.
          </p>

          {estBacktest?.estimate_seconds != null && (
            <p className="tool-est-time">
              Estimativa dinâmica: ~{formatElapsed(estBacktest.estimate_seconds)}
            </p>
          )}

          {estBacktest && (
            <p className="tool-est-meta">
              {estimateDescription(estBacktest)}
            </p>
          )}

          {lastBacktestHistory && (
            <p className="tool-last-run">
              Última execução: {formatDate(lastBacktestHistory.started_at)} — {formatElapsed(lastBacktestHistory.elapsed_seconds)}
            </p>
          )}

          <div className="form-actions">
            <button
              className="button button--primary"
              disabled={isRunningJob || runnerRunning}
              onClick={() => handleRun("backtest")}
            >
              {isRunningJob && job?.type === "backtest" ? "Rodando…" : "▶ Executar Backtest"}
            </button>
          </div>

          <JobHistoryBlock
            title="Histórico do backtest"
            items={backtestHistory}
            meta={backtestHistoryMeta}
            page={backtestHistoryPage}
            onPrev={() => loadHistory("backtest", backtestHistoryPage - 1)}
            onNext={() => loadHistory("backtest", backtestHistoryPage + 1)}
          />
        </Panel>

        {job && job.status !== "idle" && (
          <div className="dashboard__span-2">
            <Panel eyebrow="Execução atual" title={job.type === "optimizer" ? "Optimizer" : "Backtest"}>
              <JobStatus job={job} progress={progress} />

              {job.status === "done" && job.type === "optimizer" && !applyResult && (
                <div className="form-actions" style={{ marginTop: "1rem" }}>
                  <button className="button button--primary" onClick={handleApplyClick}>
                    Ver e aplicar melhores configurações
                  </button>
                </div>
              )}

              {applyResult && (
                <div className="form-message form-message--success" style={{ marginTop: "1rem" }}>
                  ✓ Aplicado: TP×{applyResult.config.atr_take_profit_multiplier} SL×{applyResult.config.atr_stop_multiplier} Trailing×{applyResult.config.atr_trailing_multiplier}
                </div>
              )}
            </Panel>
          </div>
        )}

        {actionError && (
          <div className="dashboard__span-2">
            <div className="form-message form-message--error" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>{actionError}</span>
              {actionError.includes("job em execução") && (
                <button
                  className="button button--ghost"
                  style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                  onClick={async () => {
                    try {
                      await api.resetJob();
                      setActionError(null);
                      setJob(await api.getJobStatus());
                    } catch {}
                  }}
                >
                  Forçar reset
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {showApplyModal && applyPreview && (
        <ApplyPreviewModal
          preview={applyPreview}
          onConfirm={handleApplyConfirm}
          onCancel={() => setShowApplyModal(false)}
        />
      )}
    </div>
  );
}

// =====================================================
// BLOCO DE HISTÓRICO
// =====================================================

function JobHistoryBlock({ title, items, meta, page, onPrev, onNext }) {
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: "1rem" }}>
      <p className="tool-last-run">{title}</p>
      <div className="job-history">
        {items.map((item, i) => (
          <HistoryItem key={i} item={item} />
        ))}
      </div>
      {meta.pages > 1 && (
        <div className="job-history__pagination">
          <button className="button button--ghost" disabled={page <= 1} onClick={onPrev}>
            ← Anterior
          </button>
          <span className="job-history__page">
            {page} / {meta.pages}
          </span>
          <button className="button button--ghost" disabled={page >= meta.pages} onClick={onNext}>
            Próximo →
          </button>
        </div>
      )}
    </div>
  );
}

// =====================================================
// ITEM DO HISTÓRICO
// =====================================================

function HistoryItem({ item }) {
  const isOk = item.status === "done";
  const typeLabel = item.type === "optimizer" ? "Optimizer" : "Backtest";
  const days = item.extra_args?.includes("--days")
    ? item.extra_args[item.extra_args.indexOf("--days") + 1]
    : null;
  const symbols = item.workload?.symbols;

  return (
    <div className="history-item">
      <div className="history-item__header">
        <span className="history-item__type">
          {typeLabel}{days ? ` · ${days}d` : ""}{symbols?.length ? ` · ${symbols.join(", ")}` : ""}
        </span>
        <Badge tone={isOk ? "positive" : "negative"}>{isOk ? "OK" : "Erro"}</Badge>
        <span className="history-item__meta">{formatDate(item.started_at)}</span>
        <span className="history-item__meta">{formatElapsed(item.elapsed_seconds)}</span>
      </div>

      {isOk && item.result_summary && Object.keys(item.result_summary).length > 0 && (
        <div className="history-item__summary">
          {item.type === "optimizer" && (
            <>
              <span>TP×{item.result_summary.tp} SL×{item.result_summary.sl} Trailing×{item.result_summary.trailing}</span>
              <span>Win {item.result_summary.winrate}%</span>
              <span>PnL {item.result_summary.pnl}</span>
              <span>Score {item.result_summary.score}</span>
            </>
          )}
          {item.type === "backtest" && (
            <>
              <span>Win {item.result_summary.winrate}%</span>
              <span>PnL {item.result_summary.pnl}</span>
              <span>{item.result_summary.total_trades} trades</span>
              <span>PF {item.result_summary.profit_factor}</span>
            </>
          )}
        </div>
      )}

      {!isOk && item.error && (
        <p className="history-item__error">{item.error}</p>
      )}
    </div>
  );
}

// =====================================================
// MODAL DE PREVIEW ANTES DE APLICAR
// =====================================================

function ApplyPreviewModal({ preview, onConfirm, onCancel }) {
  const { current, new: next } = preview;
  const changed = Object.keys(next).filter(k => current[k] !== next[k]);

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal">
        <h3 className="modal__title">Aplicar melhores configurações?</h3>
        <p className="modal__body">Alterações que serão aplicadas:</p>

        <div className="apply-preview">
          {["atr_take_profit_multiplier", "atr_stop_multiplier", "atr_trailing_multiplier"].map(k => {
            const label = {
              atr_take_profit_multiplier: "Take Profit ×",
              atr_stop_multiplier: "Stop Loss ×",
              atr_trailing_multiplier: "Trailing ×",
            }[k];
            const isChanged = current[k] !== next[k];
            return (
              <div key={k} className={`apply-preview__row ${isChanged ? "apply-preview__row--changed" : ""}`}>
                <span className="apply-preview__label">{label}</span>
                <span className="apply-preview__from">{current[k]}</span>
                <span className="apply-preview__arrow">{isChanged ? "→" : "="}</span>
                <span className="apply-preview__to" style={{ color: isChanged ? "var(--signal-positive)" : "var(--text-muted)" }}>{next[k]}</span>
              </div>
            );
          })}
        </div>

        {changed.length === 0 && (
          <p className="modal__body modal__body--muted">Nenhuma alteração — configuração atual já é a melhor.</p>
        )}

        <div className="modal__actions">
          <button type="button" className="button button--ghost" onClick={onCancel}>Cancelar</button>
          <button type="button" className="button button--primary" onClick={onConfirm} disabled={changed.length === 0}>
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}

// =====================================================
// STATUS DO JOB
// =====================================================

function JobStatus({ job, progress }) {
  const elapsed = job.elapsed_seconds;
  const statusLabel = { running: "⏳ Rodando…", done: "✓ Concluído", error: "✗ Erro" }[job.status] ?? job.status;
  const statusColor = { running: "#f0b429", done: "var(--signal-positive)", error: "var(--signal-negative)" }[job.status];
  const showRealProgress = job.status === "running" && progress?.total > 0;

  return (
    <div className="job-status">
      <div className="job-status__header">
        <span className="job-status__label" style={{ color: statusColor }}>{statusLabel}</span>
        {elapsed != null && <span className="job-status__elapsed">{formatElapsed(elapsed)}</span>}
      </div>
      {job.status === "running" && (
        showRealProgress
          ? <RealProgressBar progress={progress} />
          : <div className="progress-bar"><div className="progress-bar__fill progress-bar__fill--animated" /></div>
      )}
      {job.status === "error" && <div className="form-message form-message--error">{job.error}</div>}
      {job.status === "done" && job.result && <ResultTable job={job} />}
    </div>
  );
}

function RealProgressBar({ progress }) {
  const { current, total, percent, phase } = progress;
  return (
    <div className="real-progress">
      <div className="real-progress__bar">
        <div className="real-progress__fill" style={{ width: `${percent}%` }} />
      </div>
      <div className="real-progress__meta">
        <span className="real-progress__phase">{phase}</span>
        <span className="real-progress__count">{current}/{total} ({percent}%)</span>
      </div>
    </div>
  );
}

function ResultTable({ job }) {
  const r = job.result;
  if (!r) return null;
  if (job.type === "optimizer" && Array.isArray(r) && r.length > 0) {
    const best = r.reduce((a, b) => (b.score > a.score ? b : a), r[0]);
    const p = best.params || best;
    const m = best.metrics || {};
    return (
      <div className="result-table">
        <p className="result-table__title">Melhor combinação</p>
        <div className="result-table__grid">
          {[["Take Profit ×", p.atr_take_profit_multiplier], ["Stop Loss ×", p.atr_stop_multiplier], ["Trailing ×", p.atr_trailing_multiplier], ["Score", best.score?.toFixed(2)], ["Win Rate", `${((m.winrate || 0) * 100).toFixed(1)}%`], ["PnL", m.pnl?.toFixed(2)], ["Profit Factor", m.profit_factor?.toFixed(2)], ["Trades", m.total_trades]].map(([l, v]) => (
            <><span key={l + "l"} className="result-table__label">{l}</span><span key={l + "v"} className="result-table__value">{v ?? "—"}</span></>
          ))}
        </div>
      </div>
    );
  }
  if (job.type === "backtest" && r && typeof r === "object") {
    return (
      <div className="result-table">
        <p className="result-table__title">Resultado do backtest</p>
        <div className="result-table__grid">
          {[["Total trades", r.total_trades], ["Win Rate", `${((r.winrate || 0) * 100).toFixed(1)}%`], ["PnL", r.pnl?.toFixed(2)], ["Profit Factor", r.profit_factor?.toFixed(2)], ["Max Drawdown", r.max_drawdown?.toFixed(2)], ["Expectancy", r.expectancy?.toFixed(2)], ["Risco/Retorno", r.risk_reward?.toFixed(2)], ["Sharpe", r.sharpe_ratio?.toFixed(2)]].map(([l, v]) => (
            <><span key={l + "l"} className="result-table__label">{l}</span><span key={l + "v"} className="result-table__value">{v ?? "—"}</span></>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

// =====================================================
// HELPERS
// =====================================================

function estimateDescription(estimate) {
  if (!estimate?.profile || !estimate?.hardware) {
    return "";
  }

  const { profile, hardware, basis } = estimate;
  const source = basis === "history" ? "baseada em histórico" : "heurística";
  const memory = Number(hardware.memory_gb || 0).toFixed(1);

  return `${source} · ${profile.symbol_count} pares · ${profile.candles_per_symbol} candles/pare · ${profile.combination_count} combinações · ${hardware.cpu_count} CPUs · ${memory} GB RAM`;
}

function formatElapsed(seconds) {
  if (!seconds && seconds !== 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function formatDate(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}
