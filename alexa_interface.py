from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
import json
import logging
import datetime
from getEvents import EventQuery, get_time_period, get_categories, build_eventful_url

app = Flask(__name__)
ask = Ask(app, "/WhatsGood")
logging.getLogger("flask_ask").setLevel(logging.DEBUG)
eventquery = EventQuery()
api_domain = 'http://api.eventful'
# --- keys for the session.attributes dict
cat_attr = 'category'
time_attr = 'time'
city_attr = 'city'
radius_attr = 'radius'
# this is attribute for a session to keep track of which question was previously asked
last_attr = 'last_q'
attr_lst = [city_attr, time_attr, cat_attr, radius_attr]
titles_attr = "event_titles"
# mapping between the attributes and what template the user should be prompted with if that attr 
# doesn't have a value
attr_map = {cat_attr: "categoryQ", time_attr: "timeQ", city_attr: "missedInput"
    , radius_attr: "radiusQ"}

# --- defaults
cat_defaut = None
time_default = "this week"
radius_default = 25

"""
Note: each intent records the info that matches that intents name
2 ways to search:
(1) Q&A - (a) City, State (b) Time period (c) categories (d) radius
(2) Just say all of the above details in one sentence or at least (a) in one sentence 
"""

def attr_check():
    """
    helper function to check the session's attributes. If all are filled out returns True
    """
    if not session.attributes:
        return False
    for attr in attr_lst:
        if attr == cat_attr:
            if attr not in session.attributes:
                return False
        else:
            if attr not in session.attributes or session.attributes[attr] == None:
                return False
    return True

@app.route('/WhatsGood')
def home_page():
    return "The server is running..."


@ask.launch
def skill_launch():
    eventquery = EventQuery()
    welcome = render_template("welcome")
    session.attributes[last_attr] = city_attr
    card_title = render_template("welcomeTitle")
    card_txt = render_template("welcomeContent")
    return question(welcome).simple_card(title=card_title, content=card_txt)

@ask.intent("RestartIntent")
def clear():
    """
    Clear the current session's attributes and wait for another entirely new request
    """
    eventquery = EventQuery()
    session.attributes.clear()
    return question(render_template("restart"))

@ask.intent("PassIntent")
def pass_intent(all_info_call=False):
    """
    Populate the last question that was prompted with some default and then prompt the user with the
    next available question. If all session attributes filled out then return an answer. Unless
    it is city attribute then alexa will ask again
    Args:
        QUESTION: the last question asked
        ALL_INFO: arg to denote if all info intent called it or not if so, then don't return the 
            next question in the normal Q&A process
    Returns:
        nothing. but modifies the session.attributes dict
    """
    last_q = session.attributes[last_attr]
    if last_q != radius_attr:
        next_q = attr_lst[attr_lst.index(last_q) + 1]
    if last_q == city_attr:
        return question(render_template(attr_map[city_attr], input=city_attr))
    elif last_q == time_attr:
        date_tuple = get_time_period(time_default)
        session.attributes[time_attr] = str(date_tuple[0]), str(date_tuple[1])
    elif last_q == cat_attr:
        session.attributes[cat_attr] = cat_defaut
    elif last_q == radius_attr:
        session.attributes[radius_attr] = radius_default
    if attr_check():
        response = alexa_response()
        return question(response)
    if not all_info_call:
        # need to update the last_attr value as I won't be calling the actual intent function and 
        # thus I need to update the dict here as I'm just returning the same question object that 
        # the actual intent function would return but not going through that function's coder
        session.attributes[last_attr] = next_q
        return question(render_template(attr_map[next_q]))


@ask.intent("AMAZON.HelpIntent")
def help_intent():
    """
    Just prompts the user with the help template and then waits for an answer
    """
    return question(render_template("help"))

# note: the parameters have to have same syntax as the intent schema. Ie intent schema says there 
# are 2 slots for a city intent and those have names "City" and "State". Therefore the arguments to 
# this city intent. If i name them anything else - it will potentially cause me problems
@ask.intent("CityIntent")
def city_intent(City, State):
    """
    Triggered when user says city and state. Then we record those and then ask the next question in
    the Q&A process
    """
    logging.debug(str(City) + " " + str(State))
    if not City or not State:
        return question(render_template("missedInput"))
    session.attributes[city_attr] = City + "," + State
    if attr_check():
        response = alexa_response()
        return question(response)

    aval_periods_str = get_time_period()
    session.attributes[last_attr] = time_attr
    return question(render_template("timeQ", aval_time_periods=aval_periods_str))

# note: needed to change the date objects returns by get_time_period to strings because the
# attributes for a flask_ask session need to be JSON serializable and date objects are not
@ask.intent("TimePeriodIntent")
def time_period(timePeriod):
    """
    Triggered when the user says some sort of time frame. then asks next question in Q&A process
    """
    if not timePeriod:
        return question(render_template("missedInput", input=time_attr))
    date_tuple = get_time_period(timePeriod)
    session.attributes[time_attr] = (str(date_tuple[0]), str(date_tuple[1]))
    if attr_check():
        response = alexa_response()
        return question(response)
    session.attributes[last_attr] = cat_attr
    return question(render_template('categoryQ'))

# adding "..." between each category to make Alexa pause in between categories. Also, Alexa knows 
# how to say the special character &amp;
@ask.intent("ListAvailableCategoriesIntent")
def category():
    """
    Triggered when the user asks Alexa to list what are the categories
    """
    aval_categories = get_categories()
    cat_str = "These are the available categories to choose from ..." + "...".join(aval_categories)\
        + ". Which one or ones would you like to choose to include or exclude?"
    return question(render_template("categorylist", categories=cat_str))

@ask.intent("CategoryIntent")
def filter_category(cat, catTwo, catThree, catFour, catFive):
    """
    Triggered when user says no or 1 to five possible categories
    """
    final_cat = cat_lst_helper([cat, catTwo, catThree, catFour, catFive])
    session.attributes[cat_attr] = final_cat
    if attr_check():
        response = alexa_response()
        return question(response)
    session.attributes[last_attr] = radius_attr
    return question(render_template("radiusQ"))

@ask.intent("RadiusIntent")
def radius(number):
    """
    Triggered when user says something about the miles radius. Then assumes this should be end of 
    Q&A process and just checks to make sure all necessary attributes are done. If not, will
    ask user
    """
    if not number:
        return question(render_template("missedInput", input=radius_attr))
    session.attributes[radius_attr] = number
    params = session.attributes
    if attr_check():
        response = alexa_response()
        return question(response)
    for attr in attr_map:
        if attr not in session.attributes or session.attributes[attr] == None:
            session.attributes[last_attr] = attr
            if attr = city_attr:
                return question(render_template(attr_map[attr], input=attr))
            return question(render_template(attr_map[attr]))



@ask.intent("AllInfoIntent")
def all_info(timePeriod, cat, catTwo, catThree, catFour, catFive, number, City, State):
    """
    Triggered when user just wants to skip Q&A process and asks Alexa directly 
    """
    session.attributes[time_attr] = timePeriod
    session.attributes[radius_attr] = number
    session.attributes[cat_attr] = cat_lst_helper([cat, catTwo, catThree, catFour, catFive])
    if City == None:
        return question(render_template("missedInput"))
    else:
        session.attributes[city_attr] = City + "," + State
    if attr_check():
        response = alexa_response()
        return question(response)
    else:
        print("should")
        fill_missing_pieces()
        if not attr_check():
            logging.debug("Something is wrong in AllInfoIntent")
        response = alexa_response()
        return question(response)

@ask.intent("MoreInfoIntent")
def more_info(partOne, partTwo, partThree, partFour, partFive, partSix, partSeven, date):
    """
    Triggered when user asks for more detail on a specific event Alexa has said
    Broke into 6 possible parts this title could have that the user wants more details on
    and then a date if user also says the date after the event or the date if there are multiple
    events with the same title on different dates
    """
    lst = [partOne, partTwo, partThree, partFour, partFive, partSix, partSeven]
    # this is the count of actual words received by the Alexa. Used in tiebreaker situations when 
    # we have same %'s of the words in lst matching to the utterance (title + start date)
    # we use what % of words in lst matched
    # dbl list comprehension because after testing seems alexa often puts multiple words in one 
    # part. Thus want to break up those words and count them. the outer for loop is the first for 
    # on the left of list comprehension then we have the conditonal for it, then if conditonal is 
    # satisfied we go into the inner for loop
    words = [element for item in lst if item for element in item.split(" ")]
    inquiry_len = len(words)
    # iterable of results holds tuple (first % metric, tiebreaker metric, utterance, start date
        # , event_id - found in the eventquery object)
    results = []
    if inquiry_len == 0:
        return question(render_template("problem"))
    if session.attributes[titles_attr] == None:
        return question(render_template("noevents"))

    # loop through the attributes list which should have the top 10 results then match the words
    # and populate results
    for utterance, title, event_id, dt in session.attributes[titles_attr]:
        indices = set()
        matches = 0
        title_len = len(utterance.split(" "))
        for part in words:
            num = utterance.find(part)
            if num != -1 and num not in indices:
                indices.add(num)
                matches +=1
        percent_match = matches / title_len
        percent_match_inquiry = matches / inquiry_len
        results.append((percent_match, percent_match_inquiry, title, dt, event_id))
    # sorts results highest to lowest. Then we filter results to only include elements that have the
    # same values in percent_match and percent_match_inquiry to the first element (ie the most
        # highly % matched) basically looking to see if there are ties
    results = sorted(results, reverse=True)
    results = [triple for triple in results if triple[0]==results[0][0] and triple[1] == results[0][1]]
    # if there is a tie then we see if user said a date, and if any of the remaining results match 
    # in the date string we just assume they wanted that. If not match. Ask user to repeat
    # if only one then straight forward just return that one. 
    if len(results) > 1:
        print(results)
        for result in results:
            if result[3] == date:
                details = eventquery.get_details(result[4], api_domain)
                return question(render_template("detailResponse", title=clean([result[2]])
                    , start= details[0], end=details[1], venue=details[2], description=details[3]))
        return question(render_template("problem"))

    elif results:
        print(eventquery.urls)
        details = eventquery.get_details(results[0][4], api_domain)
        return question(render_template("detailResponse", title=clean([results[0][2]])
            , start= details[0], end=details[1], venue=details[2], description=details[3]))
    else:
        return question(render_template("problem"))


def cat_lst_helper(lst):
    """
    Returns:
        None if lst is full of None objects or returns a string of only the non-None objects. And 
        then if there is something to return concatenates them for you into a string with commas
        separating the elements
    """
    output = []
    for element in lst:
        if element:
            output.append(element)
    if not output:
        return None
    final_str = ""
    for el in output:
        final_str += el + ","
    return final_str



def fill_missing_pieces():
    """
    any attribute in the attributes dict that needs to be set to a default is
    """
    for attr in attr_lst:
        if session.attributes[attr] == None:
            session.attributes[last_attr] = attr
            pass_intent(all_info_call=True)

def clean(lst):
    """
    cleans the response list strings of any character alexa doesn't like (ie non valid SSML)
    """
    clean_lst = []
    for element in lst:
        new = element.replace("&", "and")
        clean_lst.append(new)
    return clean_lst

def alexa_response():
    """
    only called once alexa will be able to create a functioning URL for eventful api.
    Returns:
        a rendered template (not an actual question or statement object - actual question or 
            statement object returned by function that calls this one)
        modifies the session.attributes dict by adding a list of the event titles (sans start time)
    """
    params = session.attributes
    date_start_str = params[time_attr][0].split("-")
    date_end_str = params[time_attr][1].split("-")
    date_start = datetime.date(int(date_start_str[0]), int(date_start_str[1])
        , int(date_start_str[2]))
    date_end = datetime.date(int(date_end_str[0]), int(date_end_str[1])
        , int(date_end_str[2]))
    url = build_eventful_url(params[city_attr], mile_radius=params[radius_attr]
        , date_start=date_start, date_end=date_end, cat=params[cat_attr])
    # adds the url to the eventquery object
    eventquery.add_query(url)
    # queries that url to get info
    eventquery.query_url(api_domain)
    # gets a list of details for each event returned from that query
    lst = eventquery.get_overview(api_domain)
    clean_lst = clean([element[0] for element in lst])
    session.attributes[titles_attr] = lst
    # return question(render_template("testResponse"))
    return render_template("response", events=clean_lst)


if __name__ == "__main__":
    app.run(debug=True)
    # print("hello")



