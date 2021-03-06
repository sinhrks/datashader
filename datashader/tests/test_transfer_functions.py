from io import BytesIO

import numpy as np
import xarray as xr
import PIL
import pytest

import datashader.transfer_functions as tf


coords = [np.array([0, 1, 2]), np.array([3, 4, 5])]
dims = ['y_axis', 'x_axis']

a = np.arange(10, 19, dtype='i4').reshape((3, 3))
a[[0, 1, 2], [0, 1, 2]] = 0
s_a = xr.DataArray(a, coords=coords, dims=dims)
b = np.arange(10, 19, dtype='f4').reshape((3, 3))
b[[0, 1, 2], [0, 1, 2]] = np.nan
s_b = xr.DataArray(b, coords=coords, dims=dims)
c = np.arange(10, 19, dtype='f8').reshape((3, 3))
c[[0, 1, 2], [0, 1, 2]] = np.nan
s_c = xr.DataArray(c, coords=coords, dims=dims)
agg = xr.Dataset(dict(a=s_a, b=s_b, c=s_c))


@pytest.mark.parametrize(['attr'], ['a', 'b', 'c'])
def test_interpolate(attr):
    x = getattr(agg, attr)
    img = tf.interpolate(x, 'pink', 'red', how='log')
    sol = np.array([[0, 4291543295, 4286741503],
                    [4283978751, 0, 4280492543],
                    [4279242751, 4278190335, 0]], dtype='u4')
    sol = xr.DataArray(sol, coords=coords, dims=dims)
    assert img.equals(sol)
    img = tf.interpolate(x, 'pink', 'red', how='cbrt')
    sol = np.array([[0, 4291543295, 4284176127],
                    [4282268415, 0, 4279834879],
                    [4278914047, 4278190335, 0]], dtype='u4')
    sol = xr.DataArray(sol, coords=coords, dims=dims)
    assert img.equals(sol)
    img = tf.interpolate(x, 'pink', 'red', how='linear')
    sol = np.array([[0, 4291543295, 4289306879],
                    [4287070463, 0, 4282597631],
                    [4280361215, 4278190335, 0]])
    sol = xr.DataArray(sol, coords=coords, dims=dims)
    assert img.equals(sol)
    img = tf.interpolate(x, 'pink', 'red', how=lambda x: x ** 2)
    sol = np.array([[0, 4291543295, 4291148543],
                    [4290030335, 0, 4285557503],
                    [4282268415, 4278190335, 0]], dtype='u4')
    sol = xr.DataArray(sol, coords=coords, dims=dims)
    assert img.equals(sol)


def test_colorize():
    coords = [np.array([0, 1]), np.array([2, 5])]
    cat_agg = xr.DataArray(np.array([[(0, 12, 0), (3, 0, 3)],
                                    [(12, 12, 12), (24, 0, 0)]]),
                           coords=(coords + [['a', 'b', 'c']]),
                           dims=(dims + ['cats']))

    colors = [(255, 0, 0), '#0000FF', 'orange']

    img = tf.colorize(cat_agg, colors, how='log')
    sol = np.array([[3137273856, 2449494783],
                    [4266997674, 3841982719]])
    sol = tf.Image(sol, coords=coords, dims=dims)
    assert img.equals(sol)
    colors = dict(zip('abc', colors))
    img = tf.colorize(cat_agg, colors, how='cbrt')
    sol = np.array([[3070164992, 2499826431],
                    [4283774890, 3774873855]])
    sol = tf.Image(sol, coords=coords, dims=dims)
    assert img.equals(sol)
    img = tf.colorize(cat_agg, colors, how='linear')
    sol = np.array([[1660878848, 989876991],
                    [4283774890, 2952790271]])
    sol = tf.Image(sol, coords=coords, dims=dims)
    assert img.equals(sol)
    img = tf.colorize(cat_agg, colors, how=lambda x: x ** 2)
    sol = np.array([[788463616, 436228863],
                    [4283774890, 2080375039]])
    sol = tf.Image(sol, coords=coords, dims=dims)
    assert img.equals(sol)


coords2 = [np.array([0, 2]), np.array([3, 5])]
img1 = tf.Image(np.array([[0xff00ffff, 0x00000000],
                          [0x00000000, 0xff00ff7d]], dtype='uint32'),
                coords=coords2, dims=dims)
img2 = tf.Image(np.array([[0x00000000, 0x00000000],
                          [0x000000ff, 0x7d7d7dff]], dtype='uint32'),
                coords=coords2, dims=dims)


def test_stack():
    img = tf.stack(img1, img2)
    out = np.array([[0xff00ffff, 0x00000000],
                    [0x00000000, 0xff3dbfbc]], dtype='uint32')
    assert (img.x_axis == img1.x_axis).all()
    assert (img.y_axis == img1.y_axis).all()
    np.testing.assert_equal(img.data, out)

    img = tf.stack(img2, img1)
    out = np.array([[0xff00ffff, 0x00000000],
                    [0x00000000, 0xff00ff7d]], dtype='uint32')
    assert (img.x_axis == img1.x_axis).all()
    assert (img.y_axis == img1.y_axis).all()
    np.testing.assert_equal(img.data, out)

    img = tf.stack(img1, img2, how='add')
    out = np.array([[0xff00ffff, 0x00000000],
                    [0x00000000, 0xff3d3cfa]], dtype='uint32')
    assert (img.x_axis == img1.x_axis).all()
    assert (img.y_axis == img1.y_axis).all()
    np.testing.assert_equal(img.data, out)


def test_masks():
    # Square
    mask = tf._square_mask(2)
    np.testing.assert_equal(mask, np.ones((5, 5), dtype='bool'))
    np.testing.assert_equal(tf._square_mask(0), np.ones((1, 1), dtype='bool'))
    # Circle
    np.testing.assert_equal(tf._circle_mask(0), np.ones((1, 1), dtype='bool'))
    out = np.array([[0, 1, 0],
                    [1, 1, 1],
                    [0, 1, 0]], dtype='bool')
    np.testing.assert_equal(tf._circle_mask(1), out)
    out = np.array([[0, 0, 1, 1, 1, 0, 0],
                    [0, 1, 1, 1, 1, 1, 0],
                    [1, 1, 1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1],
                    [0, 1, 1, 1, 1, 1, 0],
                    [0, 0, 1, 1, 1, 0, 0]], dtype='bool')
    np.testing.assert_equal(tf._circle_mask(3), out)


def test_spread():
    p = 0x7d00007d
    g = 0x7d00FF00
    b = 0x7dFF0000
    data = np.array([[p, p, 0, 0, 0],
                     [p, g, 0, 0, 0],
                     [0, 0, 0, 0, 0],
                     [0, 0, 0, b, 0],
                     [0, 0, 0, 0, 0]], dtype='uint32')
    coords = [np.arange(5), np.arange(5)]
    img = tf.Image(data, coords=coords, dims=dims)

    s = tf.spread(img)
    o = np.array([[0xdc00007d, 0xdc009036, 0x7d00007d, 0x00000000, 0x00000000],
                  [0xdc009036, 0xdc009036, 0x7d00ff00, 0x00000000, 0x00000000],
                  [0x7d00007d, 0x7d00ff00, 0x00000000, 0x7dff0000, 0x00000000],
                  [0x00000000, 0x00000000, 0x7dff0000, 0x7dff0000, 0x7dff0000],
                  [0x00000000, 0x00000000, 0x00000000, 0x7dff0000, 0x00000000]])
    np.testing.assert_equal(s.data, o)
    assert (s.x_axis == img.x_axis).all()
    assert (s.y_axis == img.y_axis).all()
    assert s.dims == img.dims

    s = tf.spread(img, px=2)
    o = np.array([[0xed00863b, 0xed00863b, 0xed00863b, 0xbc00a82a, 0x00000000],
                  [0xed00863b, 0xed00863b, 0xf581411c, 0xdc904812, 0x7dff0000],
                  [0xed00863b, 0xf581411c, 0xed864419, 0xbca85600, 0x7dff0000],
                  [0xbc00a82a, 0xdc904812, 0xbca85600, 0x7dff0000, 0x7dff0000],
                  [0x00000000, 0x7dff0000, 0x7dff0000, 0x7dff0000, 0x7dff0000]])
    np.testing.assert_equal(s.data, o)

    s = tf.spread(img, shape='square')
    o = np.array([[0xed00863b, 0xed00863b, 0xbc00a82a, 0x00000000, 0x00000000],
                  [0xed00863b, 0xed00863b, 0xbc00a82a, 0x00000000, 0x00000000],
                  [0xbc00a82a, 0xbc00a82a, 0xbca85600, 0x7dff0000, 0x7dff0000],
                  [0x00000000, 0x00000000, 0x7dff0000, 0x7dff0000, 0x7dff0000],
                  [0x00000000, 0x00000000, 0x7dff0000, 0x7dff0000, 0x7dff0000]])
    np.testing.assert_equal(s.data, o)

    s = tf.spread(img, how='add')
    o = np.array([[0xff0000b7, 0xff007d7a, 0x7d00007d, 0x00000000, 0x00000000],
                  [0xff007d7a, 0xff007d7a, 0x7d00ff00, 0x00000000, 0x00000000],
                  [0x7d00007d, 0x7d00ff00, 0x00000000, 0x7dff0000, 0x00000000],
                  [0x00000000, 0x00000000, 0x7dff0000, 0x7dff0000, 0x7dff0000],
                  [0x00000000, 0x00000000, 0x00000000, 0x7dff0000, 0x00000000]])
    np.testing.assert_equal(s.data, o)

    mask = np.array([[1, 0, 1],
                     [0, 1, 0],
                     [1, 0, 1]])
    s = tf.spread(img, mask=mask)
    o = np.array([[0xbc00a82a, 0xbc00007d, 0x7d00ff00, 0x00000000, 0x00000000],
                  [0xbc00007d, 0xbc00a82a, 0x7d00007d, 0x00000000, 0x00000000],
                  [0x7d00ff00, 0x7d00007d, 0xbca85600, 0x00000000, 0x7dff0000],
                  [0x00000000, 0x00000000, 0x00000000, 0x7dff0000, 0x00000000],
                  [0x00000000, 0x00000000, 0x7dff0000, 0x00000000, 0x7dff0000]])
    np.testing.assert_equal(s.data, o)

    s = tf.spread(img, px=0)
    np.testing.assert_equal(s.data, img.data)

    pytest.raises(ValueError, lambda: tf.spread(img, px=-1))
    pytest.raises(ValueError, lambda: tf.spread(img, mask=np.ones(2)))
    pytest.raises(ValueError, lambda: tf.spread(img, mask=np.ones((2, 2))))


def test_Image_to_pil():
    img = img1.to_pil()
    assert isinstance(img, PIL.Image.Image)


def test_Image_to_bytesio():
    bytes = img1.to_bytesio()
    assert isinstance(bytes, BytesIO)
    assert bytes.tell() == 0
