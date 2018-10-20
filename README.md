# rocket-recovery-cusf 

A lightweight simulator to model the descent of amateur rockets using live wind data. Work in progress

A call is made to the CUSF balloon flight path predictor API, details can be found [here](http://tawhiri.cusf.co.uk/en/latest/api.html)

The model in `descentProfile.py` assumes two stages of parachutes will be used, a drogue and a main chute. The parameters of each chute, the rocket, initial conditions and more can be altered to tailor the model for most needs. 

### Setup

```
pip install -r "requirements.txt"
python descentProfile.py
```

### Future Plans

Not in any particular order

- [x] Create a command line argument parser
- [ ] More accurately model snatch load mechanics robustly
- [x] Add drag to rocket
- [ ] Quantify wind effect on rocket dependant mass
- [ ] Add rocket orientaion physics
- [x] Fix bug when velocity == 0

### Command Line Arguments

```
usage: descentProfile.py [-h] [-ia INITALT] [-t DT] [-m MASS] [-v VELOCITY]
                         [-da DEPLOYALT] [-dD DROGUED] [-cD CHUTED]
                         [-ot OPENTIME]

optional arguments:
  -h, --help            show this help message and exit
  -ia INITALT, --initalt INITALT
                        apogee altitude
  -t DT, --dt DT        time step
  -m MASS, --mass MASS  dry mass at apogee
  -v VELOCITY, --velocity VELOCITY
                        initial velocity at apogee
  -da DEPLOYALT, --deployalt DEPLOYALT
                        altitude main chute opens
  -dD DROGUED, --drogueD DROGUED
                        diameter of drogue
  -cD CHUTED, --chuteD CHUTED
                        diameter of main chute
  -ot OPENTIME, --opentime OPENTIME
                        assuming chute opens linearly, what is the duration is
                        secs
```

Please message me if you have other suggestions

~Robbie
