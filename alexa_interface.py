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

@app.route('/WhatsGood')
def home_page():
    return "The server is running..."


@ask.launch
def skill_launch():
    welcome = render_template("welcome")
    return question(welcome)

# note: the parameters have to have same syntax as the intent schema. Ie intent schema says there 
# are 2 slots for a city intent and those have names "City" and "State". Therefore the arguments to 
# this city intent. If i name them anything else - it will potentially cause me problems
@ask.intent("CityIntent")
def city_intent(City, State):
    logging.debug(str(City) + " " + str(State))
    session.attributes['city'] = City + "," + State
    aval_periods_str = get_time_period()
    return question(render_template("timeQ", aval_time_periods=aval_periods_str))

# note: needed to change the date objects returns by get_time_period to strings because the
# attributes for a flask_ask session need to be JSON serializable and date objects are not
@ask.intent("TimePeriodIntent")
def time_period(timePeriod):
    date_tuple = get_time_period(timePeriod)
    session.attributes['time'] = (str(date_tuple[0]), str(date_tuple[1]))
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
    final_cat = ""
    cat_list = [cat, catTwo, catThree, catFour, catFive]
    for cat_element in cat_list:
        if cat_element:
            final_cat += cat_element + ","
    session.attributes['cat'] = final_cat
    return question(render_template("radiusQ"))

@ask.intent("RadiusIntent")
def radius(number):
    session.attributes['radius'] = number
    params = session.attributes
    if 'city' in params and 'time' in params and 'cat' in params and 'radius' in params:
        date_start_str = session.attributes['time'][0].split("-")
        date_end_str = session.attributes['time'][1].split("-")
        date_start = datetime.date(int(date_start_str[0]), int(date_start_str[1])
            , int(date_start_str[2]))
        date_end = datetime.date(int(date_end_str[0]), int(date_end_str[1])
            , int(date_end_str[2]))
        url = build_eventful_url(params['city'], mile_radius=params['radius']
            , date_start=date_start, date_end=date_end, cat=params['cat'])
        eventquery.add_query(url)
        eventquery.query_url(api_domain)
        lst = eventquery.get_overview(api_domain)
        return question(render_template("response", events=lst))

if __name__ == "__main__":
    app.run(debug=True)
    # print("hello")



