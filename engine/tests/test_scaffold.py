"""Scaffold smoke test; replaced by real tests as modules land."""

import pharmashed


def test_package_importable():
    assert pharmashed.__version__ == "0.0.0"
