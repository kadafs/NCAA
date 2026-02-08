import os
import sys
from utils.ssl_adapter import get_robust_session

def dump_8_keys():
    url = "https://ncaa-api-w2ry.onrender.com/stats/odds/ncaa?date=2026-02-07"
    session = get_robust_session(retries=5)
    
    data = session.get(url).json()
    
    keys = [
        "nebraska cornhuskers vs rutgers scarlet knights",
        "ole miss rebels vs texas longhorns",
        "alcorn state braves vs arkansas-pine bluff golden lions",
        "gardner-webb runnin' bulldogs vs presbyterian blue hose",
        "buffalo bulls vs south alabama jaguars",
        "austin peay governors vs north alabama lions",
        "incarnate word cardinals vs mcneese state cowboys"
    ]
    
    for k in keys:
        print(f"{k}: {data.get(k)}")

if __name__ == "__main__":
    dump_8_keys()
