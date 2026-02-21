# sovereign_launch.pyw — Silent launcher (geen console venster)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sovereign_app import SovereignDashboard

app = SovereignDashboard()
app.mainloop()
