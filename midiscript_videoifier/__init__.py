import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Sarasa Mono SC'
plt.rcParams['font.size'] = 10.5  # 10.5pt 五号字；9pt 小五号字
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['figure.subplot.left'] = 0.11  #0.05
plt.rcParams['figure.subplot.right'] = 0.89  #0.98
plt.rcParams['figure.subplot.bottom'] = 0.15  #0.1
plt.rcParams['figure.subplot.top'] = 0.91  #0.93
plt.rcParams['figure.facecolor'] = (1, 1, 1, 0)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['axes.facecolor'] = (1, 1, 1, 0)
plt.rcParams['axes.titlesize'] = 'medium'
plt.rcParams['legend.fontsize'] = 'medium'
plt.rcParams['interactive'] = 'False'

from .base.components import Paragraph, MidiPattern
from .base.script import Script
from .base.movie import Movie
