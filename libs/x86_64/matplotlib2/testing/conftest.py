from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pytest

import matplotlib2


def pytest_configure(config):
    matplotlib2.use('agg')
    matplotlib2._called_from_pytest = True
    matplotlib2._init_tests()


def pytest_unconfigure(config):
    matplotlib2._called_from_pytest = False


@pytest.fixture(autouse=True)
def mpl_test_settings(request):
    from matplotlib2.testing.decorators import _do_cleanup

    original_units_registry = matplotlib2.units.registry.copy()
    original_settings = matplotlib2.rcParams.copy()

    backend = None
    backend_marker = request.node.get_closest_marker('backend')
    if backend_marker is not None:
        assert len(backend_marker.args) == 1, \
            "Marker 'backend' must specify 1 backend."
        backend, = backend_marker.args
        prev_backend = matplotlib2.get_backend()

    style = '_classic_test'  # Default of cleanup and image_comparison too.
    style_marker = request.node.get_closest_marker('style')
    if style_marker is not None:
        assert len(style_marker.args) == 1, \
            "Marker 'style' must specify 1 style."
        style, = style_marker.args

    matplotlib2.testing.setup()
    if backend is not None:
        # This import must come after setup() so it doesn't load the default
        # backend prematurely.
        import matplotlib2.pyplot as plt
        plt.switch_backend(backend)
    matplotlib2.style.use(style)
    try:
        yield
    finally:
        if backend is not None:
            plt.switch_backend(prev_backend)
        _do_cleanup(original_units_registry,
                    original_settings)


@pytest.fixture
def mpl_image_comparison_parameters(request, extension):
    # This fixture is applied automatically by the image_comparison decorator.
    #
    # The sole purpose of this fixture is to provide an indirect method of
    # obtaining parameters *without* modifying the decorated function
    # signature. In this way, the function signature can stay the same and
    # pytest won't get confused.
    # We annotate the decorated function with any parameters captured by this
    # fixture so that they can be used by the wrapper in image_comparison.
    baseline_images, = request.node.get_closest_marker('baseline_images').args
    if baseline_images is None:
        # Allow baseline image list to be produced on the fly based on current
        # parametrization.
        baseline_images = request.getfixturevalue('baseline_images')

    func = request.function
    func.__wrapped__.parameters = (baseline_images, extension)
    try:
        yield
    finally:
        delattr(func.__wrapped__, 'parameters')


@pytest.fixture
def pd():
    """Fixture to import and configure pandas."""
    pd = pytest.importorskip('pandas')
    try:
        from pandas.plotting import (
            register_matplotlib2_converters as register)
    except ImportError:
        from pandas.tseries.converter import register
    register()
    try:
        yield pd
    finally:
        try:
            from pandas.plotting import (
                deregister_matplotlib2_converters as deregister)
        except ImportError:
            pass
        else:
            deregister()
