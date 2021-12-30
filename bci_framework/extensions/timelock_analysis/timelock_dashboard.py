import os
import math
import random
from string import ascii_lowercase

from PySide6.QtUiTools import QUiLoader


########################################################################
class TimelockDashboard:
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, height, default_scale=0.6):
        """Constructor"""
        self.height = height
        self.default_scale = default_scale
        ui = os.path.realpath(os.path.join(
            os.environ['BCISTREAM_ROOT'], 'framework', 'qtgui', 'locktime_widget.ui'))
        self.widget = QUiLoader().load(ui)
        self.widget.setProperty('class', 'dashboard')
        self.widget.label_title.setText('')
        self.widget.gridLayout.setVerticalSpacing(30)
        self.widget.gridLayout.setContentsMargins(30, 0, 30, 30)

        self.columns = 1

    # ----------------------------------------------------------------------
    def add_widgets(self, *widgets):
        """"""
        analyzers = []
        max_r = 0
        max_c = 0
        i = 0
        for analyzer, w in widgets:

            height = w.get('scale', self.default_scale)

            name = ''.join([random.choice(ascii_lowercase)
                            for i in range(8)])
            setattr(self, name, analyzer(self.height * height))
            analyzer = getattr(self, name)
            analyzer.widget.label_title.setText(w.get('title', ''))
            analyzer.widget.setProperty('class', 'timelock')
            analyzer.widget.setContentsMargins(30, 30, 30, 30)
            analyzer._add_spacers()

            if analyzers:
                analyzer.previous_pipeline(analyzers[-1])
                analyzers[-1].next_pipeline(analyzer)

            print((i % self.columns, math.floor(i / self.columns)))

            self.widget.gridLayout.addWidget(analyzer.widget,
                                             math.floor(i / self.columns),
                                             (i % self.columns),  # col
                                             1, 1,  # spans
                                             )
            analyzers.append(analyzer)

            i += 1

        for c in range(self.columns):
            self.widget.gridLayout.setColumnStretch(c, 1)

        # self.widget.gridLayout.setColumnStretch(2, 1)

        # for i in range(max_r):
            # self.widget.gridLayout.setRowStretch(i, 0)
