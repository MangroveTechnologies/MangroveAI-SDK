import { operationMetadata, type Operation, type Operations, type CoreModels } from './contract.generated.js';

export type { Operation, Operations, CoreModels, OracleModels } from './contract.generated.js';

export class ConfigurationError extends Error { override name = 'ConfigurationError'; }
export class MalformedResponseError extends Error { override name = 'MalformedResponseError'; }
export class RequestTimeoutError extends Error { override name = 'RequestTimeoutError'; }
export class RequestAbortedError extends Error { override name = 'RequestAbortedError'; }
export class NetworkError extends Error { override name = 'NetworkError'; }

export class APIError extends Error {
  override name = 'APIError';
  declare readonly response: unknown;
  declare readonly headers: Readonly<Record<string, string>>;
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly correlationId?: string,
    readonly retryAfter?: string,
    response?: unknown,
    headers: Readonly<Record<string, string>> = {},
  ) {
    super(message);
    Object.defineProperties(this, { response: { value: response }, headers: { value: headers } });
  }
  toJSON(): Record<string, unknown> {
    return { name: this.name, status: this.status, code: this.code, message: this.message,
      correlationId: this.correlationId, retryAfter: this.retryAfter };
  }
}

export interface ClientOptions {
  apiKey?: string | undefined;
  baseUrl?: string | undefined;
  environment?: 'prod' | 'dev' | 'local';
  timeoutMs?: number;
  maxResponseBytes?: number;
  fetch?: typeof globalThis.fetch;
}

export interface RequestControls {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export type RequestOptions<K extends Operation> = Operations[K]['input'] & RequestControls;
type Input = { path?: Record<string, unknown>; query?: Record<string, unknown>;
  headers?: Record<string, string>; body?: unknown; signal?: AbortSignal; timeoutMs?: number };
type Metadata = { method: string; path: string; required: Record<string, readonly string[]>;
  bodyRequired: boolean; authenticated: boolean; queryFormats: Record<string, string> };

export interface UsageMetrics {
  conversations_count?: number | null;
  messages_count?: number | null;
  estimated_tokens?: number | null;
  strategies_count?: number | null;
  backtests_count?: number | null;
  token_breakdown?: Record<string, unknown> | null;
  tool_calls?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
  nextOffset: number | null;
}

export interface SignalListOptions extends RequestControls {
  limit?: number;
  offset?: number;
  category?: string;
  regime_direction?: string;
  role?: string;
}

export interface PollOptions extends RequestControls {
  pollIntervalMs?: number;
}

export interface BacktestStatus {
  backtest_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  [key: string]: unknown;
}

type WorkflowName = { [K in Operation]: K extends `POST /api/v1/strategy-workflow/${infer N}` ? N : never }[Operation];
type WorkflowOperation<N extends WorkflowName> = Extract<Operation, `POST /api/v1/strategy-workflow/${N}`>;
type Camel<S extends string> = S extends `${infer A}_${infer B}` ? `${A}${Capitalize<Camel<B>>}` : S;
export type StrategyWorkflow = {
  [N in WorkflowName as Camel<N>]: (
    options: RequestOptions<WorkflowOperation<N>>,
  ) => Promise<Operations[WorkflowOperation<N>]['output']>;
};

function pause(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(new RequestAbortedError('Request was cancelled')); return; }
    const onAbort = (): void => { clearTimeout(timer); signal?.removeEventListener('abort', onAbort); reject(new RequestAbortedError('Request was cancelled')); };
    const timer = setTimeout(() => { signal?.removeEventListener('abort', onAbort); resolve(); }, ms);
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function positive(value: number, name: string): number {
  if (!Number.isSafeInteger(value) || value <= 0) throw new ConfigurationError(`${name} must be a positive integer`);
  return value;
}

function environmentVariables(): Record<string, string | undefined> {
  return (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
}

type Secrets = string | readonly string[] | undefined;

function credentialField(name: string): boolean {
  return /authorization|cookie|password|(?:api|private)[_-]?key|(?:access|refresh|firebase|csrf|session|oauth|bearer)[_-]?token|secret|seed[_-]?phrase|wallet[_-]?seed|signature/i.test(name);
}

function safeString(value: unknown, secrets: Secrets, fallback: string, maxLength = 512): string {
  if (typeof value !== 'string') return fallback;
  let result = value;
  for (const secret of typeof secrets === 'string' ? [secrets] : secrets ?? []) {
    if (secret) result = result.split(secret).join('[redacted]');
  }
  return result.replace(/Bearer\s+\S+/gi, 'Bearer [redacted]')
    .replace(/((?:api[_-]?key|authorization|refresh[_-]?token|cookie)\s*[:=]\s*)[^\s,;]+/gi, '$1[redacted]')
    .replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, maxLength);
}

function errorEnvelope(value: unknown, secrets: Secrets): unknown {
  // Preserve machine-readable decisions without making credentials part of errors.
  let raw = JSON.stringify(value, (key, item: unknown) => {
    if (credentialField(key)) return '[redacted]';
    return typeof item === 'string' ? safeString(item, secrets, '', item.length) : item;
  });
  for (const secret of typeof secrets === 'string' ? [secrets] : secrets ?? []) {
    if (raw !== undefined && secret) raw = raw.split(JSON.stringify(secret).slice(1, -1)).join('[redacted]');
  }
  return raw === undefined ? undefined : JSON.parse(raw) as unknown;
}

function requestSecrets(apiKey: string | undefined, headers: Headers, body: string | undefined): string[] {
  const secrets = apiKey ? [apiKey] : [];
  for (const [key, value] of headers) {
    if (credentialField(key)) {
      secrets.push(value);
      if (key === 'cookie') for (const cookie of value.split(';')) {
        const separator = cookie.indexOf('=');
        if (separator !== -1) secrets.push(cookie.slice(separator + 1).trim());
      }
    }
  }
  const pending: unknown[] = body === undefined ? [] : [JSON.parse(body) as unknown];
  while (pending.length) {
    const current = pending.pop();
    if (current === null || typeof current !== 'object') continue;
    for (const [key, value] of Object.entries(current)) {
      if (typeof value === 'string' && credentialField(key)) secrets.push(value);
      else if (value !== null && typeof value === 'object') pending.push(value);
    }
  }
  return secrets.filter(Boolean).sort((a, b) => b.length - a.length);
}

function page<T>(value: unknown, itemKey: string, offset: number, requestedLimit: number): Page<T> {
  if (!object(value) || !Array.isArray(value[itemKey])) throw new MalformedResponseError('Expected a paginated result');
  const items = value[itemKey] as T[];
  const number = (name: string, fallback: number): number => {
    const result = value[name] ?? fallback;
    if (typeof result !== 'number' || !Number.isSafeInteger(result) || result < 0) {
      throw new MalformedResponseError(`Invalid page ${name}`);
    }
    return result;
  };
  const actualOffset = number('offset', offset);
  const limit = number('limit', requestedLimit);
  const total = number('total', actualOffset + items.length);
  if (actualOffset !== offset || total < actualOffset + items.length) throw new MalformedResponseError('Page bounds contradict the requested offset or total');
  const explicitMore = value['has_more'];
  if (explicitMore !== undefined && typeof explicitMore !== 'boolean') throw new MalformedResponseError('Invalid has_more');
  const hasMore = explicitMore ?? actualOffset + items.length < total;
  if (!hasMore && actualOffset + items.length < total) throw new MalformedResponseError('Page ended before its reported total');
  const next = Object.hasOwn(value, 'next_offset') ? value['next_offset'] : (hasMore ? actualOffset + items.length : null);
  if (hasMore && (typeof next !== 'number' || !Number.isSafeInteger(next) || next <= actualOffset || items.length === 0)) {
    throw new MalformedResponseError('Page continuation did not advance');
  }
  return { items, total, offset: actualOffset, limit, hasMore, nextOffset: hasMore ? next as number : null };
}

export class MangroveAI {
  readonly baseUrl: string;
  readonly timeoutMs: number;
  #apiKey: string | undefined;
  private readonly fetcher: typeof globalThis.fetch;
  private readonly maxResponseBytes: number;

  constructor(options: ClientOptions = {}) {
    if (typeof window !== 'undefined') throw new ConfigurationError('Use the API-key client in server-side code');
    const env = environmentVariables();
    this.#apiKey = options.apiKey ?? env['MANGROVE_API_KEY'];
    if (this.#apiKey !== undefined && (typeof this.#apiKey !== 'string' || !this.#apiKey || /[^\x21-\x7e]/.test(this.#apiKey))) {
      throw new ConfigurationError('apiKey must be a nonempty ASCII token without whitespace');
    }
    const environment = options.environment ?? env['MANGROVE_ENVIRONMENT'] ?? (this.#apiKey?.startsWith('dev_') ? 'dev' : this.#apiKey?.startsWith('local_') ? 'local' : 'prod');
    if (!['prod', 'dev', 'local'].includes(environment)) throw new ConfigurationError('environment must be prod, dev or local');
    const configured = options.baseUrl ?? env['MANGROVE_BASE_URL'];
    if ((environment === 'dev' || this.#apiKey?.startsWith('dev_')) && !configured) throw new ConfigurationError('Development requires an explicit baseUrl or MANGROVE_BASE_URL');
    const raw = configured ?? (environment === 'local' ? 'http://localhost:5001' : 'https://api.mangrovedeveloper.ai');
    let origin: URL;
    try { origin = new URL(raw); } catch { throw new ConfigurationError('baseUrl must be an absolute HTTP(S) API origin'); }
    if (origin.username || origin.password || origin.search || origin.hash) throw new ConfigurationError('baseUrl cannot contain credentials, query or fragment');
    const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname);
    if (origin.protocol !== 'https:' && !(origin.protocol === 'http:' && loopback)) throw new ConfigurationError('baseUrl requires HTTPS except for loopback testing');
    if (!['', '/', '/api/v1', '/api/v1/', '/api/v2', '/api/v2/'].includes(origin.pathname)) {
      throw new ConfigurationError('baseUrl must be an API origin or a v1/v2 base URL');
    }
    this.baseUrl = origin.origin;
    this.timeoutMs = positive(options.timeoutMs ?? 30_000, 'timeoutMs');
    this.maxResponseBytes = positive(options.maxResponseBytes ?? 8 * 1024 * 1024, 'maxResponseBytes');
    this.fetcher = options.fetch ?? globalThis.fetch;
    if (!this.fetcher) throw new ConfigurationError('This runtime needs fetch support');
  }

  async request<K extends Operation>(operation: K, options: RequestOptions<K>): Promise<Operations[K]['output']> {
    if (typeof operation !== 'string' || !Object.hasOwn(operationMetadata, operation)) throw new ConfigurationError('Operation is absent from the reviewed contract');
    if (!object(options)) throw new ConfigurationError('Request options must be an object');
    const metadata: Metadata | undefined = operationMetadata[operation];
    if (!metadata) throw new ConfigurationError('Operation is absent from the reviewed contract');
    const input = options as Input;
    if (metadata.authenticated && !this.#apiKey) throw new ConfigurationError('This operation requires an API credential');
    if (input.signal?.aborted) throw new RequestAbortedError('Request was cancelled');
    if (metadata.bodyRequired && input.body === undefined) throw new ConfigurationError('This operation requires a request body');
    const headers = new Headers({ Accept: 'application/json' });
    for (const [key, value] of Object.entries(input.headers ?? {})) {
      if (['authorization', 'host', 'content-length'].includes(key.toLowerCase())) throw new ConfigurationError('A protected header cannot be overridden');
      try { headers.set(key, value); } catch { throw new ConfigurationError('A request header is invalid'); }
    }
    if (this.#apiKey) headers.set('Authorization', `Bearer ${this.#apiKey}`);
    for (const [group, keys] of Object.entries(metadata.required)) {
      for (const key of keys) {
        const value = group === 'headers' ? headers.get(key) : input[group as 'path' | 'query']?.[key];
        if (value === undefined || value === null || value === '') throw new ConfigurationError(`Missing required ${group} parameter: ${key}`);
      }
    }
    const path = metadata.path.replace(/\{([^}]+)\}/g, (_, name: string) => {
      const value = input.path?.[name];
      if ((typeof value !== 'string' && typeof value !== 'number') || value === '.' || value === '..') throw new ConfigurationError('Invalid path parameter');
      return encodeURIComponent(String(value));
    });
    const url = new URL(this.baseUrl + path);
    for (const [key, value] of Object.entries(input.query ?? {})) {
      if (value === undefined) continue;
      if (Array.isArray(value)) {
        const format = metadata.queryFormats[key];
        if (!format || value.some(item => !['string', 'number', 'boolean'].includes(typeof item)
            || typeof item === 'number' && !Number.isFinite(item))) throw new ConfigurationError('A query parameter has an invalid array value');
        if (format === 'multi') for (const item of value) url.searchParams.append(key, String(item));
        else {
          const separator = ({ csv: ',', ssv: ' ', tsv: '\t', pipes: '|' } as Record<string, string>)[format];
          if (separator === undefined) throw new ConfigurationError('Unsupported query array encoding');
          url.searchParams.set(key, value.join(separator));
        }
        continue;
      }
      if (value === null || (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') || (typeof value === 'number' && !Number.isFinite(value))) {
        throw new ConfigurationError('Query parameters must be scalar values');
      }
      url.searchParams.set(key, String(value));
    }
    let body: string | undefined;
    if (input.body !== undefined) {
      try { body = JSON.stringify(input.body, (_, value: unknown) => {
        if (typeof value === 'number' && !Number.isFinite(value) || ['bigint', 'function', 'symbol'].includes(typeof value)) throw new Error();
        return value;
      }); } catch { throw new ConfigurationError('Request body must be JSON serializable'); }
      if (body === undefined) throw new ConfigurationError('Request body must be JSON serializable');
      headers.set('Content-Type', 'application/json');
    }
    const secrets = requestSecrets(this.#apiKey, headers, body);
    const controller = new AbortController();
    const timeout = positive(input.timeoutMs ?? this.timeoutMs, 'timeoutMs');
    let timer: ReturnType<typeof setTimeout> | undefined;
    let onAbort: (() => void) | undefined;
    const interrupted = new Promise<never>((_, reject) => {
      timer = setTimeout(() => { controller.abort(); reject(new RequestTimeoutError('Request deadline exceeded')); }, timeout);
      onAbort = () => { controller.abort(); reject(new RequestAbortedError('Request was cancelled')); };
      input.signal?.addEventListener('abort', onAbort, { once: true });
    });
    const perform = async (): Promise<unknown> => {
      let response: Response;
      try {
        response = await this.fetcher(url, { method: metadata.method, headers,
          ...(body !== undefined ? { body } : {}), signal: controller.signal, redirect: 'error' });
      } catch {
        if (input.signal?.aborted) throw new RequestAbortedError('Request was cancelled');
        if (controller.signal.aborted) throw new RequestTimeoutError('Request deadline exceeded');
        throw new NetworkError('The API request failed; no automatic retry was sent');
      }
      if (response.status >= 300 && response.status < 400) throw new MalformedResponseError('API redirects are refused');
      const contentType = response.headers.get('content-type')?.split(';', 1)[0]?.trim().toLowerCase();
      if (response.ok && response.status !== 204 && response.status !== 205
          && contentType !== 'application/json' && !contentType?.endsWith('+json')) {
        await response.body?.cancel();
        throw new MalformedResponseError('Expected application/json from the API');
      }
      const declaredLength = response.headers.get('content-length');
      if (declaredLength !== null && Number(declaredLength) > this.maxResponseBytes) {
        await response.body?.cancel();
        throw new MalformedResponseError('API response exceeds the configured size limit');
      }
      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8', { fatal: true });
      let text = '';
      let bytes = 0;
      try {
        if (reader) {
          for (;;) {
            const chunk = await reader.read();
            if (chunk.done) break;
            bytes += chunk.value.byteLength;
            if (bytes > this.maxResponseBytes) throw new MalformedResponseError('API response exceeds the configured size limit');
            text += decoder.decode(chunk.value, { stream: true });
          }
        }
        text += decoder.decode();
      } catch (error) {
        await reader?.cancel().catch(() => undefined);
        if (error instanceof MalformedResponseError) throw error;
        throw new MalformedResponseError('API response body could not be read');
      } finally { reader?.releaseLock(); }
      let data: unknown;
      if (response.ok && response.status !== 204 && response.status !== 205 && text.length === 0) {
        throw new MalformedResponseError('Expected a nonempty JSON API response');
      }
      try { data = text ? JSON.parse(text) as unknown : undefined; } catch {
        if (response.ok) throw new MalformedResponseError('Expected a JSON API response');
      }
      if (!response.ok) {
        const envelope = object(data) ? data : {};
        const nested = object(envelope['error']) ? envelope['error'] : envelope;
        const code = safeString(nested['code'] ?? envelope['code'], secrets, 'HTTP_ERROR');
        const message = safeString(nested['message'] ?? envelope['message'] ?? envelope['error'], secrets, `API request failed (${response.status})`);
        const correlation = safeString(envelope['correlation_id'] ?? response.headers.get('x-correlation-id'), secrets, '');
        const retry = safeString(response.headers.get('retry-after'), secrets, '');
        const retainedHeaders: Record<string, string> = {};
        for (const name of ['payment-required', 'payment-response', 'www-authenticate', 'retry-after', 'x-correlation-id']) {
          const value = response.headers.get(name);
          if (value !== null) {
            if (value.length > this.maxResponseBytes) throw new MalformedResponseError('API error header exceeds the configured size limit');
            retainedHeaders[name] = safeString(value, secrets, '', value.length);
          }
        }
        throw new APIError(response.status, code, message, correlation || undefined, retry || undefined,
          errorEnvelope(data, secrets), retainedHeaders);
      }
      if (response.status === 204 || response.status === 205) return undefined;
      return data;
    };
    try { return await Promise.race([perform(), interrupted]) as Operations[K]['output']; }
    finally {
      if (timer) clearTimeout(timer);
      if (onAbort) input.signal?.removeEventListener('abort', onAbort);
      controller.abort();
    }
  }

  readonly users = {
    getMyMetrics: async (controls: RequestControls = {}): Promise<UsageMetrics> => {
      const value: unknown = await this.request('GET /api/v1/users/me/metrics', controls);
      if (!object(value) || value['success'] !== true || !object(value['metrics'])) throw new MalformedResponseError('Expected a successful usage metrics response');
      const metrics = value['metrics'];
      for (const key of ['conversations_count', 'messages_count', 'estimated_tokens', 'strategies_count', 'backtests_count']) {
        const count = metrics[key];
        if (count !== undefined && count !== null && (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0)) {
          throw new MalformedResponseError('Usage metrics contain an invalid count');
        }
      }
      for (const key of ['token_breakdown', 'tool_calls']) {
        if (metrics[key] !== undefined && metrics[key] !== null && !object(metrics[key])) {
          throw new MalformedResponseError('Usage metrics contain an invalid object');
        }
      }
      return metrics;
    },
  };

  readonly signals = {
    list: async (options: SignalListOptions = {}): Promise<Page<CoreModels['api1.Signal']>> => {
      const { signal, timeoutMs, ...query } = options;
      const result: unknown = await this.request('GET /api/v1/signals/', { query,
        ...(signal ? { signal } : {}), ...(timeoutMs !== undefined ? { timeoutMs } : {}) });
      const parsed = page<CoreModels['api1.Signal']>(result, 'signals', query.offset ?? 0, query.limit ?? 50);
      if (parsed.items.some(value => !object(value) || typeof value['name'] !== 'string' || typeof value['category'] !== 'string')) {
        throw new MalformedResponseError('Signal page contains invalid entries');
      }
      return parsed;
    },
    listIter: (options: Omit<SignalListOptions, 'offset'> = {}): AsyncIterable<CoreModels['api1.Signal']> => {
      const self = this;
      return { async *[Symbol.asyncIterator]() {
        let offset = 0;
        for (;;) {
          const result = await self.signals.list({ ...options, offset });
          for (const item of result.items) yield item;
          if (!result.hasMore || result.nextOffset === null) return;
          if (result.nextOffset <= offset) throw new MalformedResponseError('Signal pagination did not advance');
          offset = result.nextOffset;
        }
      } };
    },
  };

  readonly strategyWorkflow: StrategyWorkflow = Object.fromEntries(
    Object.keys(operationMetadata).filter(key => key.startsWith('POST /api/v1/strategy-workflow/')).map(key => {
      const name = key.split('/').at(-1)!.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
      return [name, (options: Input) => this.request(key as Operation, options as RequestOptions<Operation>)];
    }),
  ) as StrategyWorkflow;

  readonly backtesting = {
    submit: async (body: CoreModels['api2.BacktestRequest'], controls: RequestControls = {}): Promise<BacktestStatus> => {
      const result: unknown = await this.request('POST /api/v2/backtests/', { body, ...controls });
      return this.backtestStatus(result);
    },
    getStatus: async (backtestId: string, controls: RequestControls = {}): Promise<BacktestStatus> => {
      const result: unknown = await this.request('GET /api/v2/backtests/{backtest_id}/status', { path: { backtest_id: backtestId }, ...controls });
      const status = this.backtestStatus(result);
      if (status.backtest_id !== backtestId) throw new MalformedResponseError('Backtest status identity does not match');
      return status;
    },
    wait: async (backtestId: string, options: PollOptions = {}): Promise<BacktestStatus> => {
      const deadline = performance.now() + positive(options.timeoutMs ?? this.timeoutMs, 'timeoutMs');
      const interval = positive(options.pollIntervalMs ?? 1_000, 'pollIntervalMs');
      for (;;) {
        const remaining = Math.floor(deadline - performance.now());
        if (remaining <= 0) throw new RequestTimeoutError('Backtest polling deadline exceeded');
        const result = await this.backtesting.getStatus(backtestId, {
          timeoutMs: remaining, ...(options.signal ? { signal: options.signal } : {}),
        });
        if (result.status === 'completed' || result.status === 'failed' || result.status === 'cancelled') return result;
        const delay = Math.min(interval, Math.floor(deadline - performance.now()));
        if (delay <= 0) throw new RequestTimeoutError('Backtest polling deadline exceeded');
        await pause(delay, options.signal);
      }
    },
  };

  private backtestStatus(value: unknown): BacktestStatus {
    if (!object(value) || typeof value['backtest_id'] !== 'string' || !value['backtest_id']
        || typeof value['status'] !== 'string' || !['pending', 'running', 'completed', 'failed', 'cancelled'].includes(value['status'])) {
      throw new MalformedResponseError('Expected a backtest identity and recognized status');
    }
    return value as BacktestStatus;
  }
}
