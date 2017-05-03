from getEvents import build_eventful_url, get_events

"""
(city, mile_radius=25, page_size=10, sort_order=sort_options[0]
        , date_start=None, date_end=None, cat=None, excl_cat=False, keyword="")
"""

def get_titles():
    cities = ["Berkeley,California", "San+Jose,California", "Los+Angeles,California"
        , "San+Diego,California", "Seattle, Washington", "New+York,New+York", "Chicago,Illinois"
        , "Houston,Texas", "Philadelphia,Pennsylvania", "Phoenix,Arizona", "San+Antonio,Texas"
        , "Dallas,Texas", "Austin,Texas", "Detroit,Michigan", "Boston,Massachusetts"
        , "Miami,Florida", "Portland,Oregon", "Milwaukee,Wisconsin", "Kansas+City,Missouri"
        , "Virginia+Beach,Virginia", "Raleigh,North+Carolina", "Colorado+Springs,Colorado"
        , "Omaha,Nebraska", "Minneapolis,Minnesota", "Las+Vegas,Nevada", "Stamford,Connecticut"]
    slot_examples = set()
    for city in cities:
        url = build_eventful_url(city, page_size=20)[0]
        events = get_events(url)
        for e_id in events:
            new_ex = events[e_id]['overview']["title"].split(" ")
            [slot_examples.add(word) for word in new_ex]
        print("Done with " + city + " got " + str(len(events)) + " events")
    return slot_examples

def write_output():
    examples = get_titles()
    with open("slot_examples.txt", "w") as f:
        for ex in examples:
            f.write(ex)
            f.write("\n")

write_output()