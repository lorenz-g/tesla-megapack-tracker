"""
Converts british national grid to lat lon
Author: Hannah Fry
http://www.hannahfry.co.uk/blog/2012/02/01/converting-british-national-grid-to-latitude-and-longitude-ii

Copied from https://github.com/fmalina/blocl-bnglatlon/blob/main/bng_latlon/bng_to_latlon.py
on 30.12.21
"""

from math import sqrt, pi, sin, cos, tan, atan2

def OSGB36toWGS84(E, N):
    """ Accept The Ordnance Survey National Grid eastings and northings.
    Return latitude and longitude coordinates.

    Usage:
    >>> from bng_to_latlon import OSGB36toWGS84
    >>> OSGB36toWGS84(538890, 177320)
    (51.477795, -0.001402)
    >>> OSGB36toWGS84(352500.2, 401400)
    (53.50713, -2.71766)
    """
    # The Airy 1830 semi-major and semi-minor axes used for OSGB36 (m)
    a, b = 6377563.396, 6356256.909
    F0 = 0.9996012717  # scale factor on the central meridian

    # Latitude and longtitude of true origin (radians)
    lat0 = 49*pi/180
    lon0 = -2*pi/180  # longtitude of central meridian

    # Northing & easting of true origin (m)
    N0, E0 = -100000, 400000
    e2 = 1 - (b*b)/(a*a)  # eccentricity squared
    n = (a-b)/(a+b)

    # Initialise the iterative variables
    lat, M = lat0, 0

    while N-N0-M >= 0.00001:  # Accurate to 0.01mm
        lat = (N-N0-M)/(a*F0) + lat
        M1 = (1 + n + (5./4)*n**2 + (5./4)*n**3) * (lat-lat0)
        M2 = (3*n + 3*n**2 + (21./8)*n**3) * sin(lat-lat0) * cos(lat+lat0)
        M3 = ((15./8)*n**2 + (15./8)*n**3) * sin(2*(lat-lat0)) * cos(2*(lat+lat0))
        M4 = (35./24)*n**3 * sin(3*(lat-lat0)) * cos(3*(lat+lat0))
        # meridional arc
        M = b * F0 * (M1 - M2 + M3 - M4)

    # transverse radius of curvature
    nu = a*F0/sqrt(1-e2*sin(lat)**2)

    # meridional radius of curvature
    rho = a*F0*(1-e2)*(1-e2*sin(lat)**2)**(-1.5)
    eta2 = nu/rho-1

    sec_lat = 1./cos(lat)
    VII = tan(lat)/(2*rho*nu)
    VIII = tan(lat)/(24*rho*nu**3)*(5+3*tan(lat)**2+eta2-9*tan(lat)**2*eta2)
    IX = tan(lat)/(720*rho*nu**5)*(61+90*tan(lat)**2+45*tan(lat)**4)
    X = sec_lat/nu
    XI = sec_lat/(6*nu**3)*(nu/rho+2*tan(lat)**2)
    XII = sec_lat/(120*nu**5)*(5+28*tan(lat)**2+24*tan(lat)**4)
    XIIA = sec_lat/(5040*nu**7)*(61+662*tan(lat)**2+1320*tan(lat)**4+720*tan(lat)**6)
    dE = E-E0

    # These are on the wrong ellipsoid currently: Airy 1830 (denoted by _1)
    lat_1 = lat - VII*dE**2 + VIII*dE**4. - IX*dE**6.
    lon_1 = lon0 + X*dE - XI*dE**3 + XII*dE**5. - XIIA*dE**7.

    # Want to convert to the GRS80 ellipsoid.
    # First convert to cartesian from spherical polar coordinates
    H = 0  # Third spherical coord.
    x_1 = (nu/F0 + H)*cos(lat_1)*cos(lon_1)
    y_1 = (nu/F0 + H)*cos(lat_1)*sin(lon_1)
    z_1 = ((1-e2)*nu/F0 + H)*sin(lat_1)

    # Perform Helmut transform (to go between Airy 1830 (_1) and GRS80 (_2))
    s = -20.4894*10**-6  # The scale factor -1
    # The translations along x, y, z axes respectively
    tx, ty, tz = 446.448, -125.157, + 542.060
    # The rotations along x, y, z respectively (in seconds)
    rxs, rys, rzs = 0.1502, 0.2470, 0.8421

    # convert seconds to radians
    def sec_to_rad(x): return x*pi/(180*3600.)

    rx, ry, rz = [sec_to_rad(x) for x in (rxs, rys, rzs)]  # (in radians)
    x_2 = tx + (1+s)*x_1 + (-rz)*y_1 + (ry)*z_1
    y_2 = ty + (rz)*x_1 + (1+s)*y_1 + (-rx)*z_1
    z_2 = tz + (-ry)*x_1 + (rx)*y_1 + (1+s)*z_1

    # Back to spherical polar coordinates from cartesian
    # Need some of the characteristics of the new ellipsoid

    # The GSR80 semi-major and semi-minor axes used for WGS84(m)
    a_2, b_2 = 6378137.000, 6356752.3141
    e2_2 = 1 - (b_2*b_2)/(a_2*a_2)  # The eccentricity of the GRS80 ellipsoid
    p = sqrt(x_2**2 + y_2**2)

    # Lat is obtained by an iterative proceedure:
    lat = atan2(z_2, (p*(1-e2_2)))  # Initial value
    latold = 2*pi
    while abs(lat - latold) > 10**-16:
        lat, latold = latold, lat
        nu_2 = a_2/sqrt(1-e2_2*sin(latold)**2)
        lat = atan2(z_2+e2_2*nu_2*sin(latold), p)

    # Lon and height are then pretty easy
    lon = atan2(y_2, x_2)
    H = p/cos(lat) - nu_2

    # Uncomment this line if you want to print the results
    # print([(lat-lat_1)*180/pi, (lon - lon_1)*180/pi])

    # Convert to degrees
    lat = lat*180/pi
    lon = lon*180/pi

    # Job's a good'n.
    return round(lat, 6), round(lon, 6)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

    import csv

    # Read in from a file
    BNG = csv.reader(open('BNG.csv', 'rU'), delimiter=',')
    next(BNG)

    # Get the output file ready
    #changes made because of: #https://stackoverflow.com/questions/3348460/csv-file-written-with-python-has-blank-lines-between-each-row
    output_file = open('BNGandLatLon.csv', 'w+', newline='')
    output = csv.writer(output_file, delimiter=',')
    output.writerow(['Lat', 'Lon', 'E', 'N'])

    # Loop through the data
    for E, N in BNG:
        lat, lon = OSGB36toWGS84(float(E), float(N))
        output.writerow([str(lat), str(lon), str(E), str(N)])
    # Close the output file
    output_file.close()


# To Do
# # common importable constants and separate util functions (Helmut transform...)
# # CLI to accept filename or value pair as args
