import os
import tkinter as tk
from tkinter import ttk
from tk_tools import Led
import u6
from u6info import *
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

plt.rc('axes', grid=True)
plt.rc('text', color='white')
plt.rc('axes', labelcolor='white')
plt.rc('xtick', color='white')
plt.rc('ytick', color='white')

class DarkLed(Led):

    def __init__(self, root, size):
        super().__init__(root, size)
        bg = ttk.Style().lookup('TFrame', 'background')
        self._canvas['background'] = bg
        self._canvas['bd'] = 2
        self._canvas['relief'] = tk.FLAT
        self._canvas['highlightthickness'] = 0

class LabJackController(u6.U6):

    """Added methods for LabJack U6 control"""

    def __init__(self, numTimers=0, numCounters=0):
        """Initialize just like u6.U6

        Parameters:
        numTimers -- int representing number of timers to initialize (max 4)
        numCounters -- int representing number of counters to initialize (max 2)
        """
        super().__init__()

        self.getCalibrationData()
        for i in range(20):
            self.getFeedback(u6.BitDirWrite(i, 0))  # output
        self.configTimerClock(TimerClockBase=3, TimerClockDivisor=4)
        if numCounters:
            self.configIO(NumberTimersEnabled=numTimers, EnableCounter1=True)
        else:
            self.configIO(NumberTimersEnabled=numTimers)

    def ToggleOn(self, relay):
        """Turns a relay on

        Parameters:
        relay -- str representing the digitial pin on the LabJack
        """
        if relay.startswith('E'):
            IONumber = int(relay[3:]) + 8
        elif relay.startswith('C'):
            IONumber = int(relay[3:]) + 16
        else:
            IONumber = int(relay[3:])
        self.getFeedback(u6.BitDirWrite(int(IONumber), 1))
        self.getFeedback(u6.BitStateWrite(int(IONumber), 0))

    def ToggleOff(self, relay):
        """Turns a relay off

        Parameters:
        relay -- str representing the digitial pin on the LabJack
        """
        if relay.startswith('E'):
            IONumber = int(relay[3:]) + 8
        elif relay.startswith('C'):
            IONumber = int(relay[3:]) + 16
        else:
            IONumber = int(relay[3:])
        self.getFeedback(u6.BitDirWrite(int(IONumber), 0))

    def getRelayState(self, relay):
        """Checks state of relay.

        Parameters:
        relay -- str representing the digitial pin on the LabJack

        Returns -- True if on and False otherwise
        """
        if relay.startswith('E'):
            IONumber = int(relay[3:]) + 8
        elif relay.startswith('C'):
            IONumber = int(relay[3:]) + 16
        else:
            IONumber = int(relay[3:])
        if self.getFeedback(u6.BitDirRead(IONumber)) == [1]:
            return True
        else:
            return False


class OsakaController():
    """Controller for Osaka turbos."""
    def __init__(self, root, pinout, LJ=None):
        """Initializes the controller but does not turn anything on.

        Parameters:
        root -- Tkinter object to place controller in
        pinout -- dictionary prescribing the LabJack pins for
                  various functions
        lj -- LabJackController object
        """
        super().__init__()
        self.root = root
        self.pinout = pinout
        self.LJ = LJ

        self.LEDframe = ttk.Frame(self.root)
        self.LEDframe.grid_columnconfigure(0, w=1)

        size = 30  # size of LED widgets
        self.PowerLED = DarkLed(self.LEDframe, size=size)
        self.AccelerationLED = DarkLed(self.LEDframe, size=size)
        self.NormalLED = DarkLed(self.LEDframe, size=size)
        self.ErrorLED = DarkLed(self.LEDframe, size=size)

        ttk.Label(self.LEDframe, text='Acceleration',
                  anchor='e').grid(row=1, column=0, sticky='ew')
        self.AccelerationLED.grid(row=1, column=1, sticky='news')
        ttk.Label(self.LEDframe, text='Normal', anchor='e').grid(row=2,
                                                                 column=0,
                                                                 sticky='ew')
        self.NormalLED.grid(row=2, column=1, sticky='news')
        ttk.Label(self.LEDframe, text='Error', anchor='e').grid(row=3,
                                                                column=0,
                                                                sticky='ew')
        self.ErrorLED.grid(row=3, column=1, sticky='news')

        self.Buttonframe = ttk.Frame(self.root)
        self.Buttonframe.grid_columnconfigure(0, w=1)

        self.OnButton = ttk.Button(self.Buttonframe,
                                   text='Spin Up',
                                   command=self.SpinUpDown)
        self.ResetButton = ttk.Button(self.Buttonframe,
                                      text='Reset',
                                      command=self.ErrorReset)

        self.OnButton.grid(row=1, column=0, sticky='ew')
        self.ResetButton.grid(row=2, column=0, sticky='ew')

        self.checkLED()

    def SpinUpDown(self):
        """Spins up or down the turbo pump."""
        if self.LJ is not None:
            if not self.LJ.getRelayState:
                self.LJ.ToggleOn(self.pinout['Start/Stop'])
                self.OnButton['text'] = 'Spin Down'
            else:
                self.LJ.ToggleOff(self.pinout['Start/Stop'])
                self.OnButton['text'] = 'Spin Up'
        else:
            if self.OnButton['text'] == 'Spin Up':
                self.OnButton['text'] = 'Spin Down'
            elif self.OnButton['text'] == 'Spin Down':
                self.OnButton['text'] = 'Spin Up'

    def ErrorReset(self):
        """TODO: Docstring for ErrorReset.
        :returns: TODO
        check to see if there is an error light
        if there is an error, trigger relay for
        2 seconds and check again
        """
        if self.LJ is not None:
            if self.LJ.getAIN(self.pinout['Error']) < 2.:
                self.LJ.ToggleOn(self.pinout['Reset'])
                self.LJ.OnButton['state'] = 'disabled'
                if self.LJ.getRelayState(self.pinout['Start/Stop']):
                    self.SpinUpDown()
                self.root.after(1000, lambda: self.LJ.ToggleOff(self.pinout['Reset']))
                self.root.after(1200, lambda: self.OnButton.config(state='normal'))

    def checkLED(self):
        """Check status of all pump indicators."""
        if self.LJ is not None:
            if self.LJ.getAIN(self.pinout['Acceleration']) > 2.:
                self.AccelerationLED.to_green()
            else:
                self.AccelerationLED.to_grey()
            if self.LJ.getAIN(self.pinout['Normal']) > 2.:
                self.NormalLED.to_green()
            else:
                self.NormalLED.to_grey()
            if self.LJ.getAIN(self.pinout['Error']) < 2.:
                self.ErrorLED.to_red()
                print('Turbo Error')
            else:
                self.ErrorLED.to_grey()
        self.root.after(100, self.checkLED)


class LeskerGaugeController():
    """Docstring for LeskerGaugeController. """
    def __init__(self, root, pinout, LJ=None):
        """TODO: to be defined. """

        self.root = root
        self.pinout = pinout
        self.LJ = LJ

        self.delay = 1000

        self.time = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.Buttonframe = ttk.Frame(self.root)
        self.Buttonframe.grid_columnconfigure(0, w=1)

        self.PowerButton = ttk.Button(self.Buttonframe,
                                      text='Power Off',
                                      command=self.PowerOnOff)
        self.PowerButton.grid(row=0, column=0, sticky='ew')

        self.readGauge()

    def PowerOnOff(self):
        """TODO: Docstring for PowerOnOff.
        :returns: TODO
        check the status of the relay and
        toggle text and button accordingly
        """
        if self.LJ is not None:
            if self.LJ.getRelayState(self.pinout['Relay']):
                self.LJ.ToggleOff(self.pinout['Relay'])
                self.PowerButton['text'] = 'Power On'
            else:
                self.LJ.ToggleOn(self.pinout['Relay'])
                self.PowerButton['text'] = 'Power Off'
        else:
            if self.PowerButton['text'] == 'Power Off':
                self.PowerButton['text'] = 'Power On'
            elif self.PowerButton['text'] == 'Power On':
                self.PowerButton['text'] = 'Power Off'

    def readGauge(self):
        """TODO: Docstring for readGauge.
        :returns: TODO
        """
        if self.LJ is not None:
            V = self.LJ.getAIN(self.pinout['Output'], resolutionIndex=8)
        else:
            V = np.random.random(1)[0]*8
        self.time=time.time()
        self.value = 10**(1.667*V - 11.46)
        self.string_var.set(f'{self.value:.2e}')
        self.root.after(self.delay, self.readGauge)

class PfiefferGaugeReader():
    """Docstring for PfiefferGaugeReader. """
    def __init__(self, root, pin, LJ=None, label='Full Range'):
        """TODO: to be defined. """

        self.root = root
        self.pin = pin
        self.LJ = LJ
        self.label = label

        self.delay = 500

        self.time = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readGauge()

    def readGauge(self):
        """TODO: Docstring for readGauge.
        :returns: TODO
        """
        if self.LJ is not None:
            V = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8)
        else:
            V = np.random.random(1)[0]*8
        self.time=time.time()
        self.value = 10**(1.667*V - 11.46)
        self.string_var.set(f'{self.value:.2e}')
        if self.value < 1e-11:
            self.value = np.nan
            self.string_var.set('Off')
        self.root.after(self.delay, self.readGauge)

class ConvectronReader():
    """Docstring for PfiefferGaugeReader. """
    def __init__(self, root, pin, LJ=None, label='Convectron'):
        """TODO: to be defined. """

        self.root = root
        self.pin = pin
        self.LJ = LJ
        self.label = label

        self.delay = 500

        self.time = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readGauge()

    def readGauge(self):
        """TODO: Docstring for readGauge.
        :returns: TODO
        """
        if self.LJ is not None:
            V = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8)
        else:
            V = np.random.random(1)[0]*8
        self.time=time.time()
        self.value = 10**(V-4)
        self.string_var.set(f'{self.value:.2e}')
        if self.value < 2e-4:
            self.value = np.nan
            self.string_var.set('Under Range')
        self.root.after(self.delay, self.readGauge)


class BaratronReader():
    """Docstring for PfiefferGaugeReader. """
    def __init__(self, root, pin, LJ=None, label='Baratron'):
        """TODO: to be defined. """

        self.root = root
        self.pin = pin
        self.LJ = LJ
        self.label=label

        self.delay = 500

        self.time = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readGauge()

    def readGauge(self):
        """TODO: Docstring for readGauge.
        :returns: TODO
        """
        if self.LJ is not None:
            V = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8)
        else:
            V = np.random.random(1)[0]*8
        self.time=time.time()
        self.value = V
        self.string_var.set(f'{self.value:.2e}')
        if self.value < 3e-3:
            self.value = np.nan
            self.string_var.set('Under Range')
        if self.value > 10.:
            self.value = np.nan
            self.string_var.set('Over Range')
        self.root.after(self.delay, self.readGauge)


class IonGaugeReader():
    """Docstring for PfiefferGaugeReader. """
    def __init__(self, root, pin, LJ=None, label='Ion Gauge'):
        """TODO: to be defined. """

        self.root = root
        self.pin = pin
        self.LJ = LJ
        self.label = label

        self.delay = 500

        self.time = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readGauge()

    def readGauge(self):
        """TODO: Docstring for readGauge.
        :returns: TODO
        """
        if self.LJ is not None:
            V = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8)
        else:
            V = np.random.random(1)[0]*8
        self.time=time.time()
        exp = abs(int(np.floor(V)))
        mantissa = (1 - (V - exp))*10
        self.value = float(f'{mantissa:.2f}e-{exp}')
        self.string_var.set(f'{self.value:.2e}')
        if self.value>1e-3:
            self.value = np.nan
            self.string_var.set('Off')
        self.root.after(self.delay, self.readGauge)


class CanvasedPlot(ttk.Frame):

    def __init__(self, master, items, labels, xlabel='Time (s)', ylabel='Value', notebook=None, tablabel=None):
        if notebook is not None:
            super().__init__(notebook)
            if tablabel is not None:
                notebook.add(self, text=tablabel)
            else:
                notebook.add(self, text=f'Tab {len(notebook.tabs())+1}')
        else:
            super().__init__()
        self.master = master
        self.items = items

        bg = ttk.Style().lookup('TFrame', 'background')
        self.fig, self.ax = plt.subplots(1, facecolor=bg)
        self.ax.set_facecolor((.21, .21, .21 ))
        self.ax.set_xlabel(xlabel, fontsize=14)
        self.ax.set_ylabel(ylabel, fontsize=14)
        self.lines = []
        for i in range(len(self.items)):
             #self.lines.append(self.ax.plot([], [], label=labels[i])[0])
             self.lines.append(self.ax.plot([], [], lw=3)[0])
        if labels is not None:
            self.legend = self.ax.legend(self.lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=14, facecolor=bg)
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill='both', expand=1)
        ttk.Button(self, text='Reset Plot', command=self.reset).pack(fill='both')
        self.update_plot()

    def update_plot(self):
        min_delay = min([item.delay for item in self.items])
        for i in range(len(self.items)):
            if self.items[i].should_plot.get():
                self.lines[i].set_xdata(np.append(self.lines[i].get_xdata(), self.items[i].time - self.master.starttime))
                self.lines[i].set_ydata(np.append(self.lines[i].get_ydata(), self.items[i].value))
            else:
                self.lines[i].set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.tight_layout()
        self.canvas.draw()
        self.after(min_delay, self.update_plot)

    def reset(self):
        for i in range(len(self.items)):
            self.lines[i].set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.tight_layout()
        self.canvas.draw()

class Info(ttk.LabelFrame):  # pylint: disable=too-many-ancestors
    """
    TODO
    """

    def __init__(self, master, label='Test', plottable=False, valuelabel='Value'):
        super().__init__(master, labelanchor='n')
        self.master = master
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(2, weight=2)

        self.plottable = plottable
        self.valuelabel = valuelabel

        self['text'] = label

        self.maketitleline()

    def clearlabels(self):
        for child in self.winfo_children():
            child.destroy()

    def maketitleline(self):
        ttk.Separator(self, orient = tk.HORIZONTAL).grid(row = 0, column = 0, columnspan = 5, sticky = 'ew')
        ttk.Label(self, text = 'Name', anchor='center').grid(row = 1, column = 0, sticky = 'ew')
        ttk.Separator(self, orient = tk.VERTICAL).grid(row = 1, column = 1, sticky = 'ns')
        ttk.Label(self, text = self.valuelabel, anchor='center').grid(row = 1, column = 2, sticky = 'ew')
        ttk.Separator(self, orient = tk.VERTICAL).grid(row = 1, column = 3, sticky = 'ns')
        if self.plottable:
            ttk.Label(self, text = 'Plot?', anchor='center').grid(row = 1, column = 4, sticky = 'ew')
        ttk.Separator(self, orient = tk.HORIZONTAL).grid(row = 2, column = 0, columnspan = 5, sticky = 'ew')

    def addrow(self, label, item):
        r = len(self.grid_slaves(column = 0))
        ttk.Label(self, text=label, anchor='center').grid(row = r, column = 0, sticky = 'ew')
        ttk.Separator(self, orient = tk.VERTICAL).grid(row = r, column = 1, sticky = 'ns')
        ttk.Label(self, textvariable=item.string_var, anchor='center').grid(row = r, column = 2, sticky = 'ew')
        ttk.Separator(self, orient = tk.VERTICAL).grid(row = r, column = 3, sticky = 'ns')
        if self.plottable:
            #ttk.Checkbutton(self, variable=item.should_plot, command = self.master.togglePlot).grid(row = r, column = 4, sticky = 'ew')
            ttk.Checkbutton(self, variable=item.should_plot).grid(row = r, column = 4, sticky = 'ew')
        ttk.Separator(self, orient = tk.HORIZONTAL).grid(row = r+1, column = 0, columnspan = 5, sticky = 'ew')


class TCReader():

    def __init__(self, root, pin, LJ=None, ColdJunction=None):
        """TODO: to be defined. """

        self.root = root
        self.pin = pin
        self.LJ = LJ
        self.ColdJunction=ColdJunction

        self.delay = 1000

        self.time=None
        self.value_old = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readTC()

    def readTC(self):
        if self.LJ is not None:
            mV = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8, gainIndex=3)*1000.
            if mV > 7:
                mV = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8, gainIndex=2)*1000.
            if self.ColdJunction is not None:
                CJVolts = self.LJ.getAIN(int(self.ColdJunction[3:]),
                                         resolutionIndex=8,
                                         gainIndex=0)
                CJTemp = 55.56 * CJVolts - 17.78
            else:
                CJTemp = self.LJ.getTemperature() + 2.5 - 273.15
            totalmVolts = TCmVolts + tempCToMVolts(CJTemp)
        else:
            totalmVolts = np.random.random(1)[0]*7
        TCtemp = mVoltsToTempC(totalmVolts)
        self.time = time.time()
        self.value_old = self.value
        self.value = TCtemp
        try:
            if (abs(self.value - self.value_old) > 50.) and (self.LJ is not None):
                self.string_var.set(f'Malfunction')
            else:
                self.string_var.set(f'{self.value:.1f}')
        except TypeError:
            pass
        self.root.after(self.delay, self.readTC)

class Flowmeter():

    def __init__(self, root, pin, LJ=None):
        """TODO: to be defined. """

        self.root = root
        self.pin = pin
        self.LJ = LJ

        self.delay = 100

        self.time = None
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readFlowmeter()

    def readFlowmeter(self):
        if self.LJ is not None:
            V = self.LJ.getAIN(int(self.pin[3:]), resolutionIndex=8)
        else:
            V = np.random.random(1)[0]*10.
        self.time = time.time()
        self.value = V
        self.string_var.set(f'{self.value:.2f}')
        self.root.after(self.delay, self.readFlowmeter)


class ToF():

    def __init__(self, root, LJ=None, dual=False, dualToF=None, dualNumber=1):
        """TODO: to be defined. """

        self.root = root
        self.LJ = LJ
        self.dual = dual
        self.dualToF = dualToF
        self.dualNumber = dualNumber

        self.delay = 100

        self.starttime = time.time()
        self.value = None
        self.time = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.readToF()

    def readToF(self):
        if self.dual:
            result = self.dualToF.value[self.dualNumber-1]
        elif self.LJ is not None:
            result = np.random.random(1)[0]*250
        else:
            result = np.random.random(1)[0]*250
        self.value=result
        try:
            self.string_var.set(f'{self.value:.0f}')
        except TypeError:
            pass
        self.root.after(self.delay, self.readToF)


class DualToF():
    def __init__(self, root, LJ=None):
        """TODO: to be defined. """

        self.root = root
        self.LJ = LJ

        self.delay = 100

        self.value = [None, None]
        self.starttime = time.time()
        self.ToF1 = ToF(root, LJ=LJ, dual=True, dualToF=self, dualNumber=1)
        self.ToF2 = ToF(root, LJ=LJ, dual=True, dualToF=self, dualNumber=2)

        self.readDualToF()

    def readDualToF(self):
        result = np.random.random(2)*250
        self.value = result
        self.time = time.time()
        self.ToF1.time = self.time
        self.ToF2.time = self.time
        self.root.after(self.delay, self.readDualToF)


class Velocity():

    def __init__(self, root, ToF):
        """TODO: to be defined. """

        self.root = root
        self.ToF = ToF

        self.delay = 100
        self.time = None
        self.heights = []
        self.times = []
        self.value = None
        self.string_var = tk.StringVar()
        self.should_plot = tk.BooleanVar()

        self.calcVelocity()

    def calcVelocity(self):
        if self.ToF.value is not None:
            self.heights.append(self.ToF.value)
            self.times.append(self.ToF.time)
            self.time = self.ToF.time
        if len(self.heights) > 3:
            self.heights.pop(0)
            self.times.pop(0)
        try:
            f0 = self.heights[0]
            f1 = self.heights[1]
            f2 = self.heights[2]
            dt_21 = self.times[2] - self.times[1]
            dt_20 = self.times[2] - self.times[0]
            dt2_21 = dt_21*dt_21
            dt2_20 = dt_20*dt_20
            self.value = ((f1-f2)/dt2_21 + (f2-f0)/dt2_20)/(1/dt_20 - 1/dt_21)
        except IndexError:
            pass
        try:
            self.string_var.set(f'{self.value:.2f}')
        except TypeError:
            pass
        self.root.after(self.delay, self.calcVelocity)

class DCMotorDriver():

    def __init__(self, root, pinout, LJ=None):

        super().__init__()
        self.root = root
        self.pinout = pinout
        self.LJ = LJ

        self.setpoint = 0.0
        self.setpoint_str = tk.StringVar()
        self.setpoint_str.set(str(self.setpoint))
        self.setpoint_fmt = tk.StringVar()
        self.setpoint_fmt.set(f'{self.setpoint:3.1f}')

        self.Statusframe = ttk.Frame(self.root)
        self.Statusframe.grid_columnconfigure(0, w=1)

        size = 30  # size of LED widgets
        self.PowerLED = DarkLed(self.Statusframe, size=size)
        self.PowerLED.grid(row=0, column=1)
        ttk.Label(self.Statusframe, text='Power', anchor='e').grid(row=0, column=0, sticky='ew')

        ttk.Label(self.Statusframe, text='Duty Cycle:', anchor='e').grid(row=1, column=0, sticky='ew')
        ttk.Label(self.Statusframe, textvariable=self.setpoint_fmt).grid(row=1, column=1, sticky='ew')

        self.Controlframe = ttk.Frame(self.root)
        self.Controlframe.grid_columnconfigure(0, w=1)
        self.Controlframe.grid_columnconfigure(1, w=1)

        self.OnButton = ttk.Button(self.Controlframe,
                                   text='Power On',
                                   command=self.PowerOnOff)
        self.OnButton.grid(row=0, column=0, sticky='ew', columnspan=2)

        ttk.Label(self.Controlframe, text='Duty Cycle:', anchor='e').grid(row=1, column=0, sticky='ew')
        ttk.Entry(self.Controlframe, textvariable=self.setpoint_str).grid(row=1, column=1, sticky='news')

        self.setButton = ttk.Button(self.Controlframe, text='Enter', command=self.setDuty)
        self.setButton.grid(row=2, column=0, columnspan=2, sticky='ew')


    def PowerOnOff(self):
        pass

    def setDuty(self):
        pass

class FileWriter:

    def __init__(self, root, objs):

        self.root = root
        self.objs = objs

        self.delay = min([obj.delay for obj in objs])

        self.location = None
        self.location_str = tk.StringVar()
        self.location_str.set('Not Selected')

        self.file = None
        self.file_str = tk.StringVar()
        self.file_str.set('Not Selected')

        self.currently = False

        self.controlframe = ttk.Frame(self.root)
        self.controlframe.grid_columnconfigure(0, w=1)
        self.controlframe.grid_columnconfigure(1, w=1)

        self.ChooseButton = ttk.Button(self.controlframe, text='Choose Save Location', command=self.chooseLocation)
        self.ChooseButton.grid(row=0, column=0, columnspan=2, sticky='ew')
        ttk.Label(self.controlframe, text='Save Location:', anchor='e').grid(row=1, column=0, sticky='news')
        ttk.Label(self.controlframe, textvariable=self.location_str, anchor='w').grid(row=1, column=1, sticky='news')
        ttk.Label(self.controlframe, text='File Name:', anchor='e').grid(row=2, column=0, sticky='news')
        ttk.Label(self.controlframe, textvariable=self.file_str, anchor='w').grid(row=2, column=1, sticky='news')
        self.WriteButton = ttk.Button(self.controlframe, text='Start Saving Data', command=self.writeFile)
        self.WriteButton.grid(row=3, column=0, columnspan=2, sticky='ew')

    def chooseLocation(self):
        filename = tk.filedialog.asksaveasfilename(initialdir='../../NPRE423-2021-VT')
        filename = filename.split('.')[0] + '.csv'
        self.file_str.set(filename.split('/')[-1])
        self.location_str.set('/'.join('/'.join(filename.split('/')[:-1])[-25:].split('/')[1:]))
        self.file = filename
        names = []
        for i in self.objs:
            names.extend([f'{i.label} Time', f'{i.label} Value'])
        self.data = pd.DataFrame(columns=names)

    def writeFile(self):
        if self.WriteButton['text'] == 'Start Saving Data':
            if os.path.exists(self.file):
                if tk.messagebox.askquestion('Overwrite File?', f"File '{self.file}' alread exists. Do you wish to overwrite it?") == 'yes':

                    self.WriteButton['text'] = 'Stop Saving Data'
                    self.ChooseButton['state'] = 'disabled'
                    self.currently = True
                    self.writing()
                else:
                    pass
            else:
                self.WriteButton['text'] = 'Stop Saving Data'
                self.ChooseButton['state'] = 'disabled'
                self.currently = True
                self.writing()
        else:
            self.WriteButton['text'] = 'Start Saving Data'
            self.ChooseButton['state'] = 'normal'
            self.currently = False
            self.data.to_csv(self.file, index=False)

    def writing(self):
        if not self.writing:
            return
        data = []
        for i in self.objs:
            data.extend([i.time, i.value])
        self.data.loc[len(self.data), :] = data
        self.root.after(self.delay, self.writing)

class PumpImage(tk.Canvas):

    def __init__(self, root):
        self.analysis_width = 1.5
        self.analysis_length = 24
        self.res_width = 4.
        self.res_length = 12
        self.separation = 5
        self.scaling = 20
        self.startheight = 5
        self.root = root
        top = tk.Toplevel(self.root)
        super().__init__(top, height=60+self.analysis_length*self.scaling, width=20+(self.separation+self.res_width/2+self.analysis_width)*self.scaling)

        self.direction = 1


        self.create_polygon(10,10, 10+self.analysis_width*self.scaling,10, 10+self.analysis_width*self.scaling,10+self.analysis_length*self.scaling, 10,10+self.analysis_length*self.scaling, 10,10)
        self.create_polygon(self.separation*self.scaling+10, 10+self.analysis_length*self.scaling - self.res_length*self.scaling,
                            self.separation*self.scaling+10+self.res_width*self.scaling, 10+self.analysis_length*self.scaling - self.res_length*self.scaling,
                            self.separation*self.scaling+10+self.res_width*self.scaling, 10+self.analysis_length*self.scaling,
                            self.separation*self.scaling+10, 10+self.analysis_length*self.scaling,
                            self.separation*self.scaling+10, 10+self.analysis_length*self.scaling - self.res_length*self.scaling)
        self.create_line(10+self.analysis_width/2*self.scaling, 10+self.analysis_length*self.scaling,
                         10+self.analysis_width/2*self.scaling, 10+self.analysis_length*self.scaling+40,
                         10+self.separation*self.scaling+self.res_width/2*self.scaling, 10+self.analysis_length*self.scaling+40,
                         10+self.separation*self.scaling+self.res_width/2*self.scaling, 10+self.analysis_length*self.scaling,
                         width=5, fill='gray')
        self.res_height = 10+self.analysis_length*self.scaling - self.startheight*self.scaling
        self.analysis_height = 10+self.analysis_length*self.scaling - self.startheight*self.scaling
        #self.res = self.create_polygon(160, 240, 240, 240, 240, 200, 160,200, fill='gray')
        self.analysis = self.create_polygon(10,self.analysis_height, 10+self.analysis_width*self.scaling,self.analysis_height, 10+self.analysis_width*self.scaling,10+self.analysis_length*self.scaling, 10,10+self.analysis_length*self.scaling, 10,10, fill='gray')
        self.res = self.create_polygon(self.separation*self.scaling+10, self.res_height,
                            self.separation*self.scaling+10+self.res_width*self.scaling, self.res_height,
                            self.separation*self.scaling+10+self.res_width*self.scaling, 10+self.analysis_length*self.scaling,
                            self.separation*self.scaling+10, 10+self.analysis_length*self.scaling,
                            self.separation*self.scaling+10, 10+self.analysis_length*self.scaling - self.res_length*self.scaling,
                                       fill='gray')
        self.pack(expand=1, fill='both')
        self.update()

    def update(self):
        modifier = int(self.res_width**2/ self.analysis_width**2)
        if (self.analysis_height - self.direction*modifier < 10) or (self.analysis_height - self.direction*modifier > 10+self.analysis_length*self.scaling - self.startheight*self.scaling):
            self.direction *= -1
        self.res_height += self.direction
        self.analysis_height -= modifier*self.direction
        self.delete(self.res)
        self.delete(self.analysis)
        self.analysis = self.create_polygon(10,self.analysis_height, 10+self.analysis_width*self.scaling,self.analysis_height, 10+self.analysis_width*self.scaling,10+self.analysis_length*self.scaling, 10,10+self.analysis_length*self.scaling, 10,10, fill='gray')
        self.res = self.create_polygon(self.separation*self.scaling+10, self.res_height,
                            self.separation*self.scaling+10+self.res_width*self.scaling, self.res_height,
                            self.separation*self.scaling+10+self.res_width*self.scaling, 10+self.analysis_length*self.scaling,
                            self.separation*self.scaling+10, 10+self.analysis_length*self.scaling,
                            self.separation*self.scaling+10, 10+self.analysis_length*self.scaling - self.res_length*self.scaling,
                                       fill='gray')
        self.root.after(100, self.update)

class MainApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.grid_rowconfigure(0, w=1)
        self.grid_columnconfigure(0, w=1)
        self.grid_columnconfigure(1, w=1)

        self.LJ = LabJackController()
        self.starttime = time.time()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        s = ttk.Style()
        self.tk.eval('''
         set base_theme_dir ./themes/awthemes-10.3.0/awthemes-10.3.0/
         package ifneeded awthemes 10.3.0 \
         [list source [file join $base_theme_dir awthemes.tcl]]
         package ifneeded colorutils 4.8\
         [list source [file join $base_theme_dir colorutils.tcl]]
         package ifneeded awdark 7.11\
         [list source [file join $base_theme_dir awdark.tcl]]
         package ifneeded awlight 7.9\
         [list source [file join $base_theme_dir awlight.tcl]]
         package ifneeded awbreezedark 1.0\
         [list source [file join $base_theme_dir awbreezedark.tcl]]
         package ifneeded awblack 7.8\
         [list source [file join $base_theme_dir awblack.tcl]]
         ''')
        self.tk.call('package', 'require', 'awdark')
        self.tk.call('package', 'require', 'awlight')
        s.theme_use('awdark')
        s.configure('.', font=('Times', 20))
        s.configure('TLabelframe.Label', font=('Times', 20, 'bold'))
        s.configure('Small.TLabelframe.Label', font=('Times', 18, 'bold'))
        s.configure('TNotebook.Tab', font=('Times', 18))
        s.configure('Header.TLabel', font=('Times', 18, 'bold underline'))
        s.configure('SubHeader.TLabel', font=('Times', 18, 'underline'))

        convectron = ConvectronReader(self, 'AIN6', LJ=self.LJ)
        baratron = BaratronReader(self, 'AIN2', LJ=self.LJ)
        iongauge = IonGaugeReader(self, 'AIN4', LJ=self.LJ)
        fullrange = PfiefferGaugeReader(self, 'AIN0', LJ=self.LJ)

        gaugeframe = Info(self, label='Pressure Gauges', plottable=True, valuelabel='Pressure (Torr)')
        gaugeframe.grid(row=0, column=0, sticky='news')
        gaugeframe.addrow('Baratron', baratron)
        gaugeframe.addrow('Convectron', convectron)
        gaugeframe.addrow('Ion Gauge', iongauge)
        gaugeframe.addrow('Full Range', fullrange)

        plot = CanvasedPlot(self, [baratron, convectron, iongauge, fullrange],
                ['Baratron', 'Convectron', 'Ion Gauge', 'Full Range'],
                ylabel='Pressure (Torr)', notebook=None, tablabel='Pressure')
        plot.ax.set_yscale('log')
        plot.grid(row=0, column=1, rowspan=2, sticky='news')

        filewriter = FileWriter(self, [baratron, convectron, iongauge, fullrange])
        filewriter.controlframe.grid(row=1, column=0, sticky='news')

    def on_closing(self):
        self.LJ.configIO(NumberTimersEnabled=0)
        for i in range(2):
            Value = self.LJ.voltageToDACBits(0.0, dacNumber=i, is16Bits=False)
            exec('self.LJ.getFeedback(u6.DAC{}_8(Value))'.format(i))
        for i in range(20):
            self.LJ.getFeedback(u6.BitDirWrite(i, 0))
        self.LJ.close()
        plt.close('all')
        self.destroy()

if __name__ == '__main__':
    root = MainApp()
    root.mainloop()
