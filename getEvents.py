import urllib.request
import logging
import json
import datetime
from googMaps import find_directions
import requests
logging.basicConfig(filename='example.log',level=logging.DEBUG)


# Will use eventful to efficiently get events that have actual locations / venues

# --- Strings for the base of the apis to be used
eventful = "http://api.eventful"

# ---Strings for API url request
event_search_base_url = "http://api.eventful.com/json/events/search?"
categories_base_url = "http://api.eventful.com/json/categories/list?"
api_key = "&app_key=q3xRBWBq5WJc3qcG"
loc_url = "location="
# can use this to limit the number of events we get back in our output as the actual JSON object 
# is just one page of the actual full results. Therefore if we want to 'scroll' through all results
# then need to retrieve other pages. the 'page_count' key in the response tells you how many pages
# there are given the page_size. Defaults to 10 per page if page_size not given in API request
events_per_pg_url = "&page_size="
# query keyword that can be used to filter searches for certain date ranges
date_url = "&date="
sort_url = "&sort_order="
within_url = "&within="
category_url = "&category="
ex_category_url = "&ex_category="
page_url = "&page_number="
keyword_url = "&keywords="

img_sizes = ["large", "medium", "thumb", "small"]
sort_options = {0: "popularity", 1: "date", 2: "relevance"}


# --- strings for the keys in the JSON response
events_key = "events"
event_key = "event"
url_key = "url"
cat_key = "category"
id_key = "id"
# ---strings for the keys in each event dict
title_key = "title"
start_key = "start_time"
stop_key = "stop_time"
venue_key = "venue_name"
venue_addr_key = "venue_address"
city_key = "city_name"
image_key = "image"
description_key = "description"
latitude_key = "latitude"
longitude_key = "longitude"
region_key = "region_abbr"
postal_key = "postal_code"
name_key = "name"
url_key = "url"


"""
Notes: on general output structure from the eventful API for JSON output

Note: some events don't have stop times in JSON response which matches the listing on the actual
posting see example:
http://sanfrancisco.eventful.com/events/restore-habitat-sf-zoo-/E0-001-101047656-5?utm_source=apis&utm_medium=apim&utm_campaign=apic



For Event Search API request:
key (in outer most dict): 'events' - a dictionary with a single key 'event'
    key (in the dict object contained under the 'events' key): 'event' a list of dictionary objects
        each dict object is a single event. This dict holds info about the event. Example keys for 
        each event dict is 'description', 'title', 'region_name'
        for more see: http://api.eventful.com/docs/events/search

"""

def get_time_period(time_period=None):
    """
    Helper method that will be called in the onIntent method when matching if user says 'this week'
    or 'this weekend' etc..
    Note: date object has method weekday() that gets weekday in int form 0-6 (Mon-Sun)
    Note: replace() on date object takes optional argument on what attribute of date object you want
        to replace
    Defaults to this week time period
    Note: Only dealing with DATE objects thus they only have 3 attributes (no time attributes)

    Returns:
        Tuple (start date, end date) (date objects)
        if argument left as None then returns the time periods that are currently supported
    """
    if not time_period:
        return ['this week...which is today through Sunday'
            , 'next week....which is the up coming Monday through Sunday'
            , 'this month...today through the end of this month']
    today = datetime.date.today()
    weekday = today.weekday()
    if time_period == "this week":
        date_start = today
        delta = datetime.timedelta(days=(6-weekday))
        date_end = today + delta
        return (date_start, date_end)
    elif time_period == "next week":
        delta_to_mon = 7 - weekday
        date_start = today + datetime.timedelta(days=delta_to_mon)
        date_end = date_start + datetime.timedelta(days=6)
        return (date_start, date_end)
    elif time_period == "this month":
        copy_today = datetime.date(today.year, today.month, today.day)
        date_start = today
        next_month = copy_today.replace(day=28) + datetime.timedelta(days=4)
        delta = datetime.timedelta(next_month.day)
        date_end = next_month - delta
        return (date_start, date_end)
    else:
        date_start = today
        delta = datetime.timedelta(days=(6-weekday))
        date_end = today + delta
        return (date_start, date_end)

def get_categories():
    """
    Gets all the categories from the eventful API
    Returns:
        A list of the ID strings sorted in Alpha order
    """
    search_url = categories_base_url + api_key
    response = urllib.request.urlopen(search_url)
    json_output = json.loads(response.read().decode('utf-8'))
    categories = []
    for cat in json_output[cat_key]:
        categories.append(cat[name_key])

    return sorted(categories)


def build_eventful_url(city, mile_radius=25, page_size=10, sort_order=sort_options[0]
        , date_start=None, date_end=None, cat=None, excl_cat=False, keyword=""):
    """
    Method that pings the eventful API and returns events near CITY within MILE_RADIUS 
    Args:
        city - string representing the city we are curious in
        date_start - assumes they are DATE objects 
        date_end - assumes they are DATE objects
        cat -list of strings (that should be the category ids that eventful understands)
        excl_cat - boolean, denotes if the CAT list is categories to filter on or exclude out
    Returns:
        the search URL constructed for eventful's api based on the arguments and a dict with 
        the keys being the query fields and the values being the values of those query fields

    """
    if date_start == None or date_end == None:
        logging.debug("Dates are none type - will just use FUTURE tag for date query field")
        date_field = "future"
    # assume if both are strs then formatted the correct way that eventful wants it other than
    # trailing zeros YYYYmmdd00-YYYY-mm-dd00
    elif isinstance(date_start, str) and isinstance(date_end, str):
         date_start += "00"
         date_end += "00"
         date_field = date_start + "-" + date_end
    else:
        # need some logic...if day is one digit then need to add 0 in front of it or else will not 
        # get desired date filtering behavior
        day = str(date_start.day)
        if len(day) == 1:
            day = "0"+day
        date_start_str = str(date_start.year) + str(date_start.month) + day + "00"
        day2 = str(date_end.day)
        if len(day2) == 1:
            day2 = "0"+day2
        date_end_str = str(date_end.year) + str(date_end.month) + day2 + "00"
        date_field = date_start_str + "-" + date_end_str
    if cat:
        print(cat)
        if excl_cat:
            cat_query = ex_category_url
            category = ','.join(cat)
        else:
            cat_query = category_url
            category = ','.join(cat)
    else:
        cat_query = category_url
        category = ''
    fields = {}
    fields['city'] = city
    fields['mile_radius'] = mile_radius
    fields['page_size'] = page_size
    fields['cat'] = cat
    fields['excl_cat'] = excl_cat
    fields['date_start'] = date_start
    fields['date_end'] = date_end

    # noticed trying to request URL via urllib with white spaces was given a 400 bad request. So 
    # needed to 'clean the url of all white spaces and replace with conventional + sign'
    clean_city = city.replace(" ","+")
    search_url = (event_search_base_url + loc_url + clean_city + within_url + str(mile_radius) + \
         api_key + events_per_pg_url + str(page_size) + sort_url + sort_order + cat_query + \
         category + date_url + date_field + keyword_url + keyword + page_url + "1")
    return search_url, fields

def get_events(url):
    """
    method given URL will actually return a list of dicts such that each dict hold details for a
    single event
    Returns:
        Dictionary of events. key - event titles (not necessarily unique), value is a dict of unique
         event ids that then lead to dicts of that specific event ids specific info
    """
    # this returns a response object that i can read() or readline() - which returns bytes
    response = urllib.request.urlopen(url)
    response = requests.get(url)
    print(response.status_code, response.text)
    if not response.text:
        print("response empty")
    else:
        print(response.text)
    # then i decode the bytes into a JSON formated STR which i then load into a JSON object using
    # the loads() method. acts like a JSON object in which it is a dictionary and can refer to its 
    # keys and the value is the corresponding value in the JSON response. Remember the values 
    # in a JSON response are always str
    json_output = response.json()
    full_event_list = json_output[events_key][event_key]
    dict_events = {}
    for event in full_event_list:
        if event[title_key] not in dict_events:
            dict_events[event[title_key]] = {event[id_key]: get_event_details(event)}
        else:
            dict_events[event[title_key]][event[id_key]] = get_event_details(event)
    return dict_events

def get_event_details(event):
    """
    Args:
        event - a dict for one specific event
    Returns:
        a dict. Where the key 'overview' holds values to be listed only when generally listing the 
        events via audio / card. Then 'details' key leads to another dict with key-value pairs with
        more essential details
    """
    general = {}
    general['overview'] = {}
    general['details'] = {}
    general['location'] = {}
    location = general['location']
    overview_values = general['overview']
    details = general['details']
    overview_values[title_key] = event[title_key]
    overview_values[start_key] = event[start_key]
    overview_values[stop_key] = event[stop_key]
    details[venue_key] = event[venue_key]
    details[description_key] = event[description_key]
    details[image_key] = get_img(event)
    details[url_key] = event[url_key]
    location['lon'] = event[longitude_key]
    location['lat'] = event[latitude_key]
    # if either the addr or city is missing then don't construct an addr. Google distance api can 
    # properly search if just have addr and city. but with just addr could possibly get something 
    # that is totally in another state/city
    if not event[venue_addr_key] or not event[city_key]:
        location['full_address'] = ""
    else:
            location[venue_addr_key] = event[venue_addr_key] + "," + event[city_key] + "," \
                + event[region_key]
    return general

def get_img(event):
    """
    takes an event dictionary and then returns the largest picture url possible. prioritizes the 
    "thumb" image url before "small"
    Not used for now as eventful image url are not HTTPS Therefore alexa doesn't allow
    """
    img_dict = event[image_key]
    url = ""
    # if img_dict:
    #     for size in img_sizes:
    #         if size in img_dict:
    #             url = img_dict[size][url_key]
    #             return url
    return url


def get_page(url):
    """
    gets the page number from this url
    """
    domain = url[:i.find(".com")]
    if domain == eventful:
        # assumes page number query is the very last
        pos = url.find(page_url)
        page = int(url[pos+len(page_url):])
        return page

def find_duplicates(lst):
    """
    Returns:
        a set of duplicates found in the iterable lst
    """
    unique = set()
    dup = set()
    for el in lst:
        if el not in unique:
            unique.add(el)
        else:
            dup.add(el)
    return dup


class EventQuery():
    """
    A class for queries to the eventful API. Use this such that we can refer back to these queries
    and allow for easier navigation within app if user has follow up questions to the result 
    of the query
    """
    def __init__(self):
        """
        self.URLS is a dict that have key-value pairs. key: domain name of api, value: tuple
            (actual url, dict of query field values)
        self.API_GETS is the dictionary where the the key is the domain name of the api and the
            value is the function for that specific api
        self.INFO dict of return objects for each URL. key: domain name, value: return object of 
            events (for the eventful get_events is just a dict whose keys are individual event_ids)
        """
        self.urls = {}
        self.api_gets = {}
        self.info = {}


    def query_all_urls(self):
        """
        Queries all the URLs in self.urls. And stores the relevant info into self.INFO. overrides 
        any existing data if certain domains in self.INFO already have return objects in place
        """
        for domain in self.urls:
            self.info[domain] = self.api_gets[domain](self.urls[domain][0])

    def query_url(self, domain):
        """
        only queries specifc url. overrides any pre-existing data and also updates our self.URLS
        assumes the url/domain is already in the object
        """
        self.info[domain] = self.api_gets[domain](self.urls[domain][0])

    def add_query(self, url_obj):
        """
        Adds the domain / url key-value pair to self.URLS and the approrirate get method for that
        given domain
        """
        url = url_obj[0]
        domain = url[:url.find(".com")]
        self.urls[domain] = url_obj
        if domain == eventful:
            self.api_gets[domain] = get_events


    def _next_page(self, domain, prev=False):
        """
        method to increment the url owned by DOMAIN to the next page. so next time query is called
        it will grab the next page. or will go to previous page if PREV = true
        """
        if prev:
            count = -1
        else:
            count = 1
        page = get_page(self.urls[domain][0])
        if domain == eventful:
            self.urls[domain][0] = self.urls[domain][0].replace(page_url+str(page)
                , page_url+str(page+count))


    def see_more_results(self, domain, less=False):
        """
        helper function that calls _next_page for the user (as don't want user directly calling
        _next_page). Updates the self.info dict. Unless LESS = true then goes to previous page's
        results
        """
        self._next_page(domain)
        self.query_url(domain)

    def get_overview(self, domain):
        """
        a dict. key is the event title. value is another dict where the key - is the unique event
        id and then its value is the result of the get_details method
        """
        dom = self.info[domain]
        events = {}
        for event in dom:
            # must create the empty dict here. first did it in the inner loop and was incorrect as 
            # if there was an event title with multiple event ids then it would just recreate the 
            # dict and then I wouldn't have proper structure of a dict that had event ids as the 
            # keys as would always just have 1:1 relationship with the last event_id of the 
            # duplicated event title as the only key
            events[event] = {}
            for event_id in dom[event]:
                # print(event, event_id)
                # note can't create a key like this (events[event][event_id]) first need to create a
                # empty dict for events[event] and then add the key event_id to that
                events[event][event_id] = self.get_details(event, event_id, domain)
        return events


    def write_output(self, domain):
        """
        helper method to just see what results I've gotten for that DOMAIN
        """
        query_fields = self.urls[domain][1]
        # print(query_fields)
        with open("output.txt", 'w') as f:
            f.write("Url: " + self.urls[domain][0])
            f.write("\n")
            f.write("\n")
            f.write("Events within {} miles of {}".format(query_fields["mile_radius"]
                , query_fields["city"]))
            f.write("\n")
            # adding str() wrapper as some values of the JSON end up being NONE objects which cannot be
            # implicitly converted to strings 
            for event in self.info[domain]:
                overview = self.info[domain][event]['overview']
                for key in overview:
                    f.write(key + ": " + str(overview[key]))
                    f.write("\n")
                f.write("---\n")

    def get_details(self, event_title, event_id, domain):
        """
        Args:
            EVENT_ID: the event id we are interested in
            DOMAIN: the domain in which we got this event info
        Returns:
            list [start time, end time, venue name, description, venue_addr, event_url]
        """
        results = []
        results.append(self.info[domain][event_title][event_id]['overview'][start_key])
        results.append(self.info[domain][event_title][event_id]['overview'][stop_key])
        results.append(self.info[domain][event_title][event_id]['details'][venue_key])
        results.append(self.info[domain][event_title][event_id]['details'][description_key])
        results.append(self.info[domain][event_title][event_id]['location'][venue_addr_key])
        results.append(self.info[domain][event_title][event_id]['details'][url_key])
        return results

    def write_detail(self, domain, event_ids):
        """
        write the 'details' of an event
        Args:
            DOMAIN - the domain that we are searching within
            EVENT_IDS - list of event ids we want to find
        Returns:
            nothing. just outputs a file
        """
        with open("details.txt", 'w') as f:
            for event_id in event_ids:
                event = self.info[domain][event_id]
                for key in event['overview']:
                    f.write(key + ": " + str(event['overview'][key]))
                    f.write("\n")
                for key in event['details']:
                    f.write(key + ": " + str(event['details'][key]))
                    f.write("\n")
                f.write("---")
                f.write("\n")


    def find_event_id(self, domain, event_string):
        """
        Find the id for the corresponding event_string. Can return multiple event ids with same
        title
        Args:
            DOMAIN - the domain that we are searching within
            EVENT_STRING - the event title string we want to match
        Returns:
            a list of event ids
        """
        ids = []
        for key in self.info[domain]:
            event_title = self.info[domain][key]['overview'][title_key]
            if event_string == event_title:
                ids.append(key)
        return ids

if __name__ == "__main__":
    # city = input("What city do you what to look for events:")
    # events = get_events(city)
    # output = get_events("Indio", cat=["music"])
    # question = EventQuery()
    query = build_eventful_url("Berkeley", cat=["music", "sports","family_fun_kids"])[0]
    events = get_events(query)
    # print(events)
    # question.add_query(query)
    # question.query_all_urls()
    # question.write_output(eventful)
    # event_id = question.find_event_id(eventful, "Willie Nelson & Family")
    # question.write_detail(eventful, event_id)
    # print(question.urls)
    # print(question.api_gets)
    # print(question.info)
    # lst = get_categories()
    # with open("categories.txt", "w") as f:
    #     for cat in lst:
    #         f.write(cat)
    #         f.write("\n")