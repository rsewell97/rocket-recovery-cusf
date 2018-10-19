import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import socket, requests, json, datetime, time, geocoder, math
from scipy import interpolate

def getAtmDensity(alt):          #returns atmospheric density as a function of altitude
    temp = pressure = 0.0           #see https://www.grc.nasa.gov/WWW/K-12/airplane/atmosmet.html
    if alt > 25000:
        temp = -131.21 + 0.00299 * alt
        pressure = 2.488 * ((temp + 273.1)/(216.6)) ** (-11.388)
    elif 11000 < alt <= 25000:
        temp = -56.46
        pressure = 22.65 * math.exp(1.73 - 0.000157 * alt)
    else:
        temp = 15.04 - 0.00649 * alt
        pressure = 101.29 * ((temp + 273.1)/288.08) ** (5.256)
    return pressure / (0.2869*(temp + 273.1))

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

def addWind(positions,dt,chute_deploy_time,mypos=geocoder.ip('me').latlng,launch_date=time.time()):    #add wind component to both stages
    launch_date = datetime.datetime.fromtimestamp(launch_date).strftime('%Y-%m-%dT%H:%M:%SZ')

    if mypos[0] > 90 or mypos[0] < -90:
        raise ValueError('Latitude out of bounds')

    info = {                                    #see http://tawhiri.cusf.co.uk/en/latest/api.html for details
        "profile": "standard_profile",
        "launch_latitude": mypos[0],
        "launch_longitude": mypos[1],
        "launch_datetime": launch_date,
        "ascent_rate": 450,
    }
    chute_deploy_time = np.clip(chute_deploy_time,0,len(positions)/dt)
    index_chute_opens = int(chute_deploy_time/dt)

    #wind displacement before chute opens
    info['burst_altitude'] = positions[0,2]
    info['descent_rate'] = (positions[0,2] - positions[index_chute_opens,2] )/ chute_deploy_time
    wind = getWind(info)
    xs = interpolate.interp1d(wind[:,2],wind[:,0],bounds_error=False, fill_value='extrapolate',kind='quadratic')(positions[:index_chute_opens,2]).reshape(-1,1)
    ys = interpolate.interp1d(wind[:,2],wind[:,1],bounds_error=False,fill_value='extrapolate',kind='quadratic')(positions[:index_chute_opens,2]).reshape(-1,1)
    wind_disp1 = np.hstack((np.hstack((xs,ys)),np.zeros_like(xs)))      #manipulate shape for addition
    last_val = wind_disp1[-1]
    wind_disp1 = np.vstack((wind_disp1,np.zeros((len(positions)-len(wind_disp1),3))))


    #wind displacement after chute opens
    info['descent_rate'] = positions[index_chute_opens,2] / (elapsed_time - chute_deploy_time)
    info['burst_altitude'] = positions[index_chute_opens,2]
    wind = getWind(info)
    xs = interpolate.interp1d(wind[:,2],wind[:,0],bounds_error=False,fill_value='extrapolate',kind='quadratic')(positions[index_chute_opens:,2]).reshape(-1,1)
    ys = interpolate.interp1d(wind[:,2],wind[:,1],bounds_error=False,fill_value='extrapolate',kind='quadratic')(positions[index_chute_opens:,2]).reshape(-1,1)

    wind_disp2 = np.hstack((np.hstack((xs,ys)),np.zeros_like(xs)))      #manipulate shape for addition
    wind_disp2 = np.vstack((np.zeros((len(positions)-len(wind_disp2),3)),np.add(wind_disp2,np.subtract(last_val,wind_disp2[0])))) 

    wind = np.add(wind_disp1,wind_disp2) * 1.0      #factor sets wind effect

    return np.add(positions,wind)                   #overestimate on displacement as model is designed for low-mass balloon models

init_alt = 15000
position = np.array([0,0,init_alt], dtype='float32')    #m
velocity = np.array([0,0,0], dtype='float32')           #m/s

dt = 0.05                               #s
dry_mass = 50                           #kg
drogue_drag_coeff = 2.2                 #perhaps optimistic
drogue_area = np.pi * 0.45**2           #m^2
chute_drag_coeff = 2.2                  #perhaps optimistic
chute_area = np.pi * 2.43**2            #m^2
chute_deployment_duration = 2           #s     assume chute opens linearly - work around but pretty good estimate


drogue_open = 1                         #initially deployed at apogee (start)          
chute_open = 0                          #initially not deployed
chute_deployment_altitude = 1500        #m
elapsed_time = 0                        #to extract event timings
positions = np.array([position])
velocities = np.array([velocity])
accelerations = np.array([0,0,0])       #initially experiencing 'zero-G'
drogue_force = np.array([0])            #likewise
chute_force = np.array([0])             #likewise

while position[2] > 0:                  #run iteration
    force_sum = np.array([0,0,-dry_mass*9.81], dtype='float32') #N
    rho = getAtmDensity(position[2])

    if np.sqrt((np.sum(velocity**2))) != 0:     #check if velocity != [0,0,0]
        unit_velocity = (velocity / np.sqrt((np.sum(velocity**2))))
    else:
        unit_velocity = velocity

    if position[2] < chute_deployment_altitude and chute_open < 1:
        chute_open += dt/chute_deployment_duration      #assume chute opens linearly
        chute_deploy_time = elapsed_time
        drogue_open = 0

    #drogue mechanics
    d_drag = drogue_open*0.5*drogue_drag_coeff*drogue_area*rho*np.linalg.norm(velocity)**2
    force_sum -= d_drag*unit_velocity
    drogue_force = np.vstack((drogue_force,[d_drag]))

    #parachute mechanics
    c_drag = chute_open*0.5*chute_drag_coeff*chute_area*rho*np.linalg.norm(velocity)**2
    force_sum -= c_drag*unit_velocity
    chute_force = np.vstack((chute_force,[c_drag]))

    #rocket drag mechanics
    rocket_drag = 0.5*0.82*np.pi*0.178**2*rho*np.linalg.norm(velocity)**2
                #0.5 * drag coeff of cyliner * cross sectional area * density * v^2
    force_sum -= rocket_drag*unit_velocity

    #linear mechanics
    accel = force_sum/dry_mass
    velocity += accel * dt
    position += velocity * dt

    positions = np.vstack((positions,position))
    velocities = np.vstack((velocities,velocity))
    accelerations = np.vstack((accelerations,accel))

    elapsed_time += dt

positions = addWind(positions,dt,chute_deploy_time)

def dataRelease(how='basic',what=[positions,velocities,accelerations]):
    if how == 'basic':
        print("""
        --------------------
        Landing Speed: {speed} m/s
        Landing dist: {distance} m
        Chute Shock Force: {shock} N
        Drogue Max Force: {drogue_max} N
        Maximum acceleration: {max_a} m/s^2 or {g}G
        --------------------
        """.format(speed=round(-float(velocity[2]),2),
        distance=round(np.linalg.norm(positions[-1])),
        shock=round(np.max(chute_force),2),
        drogue_max=round(np.max(drogue_force),2),
        max_a=round(np.max(accelerations[:,2]),2),
        g=round(np.max(accelerations[:,2]/9.81),2)))
    
    elif how == 'writetofile':
        np.savez('descent.npz', what)

    elif how == 'return':
        return what

    return
dataRelease()

def plotAll(total_time,pos3d=positions,vel=velocities,acc=accelerations,d_f=drogue_force,c_f=chute_force):       #plot everything
     
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
    ax.plot(t,d_f)
    ax.plot(t,c_f)

    fig.tight_layout()
    plt.show()
    return
plotAll(elapsed_time)