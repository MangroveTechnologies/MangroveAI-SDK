"""Public Pydantic models for all SDK domains."""

from .auth import (
    ApiKey,
    ApiKeyCreateResponse,
    LoginResponse,
    LoginUser,
    RefreshResponse,
)
from .backtesting import (
    AsyncBacktestStatus,
    AsyncBacktestSubmission,
    BacktestRequest,
    BacktestResult,
    BacktestTradesResponse,
    BulkBacktestItemResult,
    BulkBacktestRequest,
    BulkBacktestResult,
)
from .crypto_assets import (
    AssetMetadata,
    AssetTimestamps,
    CryptoAsset,
    Exchange,
    GlobalMarketResponse,
    MarketDataResponse,
    OHLCVResponse,
    RiskScores,
    TrendingResponse,
)
from .docs import (
    DocContentResponse,
    DocItem,
)
from .execution import (
    Account,
    CreateAccountRequest,
    EvaluateResult,
    Position,
    Trade,
)
from .shared import SuccessResponse
from .signals import (
    EvaluateResponse,
    MatchResponse,
    MatchResult,
    SearchSignalsRequest,
    Signal,
    SignalMetadata,
    ValidationResponse,
)
from .strategies import (
    CreateStrategyRequest,
    StrategyDetail,
    StrategyListItem,
    UpdateStrategyRequest,
)

__all__ = [
    # Shared
    "SuccessResponse",
    # Auth
    "LoginUser",
    "LoginResponse",
    "RefreshResponse",
    "ApiKey",
    "ApiKeyCreateResponse",
    # Strategies
    "StrategyListItem",
    "StrategyDetail",
    "CreateStrategyRequest",
    "UpdateStrategyRequest",
    # Backtesting
    "BacktestRequest",
    "BulkBacktestRequest",
    "BacktestResult",
    "BulkBacktestItemResult",
    "BulkBacktestResult",
    "BacktestTradesResponse",
    "AsyncBacktestSubmission",
    "AsyncBacktestStatus",
    # Signals
    "Signal",
    "SignalMetadata",
    "SearchSignalsRequest",
    "MatchResult",
    "MatchResponse",
    "EvaluateResponse",
    "ValidationResponse",
    # Crypto Assets
    "CryptoAsset",
    "RiskScores",
    "AssetMetadata",
    "AssetTimestamps",
    "Exchange",
    "MarketDataResponse",
    "OHLCVResponse",
    "TrendingResponse",
    "GlobalMarketResponse",
    # Execution
    "CreateAccountRequest",
    "Account",
    "Position",
    "Trade",
    "EvaluateResult",
    # Docs
    "DocItem",
    "DocContentResponse",
]
