"""
Tests for pvmodules.
"""

from nose.tools import ok_
from pvmismatch.pvmismatch_lib.pvmodule import PVmodule, TCT492, PCT492
import numpy as np
from copy import copy


def test_calc_mod():
    pvmod = PVmodule()
    ok_(isinstance(pvmod, PVmodule))
    return pvmod


def test_calc_tct_mod():
    pvmod = PVmodule(cell_pos=TCT492)
    isc = np.interp(np.float64(0), pvmod.Vmod, pvmod.Imod)
    voc = np.interp(np.float64(0), np.flipud(pvmod.Imod), np.flipud(pvmod.Vmod))
    ok_(np.isclose(isc, 37.8335982026))
    ok_(np.isclose(voc, 55.2798357318))
    return pvmod


def test_calc_pct_mod():
    pvmod = PVmodule(cell_pos=PCT492)
    isc = np.interp(np.float64(0), pvmod.Vmod, pvmod.Imod)
    voc = np.interp(np.float64(0), np.flipud(pvmod.Imod), np.flipud(pvmod.Vmod))
    ok_(np.isclose(isc, 37.8335982026))
    ok_(np.isclose(voc, 55.2798357318))
    return pvmod


def test_calc_pct_bridges():
    pct492_bridges = copy(PCT492)
    pct492_bridges[0][0][2]['crosstie'] = True
    pct492_bridges[0][2][2]['crosstie'] = True
    pct492_bridges[0][4][2]['crosstie'] = True
    pvmod = PVmodule(cell_pos=pct492_bridges)
    return pvmod

if __name__ == "__main__":
    test_calc_mod()
    test_calc_tct_mod()
    test_calc_pct_mod()
    test_calc_pct_bridges()
