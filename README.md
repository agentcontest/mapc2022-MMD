# MMD Team

## Python-mapc2020
__This version uses a modified version of the [python-mapc2020 libary](https://github.com/agentcontest/python-mapc2020).__
Minor adjustments were made to handle transmission between simulations and to be able to read the whole dynamic percept in the summer of 2022.

## Python
This version requires `Python 3.10.0 `and `pip 22.0.0` or higher installed and working properly.
Required libraries included in *requirements.txt* file.

## How to run
Use *main.py* from the root, where the host, port, team and the password should be added to connect to the server. For debugging, use the explain parameter (which will show what the agents are doing during the simulation).
```console
python .src\main.py --host 127.0.0.1 --port 12300 --team A --pw 1 [--explain]
```