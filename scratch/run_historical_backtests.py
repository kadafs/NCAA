import sys
import os

sys.path.insert(0, 'mlb')
from consensus_f5_v1 import generate_v1_report
from consensus_f5 import generate_consensus_report

print("Running V1 for 06/06/2026...")
generate_v1_report(date_str='06/06/2026')
os.rename('mlb/consensus_f5_v1_report.md', 'mlb/consensus_f5_v1_report_06-06.md')

print("Running Current for 06/06/2026...")
generate_consensus_report(date_str='06/06/2026')

print("Running V1 for 06/07/2026...")
generate_v1_report(date_str='06/07/2026')
os.rename('mlb/consensus_f5_v1_report.md', 'mlb/consensus_f5_v1_report_06-07.md')

print("Running Current for 06/07/2026...")
generate_consensus_report(date_str='06/07/2026')

print("ALL DONE!")
