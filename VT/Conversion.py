import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d

data = pd.read_csv('Pressure_to_Voltage.csv')

for col in data.columns:
    if 'Time' in col:
        data[col] = data[col] - data.loc[0, col]

ft = np.array(data['Full Range Time'])
fv = np.array(data['Full Range Value'])
ct = np.array(data['Convectron Time'])
cv = np.array(data['Convectron Value'])
bt = np.array(data['Baratron Time'])
bv = np.array(data['Baratron Value'])

fv = fv[ft>190]
ft = ft[ft>190]
ft = ft[fv<10.]
fv = fv[fv<10.]
cv = cv[ct>190]
ct = ct[ct>190]
ct = ct[cv<10.]
cv = cv[cv<10.]
bv = bv[bt>190]
bt = bt[bt>190]
bt = bt[bv<10.]
bv = bv[bv<10.]

# fig, ax = plt.subplots()
# ax.semilogy(ft, fv)
# ax.semilogy(ct, cv)

time = np.linspace(bt[0], bt[-1], 100)
fig, ax = plt.subplots()
f1 = interp1d(ct, cv, fill_value='extrapolate')
f2 = interp1d(bt, bv, fill_value='extrapolate')
idx = np.argsort(f2(time))
ax.semilogy(f2(time), f1(time), '-*')
z = np.polyfit(f2(time)[1:], f1(time)[1:], 2)
f = np.poly1d(z)
print(f)
ax.plot(f2(time), f(f2(time)))


# true = [0, .1e-3, .2e-3, .5e-3, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3, 1, 2, 5, 10, 20, 50, 100, 200, 300, 400, 500, 600, 700, 760, 800, 900, 1000]
# indicated = [0., .1e-3, .2e-3, .5e-3, .7e-3, 1.4e-3, 3.3e-3, 6.6e-3, 13.1e-3, 32.4e-3, 64.3e-3, 126e-3, 312e-3, 600e-3, 1.14, 2.45, 4.00, 5.80, 7.85, 8.83, 9.79, 11.3, 13.5, 16.1, 18.8, 21.8, 23.7, 25.1, 28.5, 32.5]

# plt.loglog(indicated, true)

plt.show()
