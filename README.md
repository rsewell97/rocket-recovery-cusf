# CUSF Rocket 2-Stage Parachute Descent Model

A lightweight simulator to model the descent of amateur rockets using live wind data. Work in progress

A call is made to the CUSF balloon flight path predictor API, details can be found [here](http://tawhiri.cusf.co.uk/en/latest/api.html). A sample API response can be seen [here](http://predict.cusf.co.uk/api/v1/?profile=standard_profile&launch_latitude=53.059&launch_longitude=356.8012&launch_datetime=2018-10-20T19:22:18Z&ascent_rate=450&burst_altitude=15000.0&descent_rate=36.0063897763674) and the descent vlues are zeroed, interpolated and added to the original simulation. NB: This assumes the rocket is a [linear system](https://en.wikipedia.org/wiki/Linear_system) which may not necessarily be the case.

The model in `descentProfile.py` assumes two stages of parachutes will be used, a drogue and a main chute. The parameters of each chute, the rocket, initial conditions and more can be altered to tailor the model for most needs. 

The function `dataRelease(type,what=[positions,velocities,accelerations])` allows customised output data to be debugged, written to file, or returned.

The function `plotAll(total_time)` automatically plots positions, velocity, acceleration and parachute tensions over time on a single matplotlib figure.

## Future Plans

Not in any particular order

- [x] Create a command line argument parser
- [x] Fix bug when velocity == 0
- [x] Add drag to rocket
- [ ] More accurately model snatch load mechanics robustly - model tests likely
- [ ] Quantify wind effect on rocket dependant on mass 
- [ ] Add rocket orientaion physics


## Command Line Arguments

Please note: if one argument is specified, all others must too, or they will be set to default values as seen in `descentProfile.py` 

```
usage: descentProfile.py [-h] [-ia INITALT] [-t DT] [-m MASS] [-v VELOCITY]
                         [-l LOCATION] [-da DEPLOYALT] [-dD DROGUED]
                         [-cD CHUTED] [-ot OPENTIME]

optional arguments:
  -h, --help            show this help message and exit
  -ia INITALT, --initalt INITALT
                        apogee altitude
  -t DT, --dt DT        time step
  -m MASS, --mass MASS  dry mass at apogee
  -v VELOCITY, --velocity VELOCITY
                        initial velocity at apogee
  -l LOCATION, --location LOCATION
                        initial launch [lat, long], as list
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
