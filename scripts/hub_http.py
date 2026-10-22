"""Finite network waits for the pinned Hub client; no credentials are logged."""

def configure_hub_http(factory=None, install=None):
    if factory is None:
        from huggingface_hub.utils._http import default_client_factory, set_client_factory
        factory, install = default_client_factory, set_client_factory
    def bounded():
        client = factory()
        client.timeout = type(client.timeout)(connect=15, read=45, write=45, pool=15)
        return client
    install(bounded)
