import numpy as np
import pytest

pytest.importorskip("sklearn")

from analog_finder.ml import pu                      # noqa: E402


def test_pu_bagging_finds_the_positive_pattern():
    rng = np.random.default_rng(0)
    n = 3000
    X = rng.normal(size=(n, 4)).astype(np.float32)
    like = rng.choice(n, 120, replace=False)
    X[like, 0] += 4.0                                  # 120 cells share a pattern
    pos = like[:20]                                    # only 20 of them are labelled
    X[5, 1] = np.nan                                   # missing values are allowed
    s = pu.pu_bagging(X, pos, n_bags=8, ratio=10, seed=1)
    unlabelled_like = np.setdiff1d(like, pos)
    others = np.setdiff1d(np.arange(n), like)
    assert np.isfinite(s).all()
    assert np.median(s[unlabelled_like]) > np.percentile(s[others], 90)


def test_training_mask_hides_cells():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(500, 3)).astype(np.float32)
    pos = np.arange(10)
    mask = np.ones(500, bool)
    mask[:3] = False                                   # three positives hidden
    s = pu.pu_bagging(X, pos, train_mask=mask, n_bags=3, ratio=5)
    assert s.shape == (500,)
    with pytest.raises(ValueError):
        pu.pu_bagging(X, pos, train_mask=np.zeros(500, bool), n_bags=1)


def test_percentile_of():
    s = np.array([0.1, 0.2, 0.3, np.nan], np.float32)
    assert pu.percentile_of(s, 2) == pytest.approx(2.5 / 3)


def test_feature_list_leaves_out_location_and_site_lists():
    for name in pu.LEFT_OUT:
        assert name not in pu.FEATURES
