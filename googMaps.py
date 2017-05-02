import urllib.request
import logging
import json


# legs key in json is a list for each waypoint in the request. thus usually done if user wants to 
# stop over at multiple locations so each sequence of directions to each of these points would be 
# an entry in 'legs' list. Therefore, most common requests just have 1 leg
# each element within legs is a dict. With some top level keys giving some overview details of 
# the entire leg like distance and duration

# in the distancematrix google api (simplified JSON response with just duration and time). can
# enter a list of origins and list of destinations. response under key 'rows' is a list of 
# dicts where the key is "elements" and each "elements" key holds a list of dicts where the
# i-th dict is the distance and time from every location in the origins iterable to that specific
# i-th destination location in the destinations iterable

# routes key is a list for number of routes to and from these locations. Usually just 1
''' example urls for using google maps' api
https://maps.googleapis.com/maps/api/directions/json?origin=37.783333,%20-122.416667&destination=37.333333,%20-121.9&key=AIzaSyAIWbGu_S_zvIZAzsV3XF1nHpg_62cRaaU
https://maps.googleapis.com/maps/api/directions/json?origin=Toronto&destination=Montreal&key=AIzaSyAIWbGu_S_zvIZAzsV3XF1nHpg_62cRaaU
https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins=San+Jose,CA&destinations=Berkeley,CA&key=AIzaSyBb-UtsS15upvaao9KxxYS59wuOgq9NR_k
'''

"""
Sample distancematrix api response (note in our usage only ever doing one destination and 1 origin)
Note: if available in each elements dict there will be a key 'fare' that has the cost of the trip.
seems to not be that prevalent yet though
{
   "destination_addresses" : [ "Berkeley, CA, USA" ],
   "origin_addresses" : [ "Monterey, CA, USA" ],
   "rows" : [
      {
         "elements" : [
            {
               "distance" : {
                  "text" : "119 mi",
                  "value" : 191194
               },
               "duration" : {
                  "text" : "1 hour 59 mins",
                  "value" : 7161
               },
               "status" : "OK"
            }
         ]
      }
   ],
   "status" : "OK"
}
"""
goog_dir_key = "&key=AIzaSyAIWbGu_S_zvIZAzsV3XF1nHpg_62cRaaU"
goog_dis_key = "&key=AIzaSyBb-UtsS15upvaao9KxxYS59wuOgq9NR_k"
g_api_base_url = "https://maps.googleapis.com/maps/api/"
dis_url = "distancematrix/json?units="
dir_url = "directions/json?"
trans_url = "&mode="
units_i = "imperial"
units_m = "metric"
or_dis_url = "&origins="
des_url = "&destinations="
rows_key = "rows"
elements_key = "elements"
distance_key = "distance"
duration_key = "duration"
text_key = "text"
value_key = "value"
fare_key = "fare"


def find_directions(start, end, transit_mode=None):
    """
    method that calls the google maps API.
    Args:
        START: can be the starting location's addr or longitude and latitude
        END: can be the ending location's addr or longitude and latitude
        TRANSIT_MODE: field to tell maps API how I will be travelling to end location (defaults
                to NONE which will be taken as default to driving which is goog maps default)
    Returns:
        Tuple (duration, distance, cost)
        TBD: add another element for actual directions and google place details
    """
    dis_url = build_url(start, end, transit_mode)[1]
    json_response = json.loads(urllib.request.urlopen(dis_url).read().decode('utf-8'))
    travel_info = json_response[rows_key][0][elements_key][0]
    distance = travel_info[distance_key][text_key]
    duration = travel_info[0][duration_key][text_key]
    cost = None
    if fare_key in travel_info[0]:
        cost = travel_info[fare_key]
    return duration, distance, cost



def build_url(start, end, transit_mode):
    """
    builds urls for the directions and distance matrix apis
    Args:
        START: can be the starting location's addr or longitude and latitude
        END: can be the ending location's addr or longitude and latitude 
    Returns:
        Tuple (directions api url, distance api url). These urls are 'clean' s.t. blank spaces are 
        replaced by '+'s
    """
    transit = ""
    if transit_mode:
        transit = transit_mode
    dir_url = g_api_base_url + "origin=" + start + "&destination=" + end + trans_url + transit \
        + goog_dir_key
    dis_url = g_api_base_url + or_dis_key + start + des_key + end + trans_url + transit \
        + goog_dis_key
    dir_url = dir_url.replace(" ","+")
    dis_url = dis_url.replace(" ","+")
    return dir_url, dis_url



# # then i decode the bytes into a JSON formated STR which i then load into a JSON object using
# # the loads() method. acts like a JSON object in which it is a dictionary and can refer to its 
# # keys and the value is the corresponding value in the JSON response. Remember the values 
# # in a JSON response are always str
# json_output = json.loads(response.read().decode('utf-8'))
# print(json_output.keys())
# print(len(json_output['routes'][0]['legs']))