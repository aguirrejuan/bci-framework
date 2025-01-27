from bci_framework.extensions.visualizations import EEGStream
from bci_framework.extensions.data_analysis import Feedback, marker_slicing
from bci_framework.extensions import properties as prop

import logging
import numpy as np
from datetime import datetime
import seaborn as snb

from scipy.signal import savgol_filter

from simple_pid import PID

MAX_LATENCY = 150
BUFFER = 15

pid = PID(Kp=0.7, Ki=0.07, Kd=0.0001, setpoint=0,
          sample_time=None, output_limits=(-MAX_LATENCY, MAX_LATENCY))
# pid = PID(Kp=1, Ki=0.07, Kd=0.0001, setpoint=0,
          # sample_time=None, output_limits=(-MAX_LATENCY, MAX_LATENCY))
# pid = PID(Kp=1, Ki=0.4, Kd=0.05, setpoint=0,
          # sample_time=None, output_limits=(-MAX_LATENCY, MAX_LATENCY))
# pid = PID(Kp=1, Ki=0.07, Kd=0.01, setpoint=0,
          # sample_time=None, output_limits=(-MAX_LATENCY, MAX_LATENCY))


########################################################################
class Stream(EEGStream):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """"""
        super().__init__(*args, **kwargs)
        
        
        self.feedback = Feedback(self, 'SetLatency')
        # self.feedback.on_feedback(self.on_feedback)

        # self.N = int(prop.SAMPLE_RATE / prop.STREAMING_PACKAGE_SIZE)

        self.axis_wave = self.add_subplot(221)
        self.axis_hist = self.add_subplot(223)
        self.axis_log = self.add_subplot(222)
        self.axis_time = self.add_subplot(224)

        self.subplots_adjust(hspace=0.3)

        # self.wave_line = self.axis_wave.plot([0], [0])[0]
        # self.wave_line2 = self.axis_wave.vline()[0]

        self.latency_time = self.axis_time.plot(
            [0], [0], linewidth=3, linestyle='', marker='x', color='k')[0]
        self.latency_time_filtered = self.axis_time.plot([0], [0], color='C0')[
            0]

        self.timestamp_rises = np.array([])

        self.markers_timestamps = []

        self.latencies = [0]
        self.latency_correction = 0

        self.frames_names()
        self.create_buffer(BUFFER, resampling=1000, fill=-1, aux_shape=2)
        
        self.stream()

    # ----------------------------------------------------------------------
    def get_rises(self, data, timestamp):
        """"""
        data = data.copy()

        data[data >= 0.5] = 1
        data[data < 0.5] = 0

        diff = np.diff(data, prepend=0)
        diff[diff < 0] = 0
        diff[0] = 0
        diff[-1] = 0

        return timestamp[np.nonzero(diff)[0]], diff

    # ----------------------------------------------------------------------
    def frames_names(self):
        """"""
        self.axis_wave.set_title('Event synchronization')
        self.axis_wave.set_xlabel('Time [ms]')
        self.axis_wave.set_ylabel('Amplitude')
        self.axis_wave.grid(True)

        self.axis_time.set_title('Latency timeline')
        self.axis_time.set_xlabel('Samples analyzed')
        self.axis_time.set_ylabel('Latency (ms)')
        self.axis_time.grid(True)

        self.axis_log.axis('off')

        self.axis_hist.set(
            xlabel='Latency [ms]', ylabel='Count', title='Latency histogram')
        self.axis_hist.grid(True)

    # ----------------------------------------------------------------------
    @marker_slicing(['MARKER'], t0=-1, t1=1)
    def stream(self, aux, timestamp, marker, marker_datetime):
        """"""
        latencies = np.array(self.latencies)

        if latencies.size > 5:
            latencies = latencies[3:]

            Q1 = np.quantile(latencies, 0.25)
            Q3 = np.quantile(latencies, 0.75)
            IQR = Q3 - Q1
            latencies = latencies[latencies < (Q3 + 1.5 * IQR)]
            latencies = latencies[latencies > (Q1 - 1.5 * IQR)]

        latencies = latencies[-60:]
        # LATENCY = np.mean(latencies)

        # Rise plot
        self.axis_wave.clear()
        aux = aux[0]
        aux[aux == -1] = aux[-1]
        aux = aux - aux.min()
        aux = aux / aux.max()
        self.axis_wave.set_ylim(-0.1, 1.1)
        self.axis_wave.set_xlim(-1, 1)

        self.axis_wave.set(
            xlabel='Time [ms]', ylabel='Amplitude', title='Event synchronization')

        self.axis_wave.grid(True)

        self.timestamp_rises, diff = self.get_rises(aux, timestamp)

        if self.timestamp_rises.size > 0:
            v = np.argmin(np.abs(timestamp - self.timestamp_rises[0]))
            window = aux[int(v - prop.SAMPLE_RATE * 0.3) : int(v + prop.SAMPLE_RATE * 0.3)]
            t = np.linspace(-300, 300, window.shape[0])
            self.axis_wave.plot(t, window, label='input signal')[0]

            self.axis_wave.vlines([0], -1, 2, color='k',
                                  linestyle='--', label='event')

            self.axis_wave.vlines([np.mean(latencies)], -1, 2, color='r', linestyle='--',
                                  label='mean latency')
            self.axis_wave.vlines([latencies[-1]], -1, 2, color='g', linestyle='--',
                                  label='last latency')
            self.axis_wave.legend(loc=4)
            self.axis_wave.set_xlim(-150, +150)

        # Histogram
        if latencies.size > 5:
            self.axis_hist.clear()
            self.axis_hist.grid(True, zorder=0)
            snb.histplot(latencies, kde=True,
                         ax=self.axis_hist, zorder=10)
            self.axis_hist.set(
                xlabel='Latency [ms]', ylabel='Count', title='Latency histogram')

        # Latencies
        if latencies.size > 3:
            t = range(len(latencies))
            self.latency_time.set_data(t, latencies)
            self.axis_time.set_xlim(0, t[-1])
            self.axis_time.set_ylim(
                min([latencies.min(), -50]), max([latencies.max(), 50]))

            if latencies.size > 25:
                latencies_filtered = savgol_filter(latencies, 15, 5)
                self.latency_time_filtered.set_data(t, latencies_filtered)
            # plt.plot()

        self.axis_log.clear()
        self.axis_log.axis('off')

        if latencies.size > 1:

            for i, text in enumerate([
                ('count', f'{len(self.latencies)}'),
                ('mean', f'{np.mean(latencies):.3f} ms'),
                ('jitter', f'{np.std(latencies):.3f} ms'),
                ('median', f'{np.median(latencies):.3f} ms'),
                # ('std', f'{np.std(latencies):.3f}'),
                ('range', f'{latencies.max()-latencies.min():.3f} ms'),
                # ('var', f'{latencies.var():.3f}'),
                ('min', f'{latencies.min():.3f} ms'),
                ('max', f'{latencies.max():.3f} ms'),
                ('latency correction', f'{self.latency_correction:.3f} ms'),
                ('error',
                 f'$\pm${abs(latencies.max()-latencies.min())/2:.3f} ms'),
            ]):

                self.axis_log.text(
                    10, 25 - 2 * i, f'{text[0]}:', fontdict={'weight': 'bold', 'size': 16, 'ha': 'right'})

                self.axis_log.text(
                    11, 25 - 2 * i, text[1], fontdict={'size': 16, })

        self.axis_log.set_xlim(0, 30)
        self.axis_log.set_ylim(0, 30)

        if self.timestamp_rises.size > 0:
            latency = (self.timestamp_rises - marker_datetime) * 1000
            self.latencies.append(latency.min())

        self.feed()
        self.latency_correction = pid(np.mean(self.latencies[-5:]))

        self.feedback.write({'name': 'set_latency',
                            'value': self.latency_correction,
                            })


if __name__ == '__main__':
    Stream(enable_produser=True)


















