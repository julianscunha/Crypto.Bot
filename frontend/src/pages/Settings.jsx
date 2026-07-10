import { useEffect, useState, useRef } from "react";
import { usePolling } from "../hooks/usePolling";
import { api, ApiError } from "../api/client";
import { Panel } from "../components/Panel";
import { Badge } from "../components/Badge";

const KEY_LENGTH = 64;

const DEFAULT_PAIRS = [
  "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
  "ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","MATICUSDT",
  "LINKUSDT","LTCUSDT","UNIUSDT","ATOMUSDT","ETCUSDT",
  "XLMUSDT","NEARUSDT","ALGOUSDT","FILUSDT","VETUSDT",
  "SANDUSDT","MANAUSDT","AAVEUSDT","MKRUSDT","SHIBUSDT",
];

const KLINE_INTERVAL_FIELD = {
  key: "kline_interval",
  label: "Intervalo dos candles",
  type: "select",
  options: ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"],
  hint: "Timeframe de cada candlestick. 5m é o padrão. Requer reinicialização.",
};

// =====================================================
// GRUPOS DE PARÂMETROS
// =====================================================
//
// restartRequired: true em todos os grupos -- os agentes
// (RiskAgent, PositionManagerAgent, etc.) recebem TRADING_CONFIG/
// TRADE_MANAGEMENT_CONFIG/SIGNAL_QUALITY_CONFIG uma única vez, na
// inicialização do processo (initialize_agents() em
// apps/trader/runner.py). Esses dicts são "fotografias" estáticas
// do .env calculadas no import (core/config/trading_config.py etc),
// nunca relidas depois -- então qualquer campo salvo aqui só passa
// a valer depois de um restart manual do bot, mesmo que a API
// responda 200 imediatamente. Não é um valor arbitrário: reflete o
// comportamento real do backend, não uma suposição da UI.

const GROUPS = [
  {
    id: "risk",
    eyebrow: "Proteção de capital",
    title: "Gestão de risco",
    restartRequired: true,
    fields: [
      { key: "risk_per_trade_percent", label: "Risco por trade (%)", type: "float", min: 0.01, max: 100, hint: "Percentual do saldo arriscado em cada trade. 0.25% = R$0,025 em conta de R$10. Aumente para gerar ordens maiores e passar o tamanho mínimo da exchange." },
      { key: "max_open_positions", label: "Máx. posições abertas", type: "int", min: 1, max: 10, hint: "Número máximo de posições abertas ao mesmo tempo em todos os pares." },
      { key: "max_position_exposure_percent", label: "Exposição máx. por posição (%)", type: "float", min: 1, max: 100, hint: "Percentual máximo do saldo que uma única posição pode representar." },
      { key: "minimum_risk_reward_ratio", label: "Relação risco/retorno mínima", type: "float", min: 0.1, max: 10, hint: "Proporção mínima entre lucro potencial e perda potencial. 1.2 significa que o take profit deve ser pelo menos 1.2× a distância do stop loss. Com ATR TP=3.0 e SL=2.0, a relação é 1.5." },
    ],
  },
  {
    id: "limits",
    eyebrow: "Disjuntores",
    title: "Limites diários",
    restartRequired: true,
    fields: [
      { key: "enable_daily_trade_limit", label: "Ativar limite de trades diários", type: "bool", hint: "Para o bot após atingir o número máximo de trades no dia." },
      { key: "max_daily_trades", label: "Máx. trades por dia", type: "int", min: 1, max: 200, hint: "Número máximo de trades concluídos por dia. Reinicia à meia-noite." },
      { key: "enable_daily_loss_limit", label: "Ativar limite de perda diária", type: "bool", hint: "Para o trading se as perdas realizadas ultrapassarem o percentual configurado do saldo." },
      { key: "max_daily_loss_percent", label: "Perda diária máx. (%)", type: "float", min: 0.1, max: 100, hint: "Perda máxima realizada permitida por dia como percentual do saldo." },
      { key: "enable_drawdown_protection", label: "Ativar proteção de drawdown", type: "bool", hint: "Para o trading se a queda do pico ao vale ultrapassar o limite configurado." },
      { key: "maximum_daily_drawdown_percent", label: "Drawdown máx. (%)", type: "float", min: 0.1, max: 100, hint: "Queda máxima pico-a-vale permitida antes de suspender o trading." },
    ],
  },
  {
    id: "atr",
    eyebrow: "Motor de volatilidade",
    title: "ATR e multiplicadores",
    restartRequired: true,
    fields: [
      { key: "atr_period", label: "Período do ATR (candles)", type: "int", min: 1, max: 200, hint: "Número de candles usado para calcular o Average True Range (ATR). 14 é o padrão." },
      { key: "atr_stop_multiplier", label: "Multiplicador do stop loss", type: "float", min: 0.1, max: 10, hint: "Distância do stop = ATR × este valor. Ex: ATR=100, mult=2.0 → SL 200 pontos abaixo da entrada." },
      { key: "atr_take_profit_multiplier", label: "Multiplicador do take profit", type: "float", min: 0.1, max: 20, hint: "Distância do take profit = ATR × este valor. Deve ser maior que stop_mult × risco/retorno_mín para evitar bloqueio LOW_RR. Ex: SL=2.0, RR=1.2 → TP deve ser > 2.4." },
      { key: "atr_trailing_multiplier", label: "Multiplicador do trailing stop", type: "float", min: 0.1, max: 10, hint: "Distância do trailing stop = ATR × este valor. O stop sobe com o preço, travando lucros." },
      { key: "minimum_atr_percent", label: "ATR mínimo (%)", type: "float", min: 0, max: 10, hint: "ATR mínimo como percentual do preço. Sinais bloqueados quando a volatilidade está abaixo disso (ATR_NOT_READY). Use 0 para desativar." },
    ],
  },
  {
    id: "signal",
    eyebrow: "Filtros de entrada",
    title: "Qualidade do sinal",
    restartRequired: true,
    fields: [
      { key: "minimum_signal_strength", label: "Força mínima do sinal (0–1)", type: "float", min: 0, max: 1, hint: "Pontuação mínima de confiança que a estratégia deve produzir para o sinal prosseguir. 0.5 = 50% de confiança." },
      { key: "min_signal_confidence", label: "Confiança mínima do analista (0–1)", type: "float", min: 0, max: 1, hint: "Confiança mínima do agente analista. Filtra leituras de baixa qualidade antes que a estratégia seja executada." },
      { key: "enable_volatility_filter", label: "Ativar filtro de volatilidade", type: "bool", hint: "Bloqueia sinais quando a volatilidade do mercado está abaixo do limiar mínimo de ATR." },
      { key: "enable_ema_trend_filter", label: "Ativar filtro de tendência EMA", type: "bool", hint: "Permite sinais de COMPRA apenas quando a EMA rápida está acima da EMA lenta (tendência de alta confirmada)." },
      { key: "enable_market_regime_alignment", label: "Ativar alinhamento de regime", type: "bool", hint: "Aceita apenas sinais alinhados com o regime de mercado detectado (alta/baixa/lateral)." },
      { key: "enable_signal_cooldown", label: "Ativar cooldown de sinal", type: "bool", hint: "Impede múltiplos sinais do mesmo par dentro da janela de cooldown." },
      { key: "signal_cooldown_seconds", label: "Cooldown (segundos)", type: "int", min: 1, max: 3600, hint: "Segundos mínimos entre sinais para o mesmo par quando o cooldown está ativado." },
    ],
  },
  {
    id: "structure",
    eyebrow: "Price action",
    title: "Estrutura de mercado",
    restartRequired: true,
    fields: [
      { key: "structure_min_score", label: "Pontuação mínima de estrutura (0–3)", type: "float", min: 0, max: 3, hint: "Pontuação mínima de qualidade da estrutura. Pontuação = topos mais altos (1) + fundos mais altos (1) + impulso (1). 2.0 exige 2 dos 3 confirmados. Reduza para aceitar setups mais fracos." },
      { key: "structure_min_impulse_percent", label: "Impulso mínimo (%)", type: "float", min: 0, max: 5, hint: "Variação percentual mínima para contar como perna de impulso válida. Muito baixo = ruído; muito alto = perde setups válidos." },
      { key: "structure_enable_consolidation_filter", label: "Bloquear zonas de consolidação", type: "bool", hint: "Bloqueia sinais quando o preço está em consolidação estreita. Reduz entradas em falsos rompimentos." },
    ],
  },
  {
    id: "position",
    eyebrow: "Ciclo de vida do trade",
    title: "Gestão de posição",
    restartRequired: true,
    fields: [
      { key: "enable_trailing_stop", label: "Ativar trailing stop", type: "bool", hint: "Ativa um stop que sobe com o preço, travando lucros conforme o trade evolui." },
      { key: "enable_breakeven", label: "Ativar breakeven", type: "bool", hint: "Move o stop loss para o preço de entrada ao atingir o gatilho de breakeven, eliminando o risco de perda." },
      { key: "breakeven_trigger_percent", label: "Gatilho do breakeven (%)", type: "float", min: 0.01, max: 10, hint: "Percentual de lucro que aciona a movimentação do stop para o ponto de entrada. 0.5% = stop move para breakeven após 0.5% de ganho." },
      { key: "enable_dynamic_take_profit", label: "Ativar take profit dinâmico", type: "bool", hint: "Estende o alvo de take profit quando o preço se aproxima dele em regime de alta, deixando os vencedores correrem." },
      { key: "dynamic_take_profit_proximity_percent", label: "Proximidade do TP dinâmico (%)", type: "float", min: 50, max: 99, hint: "Quão próximo do alvo (em %) antes de acionar a extensão. 90 = estende quando está 90% do caminho até o alvo." },
    ],
  },
  {
    id: "exchange",
    eyebrow: "Formatação de ordens",
    title: "Precisão da exchange",
    restartRequired: true,
    fields: [
      { key: "quantity_precision", label: "Casas decimais da quantidade", type: "int", min: 0, max: 8, hint: "Número de casas decimais para a quantidade da ordem. BTCUSDT usa 5 na mainnet e 6 na testnet tipicamente." },
      { key: "price_precision", label: "Casas decimais do preço", type: "int", min: 0, max: 8, hint: "Número de casas decimais para os preços nas ordens OCO." },
      { key: "min_order_quantity", label: "Quantidade mínima de ordem", type: "float", min: 0, max: 1, hint: "Quantidade mínima absoluta. Ordens abaixo disso são bloqueadas antes de chegar à exchange." },
      { key: "min_order_notional", label: "Valor mínimo da ordem (R$)", type: "float", min: 0, max: 1000, hint: "Valor mínimo da ordem (quantidade × preço). Use 10 para Binance mainnet. Use 0 para desativar (testnet com saldo baixo)." },
    ],
  },
  {
    id: "simulation",
    eyebrow: "Apenas no modo Paper",
    title: "Simulação",
    restartRequired: true,
    fields: [
      { key: "enable_fee_simulation", label: "Simular taxas de negociação", type: "bool", hint: "Desconta taxas simuladas da Binance no PnL do paper trading para resultados realistas." },
      { key: "maker_fee_percent", label: "Taxa maker (%)", type: "float", min: 0, max: 1, hint: "Taxa para ordens limitadas (maker). Padrão Binance é 0.1% = 0.001." },
      { key: "enable_slippage_simulation", label: "Simular slippage", type: "bool", hint: "Aplica uma pequena variação de preço simulada nas entradas/saídas para refletir o impacto real no mercado." },
      { key: "taker_fee_percent", label: "Taxa taker (%)", type: "float", min: 0, max: 1, hint: "Taxa para ordens a mercado (taker). Padrão Binance é 0.1% = 0.001." },
    ],
  },
];

// =====================================================
// PÁGINA PRINCIPAL
// =====================================================

export function Settings() {
  const { data: settings, error, isLoading, refresh } = usePolling(api.getSettings, 15000);
  const handleSaved = () => {
    refresh();
    window.dispatchEvent(new Event("crypto-bot-settings-updated"));
  };

  return (
    <div className="settings">
      <header className="dashboard__header">
        <div>
          <span className="dashboard__eyebrow">Configuração</span>
          <h1 className="dashboard__title">Configurações</h1>
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
          <ParamsForm settings={settings} onSaved={handleSaved} />
        </div>
      )}
    </div>
  );
}

// =====================================================
// PAINEL DE MODO (3 opções: Paper / Live Testnet / Live Mainnet)
// =====================================================

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

function CredentialsPanel({ settings, onSaved }) {
  const [liveConfirmed, setLiveConfirmed] = useState(settings.live_trading_confirmed);
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [balance, setBalance] = useState(settings.account_balance ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
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
  }, [settings.live_trading_confirmed, settings.account_balance]);

  const apiKeyTouched = apiKey.length > 0;
  const secretKeyTouched = secretKey.length > 0;
  const balanceTouched = !isLive && String(balance) !== String(settings.account_balance ?? "");
  const apiKeyInvalid = apiKeyTouched && apiKey.length !== KEY_LENGTH;
  const secretKeyInvalid = secretKeyTouched && secretKey.length !== KEY_LENGTH;
  const canSave = !isSaving && !apiKeyInvalid && !secretKeyInvalid &&
    (apiKeyTouched || secretKeyTouched || liveConfirmed !== settings.live_trading_confirmed || balanceTouched);

  async function handleSave(e) {
    e.preventDefault();
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    const payload = { live_trading_confirmed: liveConfirmed };
    if (apiKeyTouched) payload.binance_api_key = apiKey;
    if (secretKeyTouched) payload.binance_secret_key = secretKey;
    if (balanceTouched) payload.account_balance = parseFloat(balance);
    try {
      await api.updateSettings(payload);
      setApiKey("");
      setSecretKey("");
      setSaveSuccess(true);
      onSaved();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Falha ao salvar.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleClear(field) {
    setIsSaving(true);
    const payload = field === "api_key" ? { binance_api_key: "" } : { binance_secret_key: "" };
    try { await api.updateSettings(payload); onSaved(); }
    catch (err) { setSaveError(err instanceof ApiError ? err.message : "Falha ao limpar."); }
    finally { setIsSaving(false); }
  }

  return (
    <Panel eyebrow="Conexão Binance" title="Credenciais da carteira">
      <p className="settings__intro">
        As chaves conectam à <strong>Binance Testnet</strong> ou <strong>mainnet</strong> conforme o modo.
        Após salvar, as chaves nunca são exibidas novamente.
      </p>
      <form className="credentials-form" onSubmit={handleSave}>

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
                    ? liveBalance !== null ? `$${liveBalance}` : "—"
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

        {saveError && <div className="form-message form-message--error">{saveError}</div>}
        {saveSuccess && <div className="form-message form-message--success">Salvo com sucesso.</div>}

        <div className="form-actions">
          <button type="submit" className="button button--primary" disabled={!canSave}>
            {isSaving ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </form>
    </Panel>
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

// =====================================================
// FORMULÁRIO UNIFICADO DE PARÂMETROS (pares, mercado e todos os grupos)
// =====================================================
//
// Um único estado, uma única barra de salvar (sticky, só aparece
// quando há alteração pendente) para TODOS os campos da tela --
// pares monitorados, intervalo de candles e todos os grupos de
// parâmetros. Sem modal de confirmação e sem restart automático do
// bot: o usuário decide quando reiniciar manualmente (reiniciar
// sozinho poderia interromper uma operação em andamento). A barra só
// mostra um aviso ("Requer reinicialização") quando o campo alterado
// de fato exige isso -- ver o comentário em cima de GROUPS.

function ParamsForm({ settings, onSaved }) {

  const buildValues = (s) => {
    const v = {
      symbols: s.symbols
        ? s.symbols.split(",").map(p => p.trim().toUpperCase()).filter(Boolean)
        : [],
      kline_interval: s.kline_interval ?? "5m",
    };
    GROUPS.forEach(g => g.fields.forEach(f => {
      v[f.key] = s[f.key] ?? "";
    }));
    return v;
  };

  // symbols/kline_interval também exigem restart -- ver
  // apps/trader/runner.py (subscription do WebSocket montada uma
  // única vez no startup a partir de settings.SYMBOLS/KLINE_INTERVAL).
  const restartRequiredKeys = new Set([
    "symbols",
    "kline_interval",
    ...GROUPS.filter(g => g.restartRequired).flatMap(g => g.fields.map(f => f.key)),
  ]);

  const [validPairs, setValidPairs] = useState(DEFAULT_PAIRS);
  const [pairsLoaded, setPairsLoaded] = useState(false);
  const [values, setValues] = useState(() => buildValues(settings));
  const [dirty, setDirty] = useState({});   // { key: true }
  const [isSaving, setIsSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    async function validatePairs() {
      try {
        const res = await fetch("https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT");
        const data = await res.json();
        const available = new Set(
          (data.symbols || [])
            .filter(s => s.status === "TRADING" && s.quoteAsset === "USDT")
            .map(s => s.symbol)
        );
        const valid = DEFAULT_PAIRS.filter(p => available.has(p));
        const extras = [...available]
          .filter(s => !DEFAULT_PAIRS.includes(s)).sort()
          .slice(0, DEFAULT_PAIRS.length - valid.length);
        setValidPairs([...valid, ...extras]);
      } catch {
        setValidPairs(DEFAULT_PAIRS);
      } finally {
        setPairsLoaded(true);
      }
    }
    validatePairs();
  }, []);

  useEffect(() => {
    setValues(buildValues(settings));
    setDirty({});
    setMsg(null);
  }, [settings]);

  const hasDirty = Object.keys(dirty).length > 0;
  const needsRestart = Object.keys(dirty).some(k => restartRequiredKeys.has(k));

  function handleChange(key, value) {
    setValues(v => ({ ...v, [key]: value }));
    setDirty(d => ({ ...d, [key]: true }));
    setMsg(null);
  }

  function togglePair(pair) {
    setValues(v => ({
      ...v,
      symbols: v.symbols.includes(pair)
        ? v.symbols.filter(p => p !== pair)
        : [...v.symbols, pair],
    }));
    setDirty(d => ({ ...d, symbols: true }));
    setMsg(null);
  }

  async function handleSave() {
    if (values.symbols.length === 0) {
      setMsg({ type: "error", text: "Selecione pelo menos um par." });
      return;
    }
    setIsSaving(true);
    setMsg(null);
    const payload = {};
    if (dirty.symbols) payload.symbols = values.symbols.join(",");
    if (dirty.kline_interval) payload.kline_interval = values.kline_interval;
    GROUPS.forEach(g => g.fields.forEach(f => {
      if (!dirty[f.key]) return;
      const raw = values[f.key];
      if (raw === "" || raw === null || raw === undefined) return;
      if (f.type === "int") payload[f.key] = parseInt(raw, 10);
      else if (f.type === "float") payload[f.key] = parseFloat(raw);
      else if (f.type === "bool") payload[f.key] = raw === true || raw === "true";
      else payload[f.key] = raw;
    }));
    try {
      const result = await api.updateSettings(payload);
      setMsg({
        type: "success",
        text: result.restart_triggered
          ? "Salvo — bot reiniciado."
          : needsRestart
            ? "Alterações salvas. Reinicie o bot para aplicar."
            : "Alterações salvas.",
      });
      setDirty({});
      onSaved();
    } catch (err) {
      setMsg({ type: "error", text: err instanceof ApiError ? err.message : "Falha ao salvar." });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <Panel eyebrow="Feed de dados" title="Pares monitorados e mercado" className="dashboard__span-2">
        <div className="pairs-market-layout">
          <div className="pairs-market-layout__pairs">
            <p className="settings__intro" style={{marginBottom: "0.75rem"}}>
              Selecione os pares a monitorar. Lista validada contra a Binance. Requer reinicialização.
            </p>
            {!pairsLoaded ? (
              <div className="loading-state">Validando pares…</div>
            ) : (
              <div className="pairs-grid">
                {validPairs.map(pair => (
                  <button
                    key={pair}
                    className={`pair-btn ${values.symbols.includes(pair) ? "pair-btn--active" : ""}`}
                    onClick={() => togglePair(pair)}
                    disabled={isSaving}
                  >
                    {pair.replace("USDT", "")}
                    <span className="pair-btn__quote">/USDT</span>
                  </button>
                ))}
              </div>
            )}
            {pairsLoaded && (
              <div className="pairs-summary">
                {values.symbols.length === 0
                  ? "Nenhum par selecionado"
                  : `${values.symbols.length} par${values.symbols.length > 1 ? "es" : ""}: ${values.symbols.join(", ")}`}
              </div>
            )}
          </div>
          <div className="pairs-market-layout__market">
            <p className="pairs-market-layout__market-title">Mercado</p>
            <ParamField
              field={KLINE_INTERVAL_FIELD}
              value={values.kline_interval}
              onChange={val => handleChange("kline_interval", val)}
              disabled={isSaving}
            />
          </div>
        </div>
      </Panel>

      {GROUPS.map(group => (
        <Panel key={group.id} eyebrow={group.eyebrow} title={group.title}>
          <div className="param-grid">
            {group.fields.map(f => (
              <ParamField
                key={f.key}
                field={f}
                value={values[f.key]}
                onChange={val => handleChange(f.key, val)}
                disabled={isSaving}
              />
            ))}
          </div>
        </Panel>
      ))}

      {/* Barra de salvar sticky -- única para toda a tela, só
          aparece quando há alteração pendente. */}
      <div className={`params-save-bar ${hasDirty ? "params-save-bar--visible" : ""}`}>
        <div className="params-save-bar__inner">
          {needsRestart && (
            <span className="restart-badge">⚠ Requer reinicialização do bot</span>
          )}
          {msg && (
            <span className={`params-save-bar__msg params-save-bar__msg--${msg.type}`}>
              {msg.text}
            </span>
          )}
          <button
            className="button button--primary"
            disabled={!hasDirty || isSaving}
            onClick={handleSave}
          >
            {isSaving ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </div>
    </>
  );
}

// =====================================================
// CAMPO DE PARÂMETRO
// =====================================================

function ParamField({ field, value, onChange, disabled }) {
  const timerRef = useRef(null);
  const [showHint, setShowHint] = useState(false);

  function handleLabelEnter() {
    timerRef.current = setTimeout(() => setShowHint(true), 400);
  }
  function handleLabelLeave() {
    clearTimeout(timerRef.current);
    setShowHint(false);
  }

  const controlId = `field-${field.key}`;

  return (
    <div className="param-field">
      <div className="param-field__label-row">
        <label
          className="param-field__label"
          htmlFor={controlId}
          onMouseEnter={handleLabelEnter}
          onMouseLeave={handleLabelLeave}
        >
          {field.label}
          <span className="param-field__hint-icon">?</span>
        </label>
        {showHint && <div className="param-hint" role="tooltip">{field.hint}</div>}
      </div>

      {field.type === "bool" ? (
        <label className="toggle">
          <input
            id={controlId}
            type="checkbox"
            checked={value === true || value === "true"}
            onChange={e => onChange(e.target.checked)}
            disabled={disabled}
          />
          <span>{value === true || value === "true" ? "Ativado" : "Desativado"}</span>
        </label>
      ) : field.type === "select" ? (
        <select id={controlId} className="input" value={value} onChange={e => onChange(e.target.value)} disabled={disabled}>
          {field.options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input
          id={controlId}
          type={field.type === "text" ? "text" : "number"}
          className="input"
          value={value}
          step={field.type === "float" ? "any" : 1}
          min={field.min}
          max={field.max}
          onChange={e => onChange(e.target.value)}
          disabled={disabled}
        />
      )}
    </div>
  );
}

