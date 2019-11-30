# -*- coding: utf-8 -*-

"""
This module contains the :class:`~pvmismatch.pvmismatch_lib.pvcell.PVcell`
object which is used by modules, strings and systems.
"""

from __future__ import absolute_import
from future.utils import iteritems
from pvmismatch.pvmismatch_lib.pvconstants import PVconstants
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import newton

# Defaults
MODEL = '2diode'
RS = 0.004267236774264931  # [ohm] series resistance
RSH_STC = 10.01226369025448  # [ohm] shunt resistance at STC
RSH_0 = RSH_STC / 10  # [ohm] shunt resistance at 0 irradiance (pvsyst model)
RSH_EXP = -5.5  # [unitless] exponent relating Rsh to irradiance (pvsyst model)
ISAT1_T0 = 2.286188161253440E-11  # [A] diode one saturation current
ISAT2_T0 = 1.117455042372326E-6  # [A] diode two saturation current
N1_0 = 1.0  # [unitless] diode one ideality factor
N2_0 = 2.0  # [unitless] diode two ideality factor
MU_GAMMA = 0.0003 # [1/K] temperature coefficient of N1 (pvsyst model)
ISC0_T0 = 6.3056  # [A] reference short circuit current
TCELL = 298.15  # [K] cell temperature
ARBD = 1.036748445065697E-4  # reverse breakdown coefficient 1
BRBD = 0.  # reverse breakdown coefficient 2
VRBD_ = -5.527260068445654  # [V] reverse breakdown voltage
NRBD = 3.284628553041425  # reverse breakdown exponent
EG_0 = 1.1  # [eV] band gap of cSi
DEG_DT = -0.0002677  # [eV/K] temperature coefficient of EG (desoto model)
ALPHA_ISC = 0.0003551  # [1/K] short circuit current temperature coefficient
EPS = np.finfo(np.float64).eps

class PVcell(object):
    """
    Class for PV cells.

    :param diode_model: name of diode model (str) '2diode', 'desoto', 'pvsyst'
    :param Rs: series resistance [ohms]
    :param Rsh_STC: shunt resistance  at STC condition [ohms]
    :param Rsh_0: shunt resistance at 0 irradiance (pvsyst) [ohms]
    :param Rsh_exp: exponent relating Rsh to irradiance (pvsyst) [unitless]
    :param Isat1_T0: first saturation diode current at ref temp [A]
    :param Isat2_T0: second saturation diode current [A]
    :param Isc0_T0: short circuit current at ref temp [A]
    :param aRBD: reverse breakdown coefficient 1
    :param bRBD: reverse breakdown coefficient 2
    :param VRBD: reverse breakdown voltage [V]
    :param nRBD: reverse breakdown exponent
    :param Eg_0: band gap at STC [eV]
    :param dEg_dT: temperature dependence of band gap [eV/K]
    :param N1_0: diode one ideality factor [unitless]
    :param N2_0: diode two ideality factor [unitless]
    :param mu_gamma: temperature coeff for diode one ideality factor [1/K]
    :param alpha_Isc: short circuit current temp coeff [1/K]
    :param Tcell: cell temperature [K]
    :param Ee: incident effective irradiance [suns]
    :param pvconst: configuration constants object
    :type pvconst: :class:`~pvmismatch.pvmismatch_lib.pvconstants.PVconstants`
    """

    _calc_now = False  #: if True ``calcCells()`` is called in ``__setattr__``

    def __init__(self, model=MODEL, Rs=RS, Rsh_STC=RSH_STC, Rsh_0=RSH_0,
                 Rsh_exp=RSH_EXP, Isat1_T0=ISAT1_T0, Isat2_T0=ISAT2_T0,
                 Isc0_T0=ISC0_T0, aRBD=ARBD, bRBD=BRBD, VRBD=VRBD_, nRBD=NRBD,
                 Eg_0=EG_0, dEg_dT=DEG_DT, N1_0=N1_0, N2_0=N2_0,
                 mu_gamma=MU_GAMMA, alpha_Isc=ALPHA_ISC,
                 Tcell=TCELL, Ee=1., pvconst=PVconstants()):
        # user inputs
        if MODEL in ['2diode', 'desoto', 'pvsyst']:
            self.diode_model = model
        else:
            raise ValueError('model must be one of ''2diode'', ''desoto'' or '
                             ' ''pvsyst''; % provided'.format(model))
        self.Rs = Rs  #: [ohm] series resistance
        self.Rsh_STC = Rsh_STC  #: [ohm] shunt resistance at STC
        self.Rsh_0 = Rsh_0  #: [ohm] shunt resistance at 0 irradiance (pvsyst)
        self.Rsh_exp = Rsh_exp  #: [unitless] exponent for _Rsh (pvsyst)
        self.Isat1_T0 = Isat1_T0  #: [A] diode one sat. current at T0
        self.Isat2_T0 = Isat2_T0  #: [A] diode two saturation current
        self.Isc0_T0 = Isc0_T0  #: [A] short circuit current at T0
        self.aRBD = aRBD  #: reverse breakdown coefficient 1
        self.bRBD = bRBD  #: reverse breakdown coefficient 2
        self.VRBD = VRBD  #: [V] reverse breakdown voltage
        self.nRBD = nRBD  #: reverse breakdown exponent
        self.Eg_0 = Eg_0  #: [eV] band gap at STC
        self.dEg_dT = dEg_dT  #: [eV/K] temperature coeff of band gap
        self.N1_0 = N1_0  #: [unitless] diode one ideality factor at T0
        self.N2_0 = N2_0  #: [unitless] diode two ideality factor
        self.mu_gamma = mu_gamma  #: [1/K] temp. coeff for diode one ideality
        self.alpha_Isc = alpha_Isc  #: [1/K] short circuit temp. coeff.
        self.Tcell = Tcell  #: [K] cell temperature
        self.Ee = Ee  #: [suns] incident effective irradiance on cell
        self.pvconst = pvconst  #: configuration constants
        self.Icell = None  #: cell currents on IV curve [A]
        self.Vcell = None  #: cell voltages on IV curve [V]
        self.Pcell = None  #: cell power on IV curve [W]
        self.VocSTC = self._VocSTC()  #: estimated Voc at STC [V]
        # set calculation flag
        self._calc_now = True  # overwrites the class attribute

    def __str__(self):
        fmt = '<PVcell(Ee=%g[suns], Tcell=%g[K], Isc=%g[A], Voc=%g[V])>'
        return fmt % (self.Ee, self.Tcell, self.Isc, self.Voc)

    def __repr__(self):
        return str(self)

    def __setattr__(self, key, value):
        # check for floats
        try:
            value = np.float64(value)
        except (TypeError, ValueError):
            pass  # fail silently if not float, eg: pvconst or _calc_now
        super(PVcell, self).__setattr__(key, value)
        # recalculate IV curve
        if self._calc_now:
            Icell, Vcell, Pcell = self.calcCell()
            self.__dict__.update(Icell=Icell, Vcell=Vcell, Pcell=Pcell)

    def update(self, **kwargs):
        """
        Update user-defined constants.
        """
        # turn off calculation flag until all attributes are updated
        self._calc_now = False
        # don't use __dict__.update() instead use setattr() to go through
        # custom __setattr__() so that numbers are cast to floats
        for k, v in iteritems(kwargs):
            setattr(self, k, v)
        self._calc_now = True  # recalculate

    @property
    def Vt(self):
        """
        Thermal voltage in volts.
        """
        return self.pvconst.k * self.Tcell / self.pvconst.q

    @property
    def Isc(self):
        return self.Ee * self.Isc0

    @property
    def N1(self):
        if self.model == 'pvsyst':
            return self.N1_0 + self.mu_gamma * (self.Tcell - self.pvconst.T0)
        return self.N1_0

    @property
    def N2(self):
        return self.N2

    @property
    def Eg(self):
        if self.model == 'desoto':
            return self.Eg_0 + self.dEg_dT * (self.Tcell - self.pvconst.T0)
        return self.Eg_0

    @property
    def Rsh(self):
        if self.model == 'desoto':
            return self.Rsh_STC / self.Ee
        elif self.model == 'desoto':
            rsh_tmp = self.Rsh_STC - self.Rsh_0 * np.exp(self.Rsh_exp) / \
                (1. - np.exp(self.Rsh_exp))
            rsh_base = np.maximum(0.0, rsh_tmp)
            return rsh_base + (self.Rsh_0 - rsh_base) * \
                np.exp(self.Rsh_exp * self.Ee)
        return self.Rsh_STC

    @property
    def Aph(self):
        """
        Photogenerated current coefficient, non-dimensional.
        """
        # Aph is undefined (0/0) if there is no irradiance
        if self.Isc == 0: return np.nan
        # short current (SC) conditions (Vcell = 0)
        Vdiode_sc = self.Isc * self.Rs  # diode voltage at SC
        Idiode1_sc = self.Isat1 * (np.exp(Vdiode_sc / self.N1 / self.Vt) - 1.)
        Idiode2_sc = self.Isat2 * (np.exp(Vdiode_sc / self.N2 / self.Vt) - 1.)
        Ishunt_sc = Vdiode_sc / self.Rsh  # diode voltage at SC
        # photogenerated current coefficient
        return 1. + (Idiode1_sc + Idiode2_sc + Ishunt_sc) / self.Isc

    @property
    def Isat1(self):
        """
        Diode one saturation current at Tcell in amps.
        """
        _Tstar = self.Tcell ** 3. / self.pvconst.T0 ** 3.  # scaled temperature
        _inv_delta_T = 1. / self.pvconst.T0 - 1. / self.Tcell  # [1/K]
        k_b = self.pvconst.k / self.pvconst.q
        if self.model == 'pvsyst': # include diode factor
            _expTstar = np.exp(
                self.Eg / k_b / self.N1 * _inv_delta_T
            )
        elif self.model == 'desoto':

            _expTstar = np.exp(
                self.Eg_0 / k_b / self.pvconst.T0 - self.Eg / k_b / self.Tcell
            )
        else:
            _expTstar = np.exp(
                self.Eg / k_b * _inv_delta_T
            )
        return self.Isat1_T0 * _Tstar * _expTstar  # [A] Isat1(Tcell)

    @property
    def Isat2(self):
        """
        Diode two saturation current at Tcell in amps.
        """
        if self.model=='2diode':
            _Tstar = self.Tcell ** 3. / self.pvconst.T0 ** 3.  # scaled temperature
            _inv_delta_T = 1. / self.pvconst.T0 - 1. / self.Tcell  # [1/K]
            _expTstar = np.exp(
                self.Eg * self.pvconst.q / self.N2 / self.pvconst.k * _inv_delta_T
            )
            return self.Isat2_T0 * _Tstar * _expTstar  # [A] Isat2(Tcell)
        else:
            return 0.0

    @property
    def Isc0(self):
        """
        Short circuit current at Tcell in amps.
        """
        _delta_T = self.Tcell - self.pvconst.T0  # [K] temperature difference
        return self.Isc0_T0 * (1. + self.alpha_Isc * _delta_T)  # [A] Isc0

    @property
    def Voc(self):
        """
        Estimate open circuit voltage of cells.
        Returns Voc : numpy.ndarray of float, estimated open circuit voltage
        """
        if self.model == '2diode': # does not use ideality factors
            C = self.Aph * self.Isc + self.Isat1 + self.Isat2
            delta = self.Isat2 ** 2. + 4. * self.Isat1 * C
            return self.Vt * np.log(
                ((-self.Isat2 + np.sqrt(delta)) / 2. / self.Isat1) ** 2.
            )
        else:
            C = self.Aph * self.Isc / self.Isat1
            return self.N1 * self.Vt * np.log(1. + C)

    def _VocSTC(self):
        """
        Estimate open circuit voltage of cells.
        Returns Voc : numpy.ndarray of float, estimated open circuit voltage
        """
        Vdiode_sc = self.Isc0_T0 * self.Rs  # diode voltage at SC
        Vt_sc = self.pvconst.k * self.pvconst.T0 / self.pvconst.q
        if self.model == '2diode':
            Idiode1_sc = self.Isat1_T0 * (np.exp(Vdiode_sc / Vt_sc) - 1.)
            Idiode2_sc = self.Isat2_T0 * (np.exp(Vdiode_sc / 2. / Vt_sc) - 1.)
            Ishunt_sc = Vdiode_sc / self.Rsh  # diode voltage at SC
            # photogenerated current coefficient
            Aph = 1. + (Idiode1_sc + Idiode2_sc + Ishunt_sc) / self.Isc0_T0
            # estimated Voc at STC
            C = Aph * self.Isc0_T0 + self.Isat1_T0 + self.Isat2_T0
            delta = self.Isat2_T0 ** 2. + 4. * self.Isat1_T0 * C
            return Vt_sc * np.log(
                ((-self.Isat2_T0 + np.sqrt(delta)) / 2. / self.Isat1_T0) ** 2.
            )
        else:
            Isat = self.Isat1_T0 * (
                np.exp(Vdiode_sc / Vt_sc / self.N1_0) - 1.)
            return self.N1_0 * Vt_sc * np.log(1. + self.Isc0_T0 / Isat)

    @property
    def Igen(self):
        """
        Photovoltaic generated light current (AKA IL or Iph)
        Returns Igen : numpy.ndarray of float, PV generated light current [A]

        Photovoltaic generated light current is zero if irradiance is zero.
        """
        if self.Ee == 0: return 0
        return self.Aph * self.Isc

    def calcCell(self):
        """
        Calculate cell I-V curves.
        Returns (Icell, Vcell, Pcell) : tuple of numpy.ndarray of float
        """
        Vreverse = self.VRBD * self.pvconst.negpts
        Vff = self.Voc
        delta_Voc = self.VocSTC - self.Voc
        # to make sure that the max voltage is always in the 4th quadrant, add
        # a third set of points log spaced with decreasing density, from Voc to
        # Voc @ STC unless Voc *is* Voc @ STC, then use an arbitrary voltage at
        # 80% of Voc as an estimate of Vmp assuming a fill factor of 80% and
        # Isc close to Imp, or if Voc > Voc @ STC, then use Voc as the max
        if delta_Voc == 0:
            Vff = 0.8 * self.Voc
            delta_Voc = 0.2 * self.Voc
        elif delta_Voc < 0:
            Vff = self.VocSTC
            delta_Voc = -delta_Voc
        Vquad4 = Vff + delta_Voc * np.flipud(self.pvconst.negpts)
        Vforward = Vff * self.pvconst.pts
        Vdiode = np.concatenate((Vreverse, Vforward, Vquad4), axis=0)
        Idiode1 = self.Isat1 * (np.exp(Vdiode / self.N1 / self.Vt) - 1.)
        Idiode2 = self.Isat2 * (np.exp(Vdiode / self.N2 / self.Vt) - 1.)
        Ishunt = Vdiode / self.Rsh
        fRBD = 1. - Vdiode / self.VRBD
        # use epsilon = 2.2204460492503131e-16 to avoid "divide by zero"
        fRBD[fRBD == 0] = EPS
        Vdiode_norm = Vdiode / self.Rsh / self.Isc0_T0
        fRBD = self.Isc0_T0 * fRBD ** (-self.nRBD)
        IRBD = (self.aRBD * Vdiode_norm + self.bRBD * Vdiode_norm ** 2) * fRBD
        Icell = self.Igen - Idiode1 - Idiode2 - Ishunt - IRBD
        Vcell = Vdiode - Icell * self.Rs
        Pcell = Icell * Vcell
        return Icell, Vcell, Pcell

    # diode model
    #  *-->--*--->---*--Rs->-Icell--+
    #  ^     |       |              ^
    #  |     |       |              |
    # Igen  Idiode  Ishunt         Vcell
    #  |     |       |              |
    #  |     v       v              v
    #  *--<--*---<---*--<-----------=
    # http://en.wikipedia.org/wiki/Diode_modelling#Shockley_diode_model
    # http://en.wikipedia.org/wiki/Diode#Shockley_diode_equation
    # http://en.wikipedia.org/wiki/William_Shockley

    @staticmethod
    def f_Icell(Icell, Vcell, Igen, Rs, Vt, Isat1, Isat2, Rsh, N1, N2):
        """
        Objective function for Icell.
        :param Icell: cell current [A]
        :param Vcell: cell voltage [V]
        :param Igen: photogenerated current at Tcell and Ee [A]
        :param Rs: series resistance [ohms]
        :param Vt: thermal voltage [V]
        :param Isat1: first diode saturation current at Tcell [A]
        :param Isat2: second diode saturation current [A]
        :param Rsh: shunt resistance [ohms]
        :return: residual = (Icell - Icell0) [A]
        """
        # arbitrary current condition
        Vdiode = Vcell + Icell * Rs  # diode voltage
        Idiode1 = Isat1 * (np.exp(Vdiode / N1 / Vt) - 1.)  # diode current
        Idiode2 = Isat2 * (np.exp(Vdiode / N2 / Vt) - 1.)  # diode current
        Ishunt = Vdiode / Rsh  # shunt current
        return Igen - Idiode1 - Idiode2 - Ishunt - Icell

    def calcIcell(self, Vcell):
        """
        Calculate Icell as a function of Vcell.
        :param Vcell: cell voltage [V]
        :return: Icell
        """
        args = (np.float64(Vcell), self.Igen, self.Rs, self.Vt,
                self.Isat1, self.Isat2, self.Rsh, self.N1, self.N2)
        return newton(self.f_Icell, x0=self.Isc, args=args)

    @staticmethod
    def f_Vcell(Vcell, Icell, Igen, Rs, Vt, Isat1, Isat2, Rsh, N1, N2):
        return PVcell.f_Icell(Icell, Vcell, Igen, Rs, Vt, Isat1, Isat2, Rsh,
                              N1, N2)

    def calcVcell(self, Icell):
        """
        Calculate Vcell as a function of Icell.
        :param Icell: cell current [A]
        :return: Vcell
        """
        args = (np.float64(Icell), self.Igen, self.Rs, self.Vt,
                self.Isat1, self.Isat2, self.Rsh, self.N1, self.N2)
        return newton(self.f_Vcell, x0=self.Voc, args=args)

    def plot(self):
        """
        Plot cell I-V curve.
        Returns cellPlot : matplotlib.pyplot figure
        """
        cell_plot = plt.figure()
        plt.subplot(2, 2, 1)
        plt.plot(self.Vcell, self.Icell)
        plt.title('Cell Reverse I-V Characteristics')
        plt.ylabel('Cell Current, I [A]')
        plt.xlim(self.VRBD - 1, 0)
        plt.ylim(0, self.Isc + 10)
        plt.grid()
        plt.subplot(2, 2, 2)
        plt.plot(self.Vcell, self.Icell)
        plt.title('Cell Forward I-V Characteristics')
        plt.ylabel('Cell Current, I [A]')
        plt.xlim(0, self.Voc)
        plt.ylim(0, self.Isc + 1)
        plt.grid()
        plt.subplot(2, 2, 3)
        plt.plot(self.Vcell, self.Pcell)
        plt.title('Cell Reverse P-V Characteristics')
        plt.xlabel('Cell Voltage, V [V]')
        plt.ylabel('Cell Power, P [W]')
        plt.xlim(self.VRBD - 1, 0)
        plt.ylim((self.Isc + 10) * (self.VRBD - 1), -1)
        plt.grid()
        plt.subplot(2, 2, 4)
        plt.plot(self.Vcell, self.Pcell)
        plt.title('Cell Forward P-V Characteristics')
        plt.xlabel('Cell Voltage, V [V]')
        plt.ylabel('Cell Power, P [W]')
        plt.xlim(0, self.Voc)
        plt.ylim(0, (self.Isc + 1) * self.Voc)
        plt.grid()
        return cell_plot
