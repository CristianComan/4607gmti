def test_can_import():
    import gmti4607
    from gmti4607.models.file import GmtiFile
    assert hasattr(gmti4607, "__version__")
    assert GmtiFile
