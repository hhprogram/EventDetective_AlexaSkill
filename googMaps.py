import urllib.request
import logging
import json
from htmlParser import strip_tags


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
''' example urls for using google maps' api: (2nd dist matrix gets duration with current traffic 
    guess)
https://maps.googleapis.com/maps/api/directions/json?origin=37.783333,%20-122.416667&destination=37.333333,%20-121.9&key=AIzaSyAIWbGu_S_zvIZAzsV3XF1nHpg_62cRaaU
https://maps.googleapis.com/maps/api/directions/json?origin=Toronto&destination=Montreal&key=AIzaSyAIWbGu_S_zvIZAzsV3XF1nHpg_62cRaaU
https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins=San+Jose,CA&destinations=Berkeley,CA&key=AIzaSyBb-UtsS15upvaao9KxxYS59wuOgq9NR_k
https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins=2020%20bancroft%20way%20berkeley&destinations=1192%20Market%20St,%20San%20Francisco,%20CA%2094102&key=AIzaSyBb-UtsS15upvaao9KxxYS59wuOgq9NR_k&mode=driving&traffic_model=best_guess&departure_time=now
https://maps.googleapis.com/maps/api/staticmap?size=512x512&maptype=roadmap&markers=size:mid%7Ccolor:red%7C2020+Bancroft+way+berkeley+CA%7C2020+Oregon+St+Berkeley+CA&key=AIzaSyCFSh4EWOwcR2Rvfd_uUfIi-DeF025YUB8
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
g_api_base_url = "https://maps.googleapis.com/maps/api/"
goog_dir_key = "&key=AIzaSyAIWbGu_S_zvIZAzsV3XF1nHpg_62cRaaU"
goog_dis_key = "&key=AIzaSyBb-UtsS15upvaao9KxxYS59wuOgq9NR_k"
goog_static_map_key = "&key=AIzaSyCFSh4EWOwcR2Rvfd_uUfIi-DeF025YUB8"
# --- google static map api
static_url = "staticmap?size="
map_type_url = "&maptype="
marker_url = "&markers=size:mid%7Ccolor:red%7C"
small_marker_url = "&markers=size:small%7Ccolor:red%7C"
map_concat = "%7C"

dis_url = "distancematrix/json?units="
dir_url = "directions/json?"
traffic_url = "&traffic_model="
depart_url = "&departure_time="
trans_url = "&mode="
units_i = "imperial"
units_m = "metric"
or_dis_url = "&origins="
des_url = "&destinations="
# keys to various json dicts from api results
rows_key = "rows"
elements_key = "elements"
distance_key = "distance"
duration_key = "duration"
duration_traf_key = "duration_in_traffic"
text_key = "text"
value_key = "value"
fare_key = "fare"
routes_key = "routes"
legs_key = "legs"
steps_key = "steps"
instr_key = "html_instructions"


def find_distance(start, end, transit_mode=None):
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
    print(dis_url)
    json_response = json.loads(urllib.request.urlopen(dis_url).read().decode('utf-8'))
    travel_info = json_response[rows_key][0][elements_key][0]
    distance = travel_info[distance_key][text_key]
    if duration_key in json_response:
      duration = travel_info[duration_traf_key][text_key]
    else:
      duration = travel_info[duration_key][text_key]
    cost = None
    if fare_key in travel_info:
        cost = travel_info[fare_key]
    return duration, distance, cost


def find_directions(start, end, transit_mode=None):
    """
    Takes advantage of html parser as google directions api returns instructions in html. So want
    to strip all html tags and just return text
    Returns:
      A list of text instructions from start to end
    """
    dir_url = build_url(start, end, transit_mode)[0]
    json_response = json.loads(urllib.request.urlopen(dir_url).read().decode('utf-8'))
    route_legs = json_response[routes_key][0][legs_key]
    directions = []
    for leg in route_legs:
        for step in leg[steps_key]:
            directions.append(strip_tags(step[instr_key]))

    return directions


def find_map(start, end, *otherlocs):
  """
  builds the url to get the static map. puts a marker on the start and end locations. assumes start
  and end are in a format / have enough info to give a proper location. does clean white spaces tho
  Args:
    START: starting location
    END: end location
    OTHERLOCS: potential other waypoints or locations that we want to put markers one
  Returns:
    URL for static map
  """
  small = "200x200"
  large = "512x512"
  start = start.replace(" ","+")
  end = end.replace(" ","+")
  small_url = g_api_base_url + static_url + small + map_type_url + small_marker_url + start + map_concat + end
  big_url = g_api_base_url + static_url + large + map_type_url + marker_url + start + map_concat + end
  for loc in otherlocs:
    loc = loc.replace(" ", "+")
    small_url += loc
    big_url += loc
  small_url += goog_static_map_key
  big_url += goog_static_map_key
  return small_url, big_url


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
    traffic = "best_guess"
    depart = "now"
    if transit_mode:
        transit = transit_mode
    direc_url = g_api_base_url + dir_url + "origin=" + start + "&destination=" + end + trans_url \
        + transit + goog_dir_key
    dist_url = g_api_base_url + dis_url + units_i + or_dis_url + start + des_url + end + trans_url \
        + transit + traffic_url + traffic + depart_url + depart + goog_dis_key
    direc_url = direc_url.replace(" ","+")
    print("directions :"+ direc_url)
    dist_url = dist_url.replace(" ","+")
    return direc_url, dist_url


def get_all_map_info(start, end, transit_mode=None):
    """
    Calls all the map methods and returns a tuple with all the info
    Returns:
        (result from find_distance, results from find_directions, results from static_map)
    """
    directions = find_directions(start, end, transit_mode)
    distance = find_distance(start, end, transit_mode)
    static_map = find_map(start, end)
    return (distance, directions, static_map)


# # then i decode the bytes into a JSON formated STR which i then load into a JSON object using
# # the loads() method. acts like a JSON object in which it is a dictionary and can refer to its 
# # keys and the value is the corresponding value in the JSON response. Remember the values 
# # in a JSON response are always str
# json_output = json.loads(response.read().decode('utf-8'))
# print(json_output.keys())
# print(len(json_output['routes'][0]['legs']))
if __name__ == "__main__":
  start = "2020 Bancroft way, berkeley"
  end = "1700 steiner san francisco"
  transit = "transit"
  print(get_all_map_info(start, end,transit))

