import pandas as pd
import math


# gets number of days from date to last date +1 in dataset
def nodaysto2019(date):
    year = int(date[-4:])
    month = int(date[-7:-5])
    day = int(date[:-8])
    daysinmonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthtodays = 0
    for i in range(month-1):
        monthtodays += daysinmonth[i]
    days = (year*365)+monthtodays+day
    return 737034-days


# get training data
housingData = pd.read_csv(r"HousePriceDataTRAINING.csv")

# assigns a days to 2019 on every house
housingData["Days to 2019"] = [nodaysto2019(x) for x in housingData["Date"]]

#  adjusts price for inflation
housingData["Adjusted Price"] = [round(x*y**0.00011) for x, y in zip(housingData["Price"], housingData["Days to 2019"])]


# Split the data for every No of bedrooms
def getData(bedroomsin):
    Data = {"Latitude": [], "Longitude": [], "Date": [], "Price": [], "Bedrooms": [], "OgIndex": []}
    for i, row in housingData.iterrows():
        bedrooms = row["Bedrooms"]
        if bedrooms == bedroomsin:
            Data["Latitude"].append(row["Latitude"])
            Data["Longitude"].append(row["Longitude"])
            Data["Date"].append(row["Date"])
            Data["Price"].append(row["Price"])
            Data["Bedrooms"].append(row["Bedrooms"])
            Data["OgIndex"].append(i)
    return Data


# makes a dataframe for each bedroom (this part takes a while)
columnNames = ["Latitude", "Longitude", "Date", "Price", "Bedrooms", "OgIndex"]
DF1 = pd.DataFrame(getData(1), columns=columnNames)
DF2 = pd.DataFrame(getData(2), columns=columnNames)
DF3 = pd.DataFrame(getData(3), columns=columnNames)
DF4 = pd.DataFrame(getData(4), columns=columnNames)
DF5 = pd.DataFrame(getData(5), columns=columnNames)
DF6 = pd.DataFrame(getData(6), columns=columnNames)

bedroomDFDicList = [DF1, DF2, DF3, DF4, DF5, DF6]
for df in bedroomDFDicList:
    indexList = []
    for i, row in df.iterrows():
        indexList.append(i)
    df["Index"] = indexList


# func to check a house is in radius
def inradius(xin, yin, x, y, radius):
    if abs(xin-x) > radius:
        return False
    if abs(yin-y) > radius:
        return False
    return True


# gets houses close to current house
def gethousesaround(xin, yin, df):
    radius = 1  # Starting radius for search
    housescloselist = [[i, x, y] for x, y, i in zip(df["Latitude"], df["Longitude"], df["Index"]) if
                       inradius(xin, yin, x, y, radius)]
    length = len(housescloselist)
    if length > 20000:
        radius = 0.7
        # [index, latitude, longitude]
        housescloselist = [i for i in housescloselist if inradius(xin, yin, i[1], i[2], 0.7)]
    increment = 0.25
    while length > 200:
        radius -= increment
        newlist = [i for i in housescloselist if inradius(xin, yin, i[1], i[2], radius)]
        newlen = len(newlist)
        if newlen < 30:
            radius += increment
            increment -= increment/2
        else:
            housescloselist = newlist.copy()
            length = newlen
    return housescloselist


# func to get distance between 2 houses
def getdistance(xin, yin, x, y):
    return math.sqrt((xin - x) ** 2) + ((yin - y) ** 2)


# func to get closest N houses from the list of houses in radius
def getnclosest(n, distancelist):
    closestlist = []
    for i in range(n):
        index = -1
        trueindex = -1
        value = 1
        for j, k in enumerate(distancelist):
            if k[0] != -1:
                if k[0] < value:
                    trueindex = k[1]
                    value = k[0]
                    index = j
        closestlist.append([value, trueindex])
        distancelist[index][0] = -1
    return closestlist


# func to remove outliers in prices
def removeoutlierprices(pricedistancelist):
    total = 0
    for i in pricedistancelist:
        total += i[0]
    mean = total/len(pricedistancelist)
    difsqrtotal = 0
    for i in pricedistancelist:
        difsqrtotal += (i[0]-mean)**2
    standarddeviation = math.sqrt(difsqrtotal/len(pricedistancelist))
    relevanpricedistancelist = []
    for i in pricedistancelist:
        zscore = (i[0]-mean)/standarddeviation
        if zscore < 0.4:
            relevanpricedistancelist.append(i)
    return relevanpricedistancelist


# func to estimate value pre inflation
def getestimate(pricedistancelist):
    totalval = 0
    totaldiv = 0
    for i in pricedistancelist:
        price = i[0]
        distance = i[1]
        if distance == 0:
            distance = 0.01
        div = 1/distance
        val = price*div
        totalval += val
        totaldiv += div
    return totalval/totaldiv


# get test data
testData = pd.read_csv(r"HousePriceDataTEST.csv")

# assigns days to 2019 to all houses in test data
testData["Days to 2019"] = [nodaysto2019(x) for x in testData["Date"]]

estimatePriceList = []

# iterate through all houses in test data and get estimate
for i, row in testData.iterrows():
    print("House:", i)
    xIn = row["Latitude"]
    yIn = row["Longitude"]
    bedrooms = row["Bedrooms"]
    Df = bedroomDFDicList[bedrooms - 1]  # gets df for amount of bedrooms
    closeHouseList = gethousesaround(xIn, yIn, Df)  # gets list of closest houses
    # gets distances from house to houses in radius
    # [distance, index]
    distanceList = [[getdistance(xIn, yIn, k[1], k[2]), k[0]] for i, k in enumerate(closeHouseList)]
    closestHousesList = getnclosest(30, distanceList)  # gets 30 closest houses
    # swaps index to prices off houses
    # [price, distance]
    priceDistanceList = [[housingData.iloc[Df.iloc[i[1]]["OgIndex"]]["Adjusted Price"], i[0]] for i in closestHousesList]
    relevantPriceDistanceList = removeoutlierprices(priceDistanceList)
    estimate = getestimate(relevantPriceDistanceList)
    # adjust for inflation
    daysTo2019 = row["Days to 2019"]
    estimate = round(estimate/(daysTo2019**0.00011))
    estimatePriceList.append(estimate)

testData["Estimated Price"] = estimatePriceList

testData.to_csv(r'HousingDataWithEstimates.csv', index=False, header=True)
