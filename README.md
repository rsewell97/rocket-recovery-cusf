# rocket-recovery-cusf 

A lightweight simulator to model the descent of amateur rockets using live wind data. Work in progress

A call is made to the CUSF balloon flight path predictor API, details can be found [here](http://tawhiri.cusf.co.uk/en/latest/api.html)

The model in `descentProfile.py` assumes two stages of parachutes will be used, a drogue and a main chute. The parameters of each chute, the rocket weight, initial conditions and more can be altered to tailor the model for most needs. 


### Setup

```
pip install -r "requirements.txt"
python descentProfile.py
```

### Future Plans

- [ ] Add a command line interface
- [ ] More accurately model snatch load mechanics robustly
- [ ] Add drag to rocket
- [ ] Quantify wind effect on rocket dependant mass
- [ ] Add rocket orientaion physics
- [ ] Fix bug when velocity == 0

Please message me if you have other suggestions

~Robbie
