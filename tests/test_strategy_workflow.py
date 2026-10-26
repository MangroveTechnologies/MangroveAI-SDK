import httpx
import pytest
from pydantic import ValidationError

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.models.strategy_workflow import SaveStrategyRequest


@pytest.mark.parametrize('name,arguments', [
    ('list_sweep_markets', {'assets': ['ETH'], 'include_gapped': False}),
    ('size_sweep', {'assets': ['ETH'], 'draws_per_dataset': 2}),
    ('get_sweep_limits', {}),
    ('create_sweep', {'sweep_name': 'ETH search', 'assets': ['ETH']}),
    ('launch_sweep', {'experiment_id': 'exp1'}),
    ('get_sweep', {'experiment_id': 'exp1'}),
    ('list_sweeps', {'limit': 3}),
    ('list_run_filters', {'experiment_id': 'exp1'}),
    ('get_sweep_run', {'experiment_id': 'exp1', 'run_index': 0, 'config_hash': 'recorded'}),
    ('pause_sweep', {'experiment_id': 'exp1'}),
])
def test_sweep_calls_preserve_server_arguments_and_results(name, arguments):
    mock = MockTransport()
    response = {'status': 'queued', 'cap_applied': True, 'server_extension': {'value': 7}}
    mock.add_response('POST', '/strategy-workflow/' + name, json=response)
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    assert getattr(client.strategy_workflow, name)(**arguments) == response
    assert mock.requests[-1].json == arguments
    assert len(mock.requests) == 1


def test_sweep_launch_gateway_failure_does_not_launch_again():
    from mangrove_ai.exceptions import ServerError
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(504, json={'error': 'gateway timeout'})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = MangroveAI(api_key='test_key', environment='local', httpx_client=http_client)
        with pytest.raises(ServerError) as exc_info:
            client.strategy_workflow.launch_sweep('exp1')
    assert exc_info.value.status_code == 504
    assert len(requests) == 1
    assert requests[0].method == 'POST'
    assert requests[0].url.path.endswith('/strategy-workflow/launch_sweep')


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


def test_the_build_sends_only_asset_and_an_optional_candle_size():
    mock = MockTransport()
    for _ in range(2):
        mock.add_response('POST', '/strategy-workflow/build_strategy_for_regime', json={
            'regime': {'lookback_days': 180, 'window_direction': 'bull', 'band': 'neutral'},
            'strategy': {'status': 'draft'}, 'backtest': {'verdict': 'PASS'}, 'table': []})
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    result = client.strategy_workflow.build_strategy_for_regime('BTC', '1h')
    assert result['regime']['band'] == 'neutral'
    assert mock.requests[-1].json == {'asset': 'BTC', 'candle_size': '1h'}
    client.strategy_workflow.build_strategy_for_regime('BTC')
    assert mock.requests[-1].json == {'asset': 'BTC'}


def test_engine_and_marketplace_reads_use_the_workflow_endpoints():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/find_sweep_runs', json={'results': []})
    mock.add_response('POST', '/strategy-workflow/search_marketplace', json={'strategies': []})
    mock.add_response('POST', '/strategy-workflow/get_marketplace_strategy', json={'available': True})
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    assert client.strategy_workflow.find_sweep_runs('sharpe_ratio', asset='BTC') == {'results': []}
    assert client.strategy_workflow.search_marketplace(asset='BTC') == {'strategies': []}
    assert client.strategy_workflow.get_marketplace_strategy('m1') == {'available': True}


def test_backtest_trades_and_markets_use_the_workflow_endpoints():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/get_backtest_trades', json={'found': True, 'trades': []})
    mock.add_response('POST', '/strategy-workflow/list_backtest_markets', json={'asset': 'BTC', 'markets': []})
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    assert client.strategy_workflow.get_backtest_trades('b1', offset=500, limit=500)['found'] is True
    assert mock.requests[-1].json == {'backtest_id': 'b1', 'offset': 500, 'limit': 500}
    assert client.strategy_workflow.list_backtest_markets('BTC')['asset'] == 'BTC'
    assert mock.requests[-1].json == {'asset': 'BTC'}


def test_engine_source_hash_is_forwarded_unchanged():
    mock = MockTransport()
    mock.add_response('POST', '/strategy-workflow/save_strategy', json={
        'strategy_id': 's1', 'created': True, 'name': 'BTC', 'asset': 'BTC', 'status': 'draft',
        'rules': {}, 'resolved_config': {}, 'base_token': 'BTC',
        'quote_token': 'USDC', 'market_data_venue': 'BINANCE',
    })
    client = MangroveAI(api_key='test_key', environment='local', httpx_client=mock)
    client.strategy_workflow.save_strategy(SaveStrategyRequest(
        strategy_name='BTC', asset='BTC', source_experiment_id='experiment',
        source_run_index=0, source_config_hash='selected-config',
    ))
    assert mock.requests[-1].json['source_config_hash'] == 'selected-config'
    assert mock.requests[-1].json['source_run_index'] == 0


def test_skill_optional_tools_are_typed_and_backwards_compatible():
    from mangrove_ai.models.strategy_workflow import SkillDocument

    body = dict(skill='strategy-composition', version='hash', instructions='server',
                required_tools=['save_strategy'])
    assert SkillDocument(**body).optional_tools == []
    assert SkillDocument(**body, optional_tools=['propose_adopt']).optional_tools == ['propose_adopt']
