from scripts.hub_http import configure_hub_http
import unittest
from types import SimpleNamespace

class HubTimeouts(unittest.TestCase):
    def test_installed_factory_preserves_client_and_sets_finite_timeouts(self):
        class Timeout:
            def __init__(self,**kwargs):self.values=kwargs
        client=SimpleNamespace(timeout=Timeout(),headers={'preserve':'yes'})
        installed=[]
        configure_hub_http(factory=lambda:client,install=installed.append)
        self.assertIs(installed[0](),client)
        self.assertEqual(client.timeout.values,dict(connect=15,read=45,write=45,pool=15))
        self.assertEqual(client.headers,{'preserve':'yes'})
