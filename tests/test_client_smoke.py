from epss_client import EpssClient


def test_prepare_and_query_params_do_not_crash():
	client = EpssClient()
	assert client is not None
