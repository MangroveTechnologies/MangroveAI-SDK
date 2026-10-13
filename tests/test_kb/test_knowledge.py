from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport


def test_canonical_namespace_routes_and_paging_arguments():
    mock = MockTransport()
    document = {'slug': 'guide', 'title': 'Guide', 'content': 'page', 'offset': 6000, 'next_offset': 6004, 'has_more': True}
    mock.add_response('GET', '/knowledge/documents/guide', json=document)
    mock.add_response('GET', '/knowledge/documents', json={'total': 0, 'documents': [], 'source': {}})
    mock.add_response('GET', '/knowledge/quick-reference', json=document)
    mock.add_response('GET', '/knowledge/search', json={'query': 'risk', 'total_results': 9, 'results': []})
    mock.add_response('GET', '/knowledge/glossary', json={'term': 'RSI', 'entry': {'term': 'RSI', 'definition': 'definition'}})
    mock.add_response('POST', '/knowledge/query', json={'op': 'ask', 'result': {'items': []}})
    client = MangroveAI(api_key='test-key', environment='local', httpx_client=mock)
    assert client.knowledge.list_documents().total == 0
    result = client.knowledge.get_document('guide', offset=6000, max_chars=100, view='section', section_anchor='risk')
    assert result.has_more and result.next_offset == 6004
    assert mock.requests[-1].params == {'offset': 6000, 'max_chars': 100, 'view': 'section', 'section_anchor': 'risk', 'full': 'false'}
    client.knowledge.quick_reference(view='overview')
    assert mock.requests[-1].params['view'] == 'overview'
    assert client.knowledge.search('risk', tag='risk').total_results == 9
    assert mock.requests[-1].params['tag'] == 'risk'
    assert client.knowledge.glossary('RSI').entry.definition == 'definition'
    assert client.knowledge.query('ask', q='risk').op == 'ask'
    assert len(mock.requests) == 6
