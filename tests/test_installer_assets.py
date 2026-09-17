from installer.prepare_assets import version_numbers


def test_version_numbers_pads_and_truncates() -> None:
    assert version_numbers("1.5.1") == (1, 5, 1, 0)
    assert version_numbers("2.10.3.4") == (2, 10, 3, 4)
    assert version_numbers("3.0") == (3, 0, 0, 0)
