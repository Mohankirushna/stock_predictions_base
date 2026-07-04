import pytest

from app.core.container import Container, ContainerError


class Port:  # stand-in for a domain port
    pass


class Adapter(Port):
    pass


def test_singleton_binding_returns_same_instance() -> None:
    c = Container()
    c.register(Port, lambda _: Adapter())
    assert c.resolve(Port) is c.resolve(Port)


def test_transient_binding_returns_new_instances() -> None:
    c = Container()
    c.register(Port, lambda _: Adapter(), singleton=False)
    assert c.resolve(Port) is not c.resolve(Port)


def test_unregistered_key_raises() -> None:
    with pytest.raises(ContainerError):
        Container().resolve(Port)


def test_reset_clears_singletons() -> None:
    c = Container()
    c.register(Port, lambda _: Adapter())
    first = c.resolve(Port)
    c.reset()
    assert c.resolve(Port) is not first


def test_provider_receives_container_for_nested_resolution() -> None:
    c = Container()
    c.register_instance(str, "postgres://x")

    class Repo:
        def __init__(self, dsn: str) -> None:
            self.dsn = dsn

    c.register(Repo, lambda ctr: Repo(ctr.resolve(str)))
    assert c.resolve(Repo).dsn == "postgres://x"
