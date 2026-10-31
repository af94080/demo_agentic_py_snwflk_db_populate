# Usage

### 1. Run the script from the command line

***python3 3_build_demo_dbs_in_snwflk.py***

### 2. Send the output to a log file

***python3 -u 3_build_demo_dbs_in_snwflk.py >> build_demo_dbs_log_103126_1228.txt 2>&1***

***python3 -u 3_build_demo_dbs_in_snwflk.py > logs/3_build_demo_dbs_in_snwflk_log_$(date +%m%d%y_%H%M).txt 2>&1***

### 3. Describe the databases you'd like the agent to build

<sub>To choose which databases get built, edit the request text inside `run_agent(...)` at the bottom of `3_build_demo_dbs_in_snwflk.py`, under `if __name__ == "__main__":`.</sub>

<sub>Write it in plain English, for example: `run_agent("Build three demo databases: sales, retail, and log_processing.")`</sub>

<sub>The prefix `demo_oct_31_` is added automatically, so you get names like `DEMO_OCT_31_SALES`.</sub>

### 4. Run the evaluation script

***python3 -u 4_eval_dbs.py > logs/eval_dbs_log_$(date +%m%d%y_%H%M).txt 2>&1***
