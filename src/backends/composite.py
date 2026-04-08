from deepagents.backends import CompositeBackend, StateBackend, StoreBackend


def make_composite_backend(runtime):
    """Tạo CompositeBackend với routing cho long-term memory.

    /memories/* → StoreBackend (persistent, cross-thread)
    Mọi path khác → StateBackend (ephemeral, per-thread)
    """
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": StoreBackend(runtime),
        },
    )
