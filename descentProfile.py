import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import requests, json, datetime, time, geocoder, argparse, sys
from scipy import interpolate

class Parachute:
    def __init__(self, name, deployalt, D, m, rated_load=2400, Cd=2.1, L=5):
        self.name = str(name)           #name for graphical purposes
        self.deployalt = deployalt      #Deploy aly /m
        self.area = 0.25*np.pi*D**2     #Diameter of chute /m
        self.mass = m                   #mass of chute /kg
        self.Cd = Cd                    #Coefficient of drag, Fruity chutes approx 2.1
        self.open = 0                   #only used for simple model
        self.lost = False               #tracking if next parachute has opened
        self.deploytime = -1            #time parachute deploys
        self.duration = 1               #simply for graphical puropses
        self.discardtime = -1           #time next parachute opens
        self.rated_load = rated_load    #in lbs - CAUTION
        self.length = L                 #length of shock cord
        self.forces = np.array([0])

drogue = Parachute("Drogue",15000,0.9,0.21)
main = Parachute("Main",2000,4.26,1.7)
parachutes = [drogue,main]

def getAtmDensity(alt):         #returns atmospheric density as a function of altitude
    temp = pressure = 0         #see https://www.grc.nasa.gov/WWW/K-12/airplane/atmosmet.html
    if alt > 25000:
        temp = -131.21 + 0.00299 * alt
        pressure = 2.488 * ((temp + 273.1)/(216.6)) ** (-11.388)
    elif 11000 < alt <= 25000:
        temp = -56.46
        pressure = 22.65 * np.exp(1.73 - 0.000157 * alt)
    else:
        temp = 15.04 - 0.00649 * alt
        pressure = 101.29 * ((temp + 273.1)/288.08) ** (5.256)
    return pressure / (0.2869*(temp + 273.1))

if len(sys.argv) != 1:      #will only perform if command line arguments specified
    parser = argparse.ArgumentParser()
    parser.add_argument('-ia','--initalt',default=15000,type=float,help='apogee altitude')
    parser.add_argument('-t','--dt',default=0.05,       type=float,help='time step')
    parser.add_argument('-m','--mass',default=50,       type=float,help='dry mass at apogee')
    parser.add_argument('-v','--velocity',default=[0,0,0],type=list,help='initial velocity at apogee')
    parser.add_argument('-l','--location',default=geocoder.ip('me').latlng,type=list,help='initial launch [lat, long], as list')
    parser.add_argument('-da','--deployalt',default=1500,type=float,help='altitude main chute opens')
    parser.add_argument('-dD','--drogueD',default=0.9   ,type=float,help='diameter of drogue')
    parser.add_argument('-cD','--chuteD',default=4.86   ,type=float,help='diameter of main chute')
    parser.add_argument('-ot','--opentime',default=2    ,type=float,help='assuming chute opens linearly, what is the duration is secs')
    a = parser.parse_args()

    #command line > local vars
    initalt = a.initalt
    dt = a.dt
    dry_mass = a.mass
    velocity = np.array(a.velocity, dtype='float32')   #m/s
    location = a.location
    chute_deploy_altitude = a.deployalt
    drogue_area = np.pi * (a.drogueD/2)**2   #m^2
    chute_area = np.pi * (a.chuteD/2)**2     #m^2
    chute_open_duration = a.opentime
else:
    #input parameters can be debuggd easily here
    initalt = 15000
    dt = 0.03
    dry_mass = 50
    velocity = np.array([100,0,0], dtype='float32')   #m/s
    location = [52.202541,0.131240]     #geocoder.maxmind('me').latlng - I used all my free quota lol

#initialise simulation
elapsed_time = 0                        #used to extract event timings
position = np.array([0,0,initalt], dtype='float32')    #m
positions = np.array([position])
velocities = np.array([velocity])
accelerations = np.array([0,0,0])       #initially experiencing 'zero-G'

print("Simulation initialised")
while position[2] > 0:                  #run iteration
    force_sum = np.array([0,0,-dry_mass*9.81], dtype='float32') #N
    rho = getAtmDensity(position[2])

    if np.sqrt((np.sum(velocity**2))) != 0:     #check if velocity = [0,0,0]
        unit_velocity = (velocity / np.sqrt((np.sum(velocity**2))))
    else:
        unit_velocity = velocity

    for i, parachute in enumerate(parachutes):
        if position[2] <= parachute.deployalt and parachute.open < 1 and parachute.lost == False:
            if parachute.open == 0:
                parachute.deploytime = elapsed_time

                for j, chute in enumerate(parachutes[:i]):
                    chute.lost = True
                    chute.open = 0
                    chute.discardtime = elapsed_time
                    
            parachute.open += dt/parachute.duration      #assume chute opens linearly
    

        #chute mechanics
        drag = parachute.open*0.5*parachute.Cd*parachute.area*rho*np.linalg.norm(velocity)**2
        force_sum -= drag*unit_velocity
        parachute.forces = np.append(parachute.forces,drag)

    #rocket drag
    rocket_drag = 0.5*0.82*np.pi*0.178**2*rho*np.linalg.norm(velocity)**2
                #0.5 * drag coeff of long cyliner * cross sectional area * density * v^2
    force_sum -= rocket_drag * unit_velocity

    #mechanics
    accel = force_sum/dry_mass
    velocity += accel * dt
    position += velocity * dt
    positions = np.vstack((positions,position))
    velocities = np.vstack((velocities,velocity))
    accelerations = np.vstack((accelerations,accel))

    elapsed_time += dt

parachutes[-1].discardtime = elapsed_time
for parachute in parachutes:
    parachute.index_opens = int(parachute.deploytime/dt)
    parachute.index_lose = int(parachute.discardtime/dt)


def getWind(arguments):             #use balloon descent API to extract x,y position during ascent
    url = 'http://predict.cusf.co.uk/api/v1/?'  #.format(host=socket.gethostbyname("predict.cusf.co.uk"))
    for arg, value in arguments.items():
        url += arg + '=' + str(value) + '&'
    print(url)
    response = requests.get(url)
    json_data = json.loads(response.text)
    # print(json.dumps(json_data,indent=4),url)

    data = []
    for item in (x for x in json_data['prediction'] if x['stage'] == 'descent'):
        inilon, inilat = item['trajectory'][0]['longitude'], item['trajectory'][0]['latitude']  #normalise coordinate system
        # print(init_time)
        for des in item['trajectory']:

            lat = des['latitude']-inilat              #normalise from apogee
            lon = des['longitude']-inilon
            
            x = (6371000+des['altitude'])*np.sin(np.deg2rad(lon))       #sin(x) = x, 6371000m=radius of earth
            y = (6371000+des['altitude'])*np.sin(np.deg2rad(lat))
            data.append([x,y,des['altitude']])

    return np.asarray(data, dtype='float32')  #array in form [x,y,altitude] over time -> need to interpolate

def addWind(positions,dt,deploytime,mypos,launch_date=time.time()):    #add wind component to both stages
    print("Simulation finished, adding wind")
    launch_date = datetime.datetime.fromtimestamp(launch_date).strftime('%Y-%m-%dT%H:%M:%SZ')

    if mypos[0] > 90 or mypos[0] < -90:
        raise ValueError('Latitude out of bounds')
    if mypos[1] < 0 or mypos[1] > 360:
        mypos[1] = mypos[1] % 360

    if dt < 0:
        raise ValueError("Can't have negative time step")
    if deploytime > len(positions)/dt:
        print("Main parachute didn't open")

    info = {                                    #see http://tawhiri.cusf.co.uk/en/latest/api.html for details
        "profile": "standard_profile",
        "launch_latitude": mypos[0],
        "launch_longitude": mypos[1],
        "launch_datetime": launch_date,
        "ascent_rate": 450,
    }
    deploytime = np.clip(deploytime,0,len(positions)/dt)
    index_chute_opens = int(deploytime/dt)

    #wind displacement before chute opens
    tmp = []
    for i, parachute in enumerate(parachutes):
        info['burst_altitude'] = positions[parachute.index_opens,2]
        info['descent_rate'] = -(positions[parachute.index_opens,2] - positions[parachute.index_lose,2] ) / (parachute.deploytime - parachute.discardtime)

        wind = getWind(info)
        xs = interpolate.interp1d(wind[:,2],wind[:,0],bounds_error=False, fill_value='extrapolate',kind='quadratic')(positions[parachute.index_opens:parachute.index_lose,2]).reshape(-1,1)
        ys = interpolate.interp1d(wind[:,2],wind[:,1],bounds_error=False,fill_value='extrapolate',kind='quadratic')(positions[parachute.index_opens:parachute.index_lose,2]).reshape(-1,1)  
        wind_disp = np.hstack((np.hstack((xs,ys)),np.zeros_like(xs)))      #manipulate shape for addition
        tmp.append(wind_disp)
        if i != 0:
            tmp[i] += last_val 
        last_val = wind_disp[-1]
    
    wind_displacements = np.vstack((i for i in tmp))
    wind_displacements = np.vstack((wind_displacements,[last_val,last_val]))

    return np.add(positions,wind_displacements)                   #overestimate on displacement as model is designed for low-mass balloon models
positions = addWind(positions,dt,main.deploytime,mypos=location)

def getShockForces(velocities=velocities):  #assumes canopy mass << dry mass
    for parachute in parachutes:
        ult_tensile_strain = 0.015   #of nylon

        k = (parachute.rated_load*0.454) / (parachute.length * ult_tensile_strain)
        parachute.max_force = np.linalg.norm(velocities[parachute.index_opens])*np.sqrt(k*parachute.mass*dry_mass/(dry_mass+parachute.mass))

    return
getShockForces()

def dataRelease(how='basic',what=[positions,velocities,accelerations]):
    if how == 'basic':
        print("""\n--------------------\nLanding Speed: {speed} m/s\nLanding dist: {distance} m""".format(speed=round(-float(velocity[2]),2),distance=round(np.linalg.norm(positions[-1]))))
        try:
            for i in parachutes:
                print("{} Shock Force: {} N".format(i.name,round(i.max_force,2)))
        except AttributeError:
            pass
        print("--------------------")
    
    elif how == 'writetofile':
        np.savez('descent.npz', what)

    elif how == 'return':
        return what

    return
dataRelease()

def plotAll(total_time,pos3d=positions,vel=velocities,acc=accelerations,tensions=parachutes):       #plot everything
     
    t = np.linspace(0,total_time,len(positions),dtype='float32')
    fig = plt.figure()

    ax = fig.add_subplot(2, 2, 1, projection='3d')
    ax.set_title('Position')
    ax.plot(pos3d[:,0],pos3d[:,1],pos3d[:,2],'r')
    ax.set_xlim([-pos3d[0,2],pos3d[0,2]])
    ax.set_ylim([-pos3d[0,2],pos3d[0,2]])
    ax.text(-2000,pos3d[0,2],0, 'North','x')

    ax = fig.add_subplot(2, 2, 2)
    ax.set_title('Velocity')
    ax.plot(t,vel[:,2])

    ax = fig.add_subplot(2, 2, 3)
    ax.set_title('Acceleration')
    ax.plot(t,acc[:,2],'g')

    ax = fig.add_subplot(2, 2, 4)
    ax.set_title('Line Tensions')
    for i in tensions:
        ax.plot(t,i.forces,label=i.name)
    ax.legend()

    fig.tight_layout()
    plt.show()
    return
plotAll(elapsed_time)