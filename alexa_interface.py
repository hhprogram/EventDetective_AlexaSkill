from flask import Flask, render_template
from flask_ask import Ask, statement, question, session
import json
from getEvents import EventQuery, get_time_period, get_categories, build_eventful_url

app = Flask(__name__)
ask = Ask(app, "/WhatsGood")
eventquery = EventQuery()
api_domain = 'http://api.eventful'

@ask.launch
def skill_launch():
    welcome = render_template("welcome")
    return question(welcome)

@ask.intent("CityIntent")
def city_intent(city):
    session.attributes['city'] = city
    return question(render_template("timeQ", aval_time_periods=aval_periods_str))


@ask.intent("TimePeriodIntent")
def time_period(time_period):
    session.attributes['time'] = get_time_period(time_period)
    return question(render_template('categoryQ'))

@ask.intent("ListAvailableCategoriesIntent")
def category():
    aval_categories = get_categories()
    cat_str = "These are the available categories to choose from ..." + " ".join(aval_categories) \
        + ". Which one or ones would you like to choose to include or exclude?"
    return question(render_template("categorylist", categories=cat_str))

def str_to_list(categories):
    cat_lst = categories.split(",")
    if cat_lst == 'no':
        return None
    return cat_lst


@ask.intent("CategoryIntent", convert={'categories': str_to_list})
def filter_category(categories):
    if categories:
        session.attributes['cat'] = categories
    else:
        session.attributes['cat'] = None
    return question(render_template("radiusQ"))

@ask.intent("RadiusIntent")
def radius(dis):
    session.attributes['radius'] = dis
    params = session.attributes
    if 'city' in params and 'time' in params and 'cat' in params and 'radius' in params:
        url = build_eventful_url(params['city'], mile_radius=params['radius']
            , date_start=params['time'][0], date_end=params['time'][1], cat=params['cat'])
        eventquery.add_query(url)
        eventquery.query_url(api_domain)
        lst = eventquery.get_titles(api_domain)
        return question(render_template("response", events=lst))





