import pytest
from pydantic import ValidationError

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.models.strategy_workflow import SaveStrategyRequest


def test_skill_is_fetched_live_including_version_and_resource():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/load_skill', json={
        'skill': 'strategy-composition', 'version': 'sha256', 'instructions': 'server instructions',
        'required_tools': ['save_strategy'], 'resource': 'signal_archetype_map.yaml',
    })
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    skill = client.strategy_workflow.load_skill('strategy-composition', resource='signal_archetype_map.yaml')
    assert skill.version == 'sha256'
    assert skill.instructions == 'server instructions'
    assert skill.required_tools == ['save_strategy']


def test_save_uses_canonical_endpoint_and_preserves_draft():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/save_strategy', json={
        'strategy_id': 's1', 'created': True, 'name': 'BTC', 'asset': 'BTC', 'status': 'draft',
        'rules': {'entry': []}, 'resolved_config': {}, 'base_token': 'BTC',
        'quote_token': 'USDT', 'market_data_venue': 'binance',
    })
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    result = client.strategy_workflow.save_strategy(SaveStrategyRequest(
        strategy_name='BTC', asset='BTC', market_data_venue='binance', quote_token='USDT',
        entry_signals=[{'name': 'trigger', 'timeframe': '1h'}],
    ))
    assert result.status == 'draft'
    assert result.market_data_venue == 'binance'


def test_save_cannot_forge_a_tenant_or_bypass_draft():
    for field in ('user_id', 'org_id', 'session_id', 'status'):
        with pytest.raises(ValidationError):
            SaveStrategyRequest(strategy_name='BTC', asset='BTC', **{field: 'other'})


def test_the_build_sends_only_asset_and_timeframe():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/build_strategy_for_regime', json={
        'regime': {'horizon': '180d', 'band': 'neutral'}, 'strategy': {'status': 'draft'},
        'backtest': {'verdict': 'PASS'}, 'table': []})
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    result = client.strategy_workflow.build_strategy_for_regime('BTC', '1h')
    assert result['regime']['band'] == 'neutral'
    assert mock.requests[-1].json == {'asset': 'BTC', 'timeframe': '1h'}


def test_engine_and_marketplace_reads_use_the_workflow_endpoints():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/find_sweep_runs', json={'results': []})
    mock.add_response('POST', '/strategy-workflow/search_marketplace', json={'strategies': []})
    mock.add_response('POST', '/strategy-workflow/get_marketplace_strategy', json={'available': True})
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    assert client.strategy_workflow.find_sweep_runs('sharpe_ratio', asset='BTC') == {'results': []}
    assert client.strategy_workflow.search_marketplace(asset='BTC') == {'strategies': []}
    assert client.strategy_workflow.get_marketplace_strategy('m1') == {'available': True}
