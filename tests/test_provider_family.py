import pytest


@pytest.mark.parametrize('method,path,args,kwargs,payload', [
    ('get_smart_money_flows', '/crypto-assets/flow-intelligence/ETH', ['ETH'], {'chain': 'base', 'timeframe': '7d'}, {'symbol': 'ETH', 'chain': 'base', 'timeframe': '7d', 'data': {'whale_net_flow_usd': None}}),
    ('get_smart_money_netflows', '/crypto-assets/smart-money/netflows', [], {'chains': ['base'], 'include_labels': ['Fund']}, {'count': 1, 'chains': ['base'], 'labels': ['Fund'], 'data': [{'symbol': 'ETH'}]}),
    ('get_smart_money_holdings', '/crypto-assets/smart-money/holdings', [], {'min_value_usd': 100}, {'count': 0, 'chains': ['ethereum'], 'labels': ['Fund'], 'data': []}),
])
def test_missing_canonical_methods_preserve_payload(client, method, path, args, kwargs, payload):
    client._http.add_response('GET', path, json={'success': True, 'provider': 'nansen', 'quality': {'stale': True}, **payload})
    result = getattr(client.on_chain, method)(*args, **kwargs)
    assert result.provider == 'nansen'
    assert result.model_dump()['quality'] == {'stale': True}
    assert result.data == payload['data']
    assert len(client._http.requests) == 1


@pytest.mark.parametrize('method,path', [('get_perp_funding_rates', '/defi/perp-funding'), ('get_lending_rates', '/defi/lending-rates')])
def test_defi_aliases_make_one_request(client, method, path):
    client._http.add_response('GET', path, json={'success': True, 'count': 1, 'data': [{'rate': 2.5}], 'provider': 'defillama'})
    result = getattr(client.defi, method)()
    assert result.model_dump()['provider'] == 'defillama'
    assert len(client._http.requests) == 1
