import { useEffect, useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { api, ApiError } from "../api/client";
import { Panel } from "../components/Panel";
import { Badge } from "../components/Badge";
import { formatUsd } from "../lib/format";

const KEY_LENGTH = 64;

// =====================================================
// PÁGINA PRINCIPAL
// =====================================================

export function Operation() {
  const { data: settings, error, isLoading, refresh } = usePolling(api.getSettings, 15000);
  const handleSaved = () => {
    refresh();
    window.dispatchEvent(new Event("crypto-bot-settings-updated"));
  };

  return (
    <div className="settings">
      <header className="dashboard__header">
        <div>
          <span className="dashboard__eyebrow">Operação</span>
          <h1 className="dashboard__title">Operação</h1>
        </div>
      </header>

      {isLoading && !settings && <div className="loading-state">Carregando configurações…</div>}

      {error && !settings && (
        <div className="error-state">
          <h2>Não foi possível conectar à API</h2>
          <p>{error instanceof ApiError ? error.message : "Ocorreu um erro inesperado."}</p>
        </div>
      )}

      {settings && (
        <div className="settings__grid">
          <ModePanel settings={settings} onSaved={handleSaved} />
          <CredentialsPanel settings={settings} onSaved={handleSaved} />
        </div>
      )}
    </div>
  );
}

// =====================================================
// PAINEL DE MODO (3 opções: Paper / Live Testnet / Live Mainnet)
// =====================================================
//
// Trocar de modo é uma ação imediata (dispara restart do bot assim
// que confirmada em modal), não um campo de formulário acumulável --
// por isso fica fora da barra de salvar sticky do CredentialsPanel
// abaixo, que junta várias edições antes de enviar.

const MODES = [
  {
    id: "paper",
    label: "Paper",
    description: "Simulado — nenhuma ordem real é enviada. Ideal para testes sem risco.",
    danger: false,
    requiresConfirmedLive: false,
    testnet: null,
  },
  {
    id: "live_testnet",
    label: "Live Testnet",
    description: "Ordens reais na Binance Testnet com dinheiro fictício. Valida o fluxo completo sem risco.",
    danger: false,
    requiresConfirmedLive: true,
    testnet: true,
  },
  {
    id: "live_mainnet",
    label: "Live Mainnet",
    description: "Ordens reais na Binance com dinheiro real. Use com cautela.",
    danger: true,
    requiresConfirmedLive: true,
    testnet: false,
  },
];

function currentModeId(settings) {
  if (settings.mode !== "live") return "paper";
  return settings.binance_testnet ? "live_testnet" : "live_mainnet";
}

function ModePanel({ settings, onSaved }) {
  const [pending, setPending] = useState(null);
  const [isSwitching, setIsSwitching] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const current = currentModeId(settings);
  const canUseLive = settings.live_trading_available;

  function handleSelect(modeObj) {
    if (modeObj.id === current || isSwitching) return;
    if (modeObj.requiresConfirmedLive && !canUseLive) return;
    setError(null);
    setSuccess(null);
    setPending(modeObj);
  }

  async function handleConfirm() {
    const modeObj = pending;
    setPending(null);
    setIsSwitching(true);

    const payload =
      modeObj.id === "paper"
        ? { mode: "paper" }
        : { mode: "live", binance_testnet: modeObj.testnet };

    try {
      const result = await api.updateSettings(payload);
      setSuccess(result.restart_triggered ? "Modo alterado. Bot reiniciado." : "Modo alterado.");
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao trocar modo.");
    } finally {
      setIsSwitching(false);
    }
  }

  return (
    <Panel eyebrow="Modo de operação" title="Modo de execução">
      <div className="mode-row">
        {MODES.map((m) => {
          const isActive = m.id === current;
          const isLocked = m.requiresConfirmedLive && !canUseLive;
          return (
            <ModeOption
              key={m.id}
              mode={m}
              active={isActive}
              locked={isLocked}
              disabled={isSwitching}
              onSelect={() => handleSelect(m)}
            />
          );
        })}
      </div>

      {!canUseLive && (
        <p className="form-message form-message--muted">
          Para habilitar os modos Live, vá em <strong>Credenciais</strong>: configure as chaves e marque "Confirmar trading real".
        </p>
      )}

      {isSwitching && <div className="form-message">Trocando modo e reiniciando…</div>}
      {error && <div className="form-message form-message--error">{error}</div>}
      {success && <div className="form-message form-message--success">{success}</div>}

      {pending && (
        <ModeConfirmModal
          mode={pending}
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      )}
    </Panel>
  );
}

function ModeOption({ mode, active, locked, disabled, onSelect }) {
  const className = [
    "mode-row__option",
    active ? "mode-row__option--active" : "",
    locked ? "mode-row__option--disabled" : "mode-row__option--selectable",
    mode.danger ? "mode-row__option--danger" : "",
  ].filter(Boolean).join(" ");

  return (
    <button type="button" className={className} onClick={onSelect} disabled={disabled || locked}>
      <div className="mode-row__option-head">
        <span className="mode-row__name">{mode.label}</span>
        {active && <Badge tone="positive">Ativo</Badge>}
        {!active && locked && <Badge tone="neutral">Bloqueado</Badge>}
        {!active && !locked && mode.danger && <Badge tone="negative">⚠ Real</Badge>}
      </div>
      <p className="mode-row__desc">{mode.description}</p>
    </button>
  );
}

function ModeConfirmModal({ mode, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal">
        <h3 className="modal__title">Trocar para {mode.label}?</h3>
        <p className="modal__body">
          {mode.id === "paper" && "O bot voltará para simulação. Nenhuma ordem real será enviada. O bot será reiniciado."}
          {mode.id === "live_testnet" && "O bot passará a colocar ordens reais na Binance Testnet (dinheiro fictício). O bot será reiniciado."}
          {mode.id === "live_mainnet" && <><strong>Atenção: ordens reais na Binance com dinheiro real.</strong> O bot será reiniciado imediatamente.</>}
        </p>
        <p className="modal__body modal__body--muted">Bloqueado se houver alguma posição aberta.</p>
        <div className="modal__actions">
          <button type="button" className="button button--ghost" onClick={onCancel}>Cancelar</button>
          <button
            type="button"
            className={mode.danger ? "button button--danger" : "button button--primary"}
            onClick={onConfirm}
          >
            {mode.danger ? `Confirmar — usar ${mode.label}` : `Trocar para ${mode.label}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// =====================================================
// PAINEL DE CREDENCIAIS
// =====================================================
//
// Mesmo padrão de barra de salvar sticky do ParamsForm (Settings.jsx):
// acumula edições em `dirty` e só mostra o botão/barra quando há algo
// pendente, em vez do botão estático que existia antes.

function CredentialsPanel({ settings, onSaved }) {
  const [liveConfirmed, setLiveConfirmed] = useState(settings.live_trading_confirmed);
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [balance, setBalance] = useState(settings.account_balance ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [liveBalance, setLiveBalance] = useState(null);
  const [liveBalanceSource, setLiveBalanceSource] = useState(null);
  const [liveBalanceError, setLiveBalanceError] = useState(null);

  const isLive = settings.mode === "live";

  // Busca saldo real da Binance quando em LIVE
  useEffect(() => {
    if (!isLive) { setLiveBalance(null); setLiveBalanceSource(null); setLiveBalanceError(null); return; }
    async function fetchLive() {
      try {
        const r = await api.getLiveBalance();
        setLiveBalance(r.balance);
        setLiveBalanceSource(r.source);
        setLiveBalanceError(r.error);
      } catch {
        setLiveBalanceError("Erro ao buscar saldo.");
      }
    }
    fetchLive();
    const i = setInterval(fetchLive, 30000);
    return () => clearInterval(i);
  }, [isLive]);

  useEffect(() => {
    setLiveConfirmed(settings.live_trading_confirmed);
    setBalance(settings.account_balance ?? "");
    setApiKey("");
    setSecretKey("");
    setMsg(null);
  }, [settings]);

  const apiKeyTouched = apiKey.length > 0;
  const secretKeyTouched = secretKey.length > 0;
  const balanceTouched = !isLive && String(balance) !== String(settings.account_balance ?? "");
  const liveConfirmedTouched = liveConfirmed !== settings.live_trading_confirmed;
  const apiKeyInvalid = apiKeyTouched && apiKey.length !== KEY_LENGTH;
  const secretKeyInvalid = secretKeyTouched && secretKey.length !== KEY_LENGTH;

  const hasDirty = apiKeyTouched || secretKeyTouched || liveConfirmedTouched || balanceTouched;
  const canSave = hasDirty && !isSaving && !apiKeyInvalid && !secretKeyInvalid;

  async function handleSave() {
    setIsSaving(true);
    setMsg(null);
    const payload = { live_trading_confirmed: liveConfirmed };
    if (apiKeyTouched) payload.binance_api_key = apiKey;
    if (secretKeyTouched) payload.binance_secret_key = secretKey;
    if (balanceTouched) payload.account_balance = parseFloat(balance);
    try {
      await api.updateSettings(payload);
      setApiKey("");
      setSecretKey("");
      setMsg({ type: "success", text: "Alterações salvas." });
      onSaved();
    } catch (err) {
      setMsg({ type: "error", text: err instanceof ApiError ? err.message : "Falha ao salvar." });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleClear(field) {
    setIsSaving(true);
    const payload = field === "api_key" ? { binance_api_key: "" } : { binance_secret_key: "" };
    try { await api.updateSettings(payload); onSaved(); }
    catch (err) { setMsg({ type: "error", text: err instanceof ApiError ? err.message : "Falha ao limpar." }); }
    finally { setIsSaving(false); }
  }

  return (
    <>
      <Panel eyebrow="Conexão Binance" title="Credenciais da carteira">
        <p className="settings__intro">
          As chaves conectam à <strong>Binance Testnet</strong> ou <strong>mainnet</strong> conforme o modo.
          Após salvar, as chaves nunca são exibidas novamente.
        </p>
        <div className="credentials-form">

          <div className="balance-row">
            {/* Esquerda — saldo manual */}
            <div className="balance-row__col">
              <div className="field__label-row">
                <label className="field__label">Saldo da conta (USDT)</label>
                <Badge tone="neutral">Manual</Badge>
              </div>
              <input
                type="number"
                className="input"
                value={balance}
                step="0.01"
                min="0"
                onChange={e => setBalance(e.target.value)}
                disabled={isSaving || isLive}
                placeholder="Ex: 100.00"
              />
              {isLive && (
                <span className="field__hint field__hint--info">
                  🔒 Travado em modo LIVE. Edite em modo Paper.
                </span>
              )}
            </div>

            {/* Direita — saldo real Binance */}
            <div className="balance-row__col balance-row__col--auto">
              <div className="field__label-row">
                <label className="field__label">Dados da conta</label>
                <Badge tone={isLive ? "positive" : "neutral"}>
                  {isLive ? (settings.binance_testnet ? "TESTNET" : "MAINNET") : "PAPER"}
                </Badge>
              </div>
              <div className="balance-auto-info">
                <div className="balance-auto-info__item">
                  <span className="balance-auto-info__label">Saldo disponível</span>
                  <span className="balance-auto-info__value">
                    {isLive
                      ? liveBalance !== null ? formatUsd(liveBalance) : "—"
                      : "—"}
                  </span>
                </div>
                <div className="balance-auto-info__item">
                  <span className="balance-auto-info__label">Fonte</span>
                  <span className="balance-auto-info__value">
                    {isLive
                      ? liveBalanceSource === "binance_testnet"
                        ? "Binance Testnet"
                        : liveBalanceSource === "binance_mainnet"
                          ? "Binance Mainnet"
                          : "Binance API"
                      : "Configuração manual"}
                  </span>
                </div>
                <div className="balance-auto-info__item">
                  <span className="balance-auto-info__label">Atualizado</span>
                  <span className="balance-auto-info__value">
                    {isLive ? "A cada 30s" : "—"}
                  </span>
                </div>
                {liveBalanceError && (
                  <span className="field__hint field__hint--error" style={{fontSize:"0.7rem"}}>
                    ⚠ {liveBalanceError}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="field-row">
            <label className="toggle">
              <input type="checkbox" checked={liveConfirmed} onChange={e => setLiveConfirmed(e.target.checked)} />
              <span>Confirmar trading real <span className="field__hint--muted">(obrigatório para desbloquear os modos Live)</span></span>
            </label>
          </div>

          <div className="credentials-fields-row">
            <CredentialField label="API key" value={apiKey} onChange={setApiKey}
              isSet={settings.binance_api_key_set} masked={settings.binance_api_key_masked}
              invalid={apiKeyInvalid} onClear={() => handleClear("api_key")} disabled={isSaving} />
            <CredentialField label="API secret" value={secretKey} onChange={setSecretKey}
              isSet={settings.binance_secret_key_set} masked={settings.binance_secret_key_masked}
              invalid={secretKeyInvalid} onClear={() => handleClear("secret_key")} disabled={isSaving} />
          </div>
        </div>
      </Panel>

      {/* Barra de salvar sticky -- mesmo padrão do ParamsForm em
          Settings.jsx: só aparece quando há alteração pendente. */}
      <div className={`params-save-bar ${hasDirty ? "params-save-bar--visible" : ""}`}>
        <div className="params-save-bar__inner">
          {msg && (
            <span className={`params-save-bar__msg params-save-bar__msg--${msg.type}`}>
              {msg.text}
            </span>
          )}
          <button
            className="button button--primary"
            disabled={!canSave}
            onClick={handleSave}
          >
            {isSaving ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </div>
    </>
  );
}

function CredentialField({ label, value, onChange, isSet, masked, invalid, onClear, disabled }) {
  return (
    <div className="field">
      <div className="field__label-row">
        <label className="field__label">{label}</label>
        {isSet ? <Badge tone="positive">Configurada</Badge> : <Badge tone="neutral">Não configurada</Badge>}
      </div>
      <div className="field__control-row">
        <input
          type="password"
          className={`input mono ${invalid ? "input--invalid" : ""}`}
          placeholder={isSet ? masked : "Cole a chave de 64 caracteres"}
          value={value}
          onChange={e => onChange(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          disabled={disabled}
        />
        {isSet && (
          <button type="button" className="button button--ghost" onClick={onClear} disabled={disabled}>
            Limpar
          </button>
        )}
      </div>
      {invalid && (
        <span className="field__hint field__hint--error">Deve ter exatamente {KEY_LENGTH} caracteres.</span>
      )}
    </div>
  );
}
