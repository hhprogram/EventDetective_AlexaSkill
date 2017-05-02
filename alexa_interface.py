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
cat_attr = 'cat'
time_attr = 'time'
city_attr = 'city'
radius_attr = 'radius'
# this is attribute for a session to keep track of which question was previously asked
last_attr = 'last_q'
attr_lst = [city_attr, time_attr, cat_attr, radius_attr]
# mapping between the attributes and what template the user should be prompted with if that attr 
# doesn't have a value
attr_map = {cat_attr: "categoryQ", time_attr: "timeQ", city_attr: "missedCity"
    , radius_attr: "radiusQ"}

# --- defaults
cat_defaut = None
time_default = "this week"
radius_default = 25

def attr_check():
    """
    helper function to check the session's attributes. If all are filled out returns True
    """
    if not session.attributes:
        return False
    for attr in attr_lst:
        if session.attributes[attr] == None:
            return False
    return True

@app.route('/WhatsGood')
def home_page():
    return "The server is running..."


@ask.launch
def skill_launch():
    welcome = render_template("welcome")
    session.attributes[last_attr] = city_attr
    return question(welcome)

@ask.intent("RestartIntent")
def clear():
    """
    Clear the current session's attributes and wait for another entirely new request
    """
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
        return question(render_template(attr_map[city_attr]))
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
    logging.debug(str(City) + " " + str(State))
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
    aval_categories = get_categories()
    cat_str = "These are the available categories to choose from ..." + "...".join(aval_categories)\
        + ". Which one or ones would you like to choose to include or exclude?"
    return question(render_template("categorylist", categories=cat_str))

@ask.intent("CategoryIntent")
def filter_category(cat, catTwo, catThree, catFour, catFive):
    final_cat = cat_lst_helper([cat, catTwo, catThree, catFour, catFive])
    session.attributes[cat_attr] = final_cat
    if attr_check():
        response = alexa_response()
        return question(response)
    session.attributes[last_attr] = radius_attr
    return question(render_template("radiusQ"))

@ask.intent("RadiusIntent")
def radius(number):
    session.attributes[radius_attr] = number
    params = session.attributes
    if attr_check():
        response = alexa_response()
        return question(response)
    for attr in attr_map:
        if attr not in session.attributes:
            return question(render_template(attr_map[attr]))


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


@ask.intent("AllInfoIntent")
def all_info(timePeriod, cat, catTwo, catThree, catFour, catFive, number, City, State):
    session.attributes[time_attr] = timePeriod
    session.attributes[radius_attr] = number
    session.attributes[cat_attr] = cat_lst_helper([cat, catTwo, catThree, catFour, catFive])
    if City == None:
        return question(render_template("missedCity"))
    else:
        session.attributes[city_attr] = City + "," + State
    if attr_check():
        response = alexa_response()
        return question(response)
    else:
        print("should")
        for attr in attr_lst:
            if session.attributes[attr] == None:
                session.attributes[last_attr] = attr
                pass_intent(all_info_call=True)
        if not attr_check():
            logging.debug("Something is wrong in AllInfoIntent")
        response = alexa_response()
        return question(response)

def alexa_response():
    params = session.attributes
    date_start_str = params[time_attr][0].split("-")
    date_end_str = params[time_attr][1].split("-")
    date_start = datetime.date(int(date_start_str[0]), int(date_start_str[1])
        , int(date_start_str[2]))
    date_end = datetime.date(int(date_end_str[0]), int(date_end_str[1])
        , int(date_end_str[2]))
    url = build_eventful_url(params[city_attr], mile_radius=params[radius_attr]
        , date_start=date_start, date_end=date_end, cat=params[cat_attr])
    eventquery.add_query(url)
    eventquery.query_url(api_domain)
    lst = eventquery.get_overview(api_domain)
    # return question(render_template("testResponse"))
    return render_template("response", events=lst)


if __name__ == "__main__":
    app.run(debug=True)
    # print("hello")



