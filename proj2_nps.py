#################################
##### Name: Tia Caldwell    
##### Uniqname: tiacc
#################################

from bs4 import BeautifulSoup
import requests
from requests import Session, Request
import json
import secrets # file that contains your API key

CACHE_FILENAME = "national_park_cache.json"
CACHE_DICT = {}

def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary. if the cache file doesn't exist, creates a new cache dictionary
    
    Parameters
    ----------
    None
    
    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk
    
    Parameters
    ----------
    cache_dict: dict
        The dictionary to save
    
    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 

def cache_or_request(url): 
    '''
     Pull html as text either by making a new request or accessing the cache 

    Parameters
    ----------
    url 
        str 
        The url of the page to scrape

    Returns
    -------
    str
        the returned value 
    '''

    cache_dict = open_cache()

    if url in cache_dict:  
        print("Using cache")
        return cache_dict[url]

    else: 
        print("Fetching")
        response = requests.get(url)
        cache_dict[url] = response.text
        save_cache(cache_dict)
        return cache_dict[url]

class NationalSite:
    '''a national site

    Instance Attributes
    -------------------
    category: string
        the category of a national site (e.g. 'National Park', '')
        some sites have blank category.
    
    name: string
        the name of a national site (e.g. 'Isle Royale')

    address: string
        the city and state of a national site (e.g. 'Houghton, MI')

    zipcode: string
        the zip-code of a national site (e.g. '49931', '82190-0168')

    phone: string
        the phone of a national site (e.g. '(616) 319-7906', '307-344-7381')
    '''
    def __init__ (self, category, name, address, zipcode, phone):
        self.category = category
        self.name = name
        self.address = address
        self.zipcode = zipcode 
        self.phone = phone

    def info(self):
        return self.name + " (" + self.category + "): " + self.address + " " + self.zipcode


def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "https://www.nps.gov"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
        e.g. {'michigan':'https://www.nps.gov/state/mi/index.htm', ...}
    '''
    base_url = "https://www.nps.gov"
    response = cache_or_request("https://www.nps.gov/index.htm")
    response_formatted = BeautifulSoup(response, 'html.parser') 

    html_section = response_formatted.find('ul', class_ = "dropdown-menu SearchBar-keywordSearch")
    html_urls = html_section.find_all('a')

    state_url_dict = {}
    for html_url in html_urls: 
        state_url = html_url['href']
        state_name = html_url.text
        state_url_dict[html_url.text.lower()] = base_url + state_url

    return state_url_dict

def get_site_instance(state_url):
    '''Make an instances from a national site URL.
    
    Parameters
    ----------
    state_url: string
        The URL for a national site page in nps.gov
    
    Returns
    -------
    instance
        a national site instance
    '''
    response = cache_or_request(state_url)
    response_formatted = BeautifulSoup(response, 'html.parser') 

    category = response_formatted.find('span',class_ = "Hero-designation").text.strip()
    name = response_formatted.find('a', class_ = "Hero-title").text.strip()
    try:
        address = response_formatted.find('span', itemprop = "addressLocality").text + ", " + response_formatted.find('span', itemprop = "addressRegion").text.strip()
    except: 
        address = "Missing address"
    try:
        zipcode = response_formatted.find('span', itemprop = "postalCode").text.strip()
    except:
        zipcode = ""
    phone = response_formatted.find('span', itemprop = "telephone").text.strip()

    return NationalSite(category,name,address,zipcode,phone)

def get_sites_for_state(state_url):
    '''Make a list of national site instances from a state URL.
    
    Parameters
    ----------
    state_url: string
        The URL for a state page in nps.gov
    
    Returns
    -------
    list
        a list of national site instances
    '''
    response = cache_or_request(state_url)
    response_formatted = BeautifulSoup(response, 'html.parser') 
    html_urls = response_formatted.find('div', id = "parkListResultsArea").find_all('h3')

    parks_url_list = []
    for html_url in html_urls: 
        park_url = html_url.find('a')['href']
        parks_url_list.append("https://www.nps.gov/" + park_url)
    
    parks_instances = []
    for url in parks_url_list:
        parks_instances.append(get_site_instance(url))

    return parks_instances

def get_nearby_places(site_object):
    
    '''Obtain API data from MapQuest API.
    
    Parameters
    ----------
    site_object: object
        an instance of a national site
    
    Returns
    -------
    dict
        a converted API return from MapQuest API
    '''
    
    base_url = "http://www.mapquestapi.com/search/v2/radius?"

    options = {
            'key' : secrets.API_KEY, 
            'origin': site_object.zipcode,
            'radius': '10', 
            'maxMatches': '10',
            'ambiguities': 'ignore',
            'outformat': 'json'} 

    #nearby_dict['options'] = options 
    nearby_dict = options
    nearby_dict['result_count'] = {}


    s = requests.Session()
    prepared = Request('GET', base_url, params=options).prepare()
    url = prepared.url 
    response = cache_or_request(url)
    api_response = json.loads(response)

   # nearby_dict['result_count'] = len(api_response['searchResults'])

    index = 1 
    for result in api_response['searchResults']:
    
        name = result['name']
        category = result['fields']['group_sic_code_name_ext']
        if category == "": category = "no category"
        address = result['fields']['address']
        if address == "": address = "no address"
        city = result['fields']['city']
        if city == "": city = "no city"

        nearby_dict['result_count'][index] = "- " + name + " (" + category +"): " + address +", " + city

        index = index +1 

    return nearby_dict

#MI_instances = get_sites_for_state("https://www.nps.gov/state/mi/index.htm")
#one_MI = MI_instances[0]
#near_MI = get_nearby_places(one_MI)
#print(near_MI['options'])
#print(near_MI)

def user_inut_to_list():

    ''' Prompt the user for a state, and then scrape all 
    national sites in that state from "https://www.nps.gov". 
    prints out list of sites.

    Parameters
    ----------
    None

    Returns
    -------
    None
    '''
    state = ""
    end_all = 0

    while True: 
        if end_all == 1: 
            break 

        state = input("\n Enter the name of a state or type 'exit': ")
        state_clean = state.lower().strip()

        if state_clean == "exit":
            break
        
        else: 
            try:
                dictonary_of_websites = build_state_url_dict()
                state_url = dictonary_of_websites[state_clean] #caching here 
                state_parks = get_sites_for_state(state_url) 

                print("-------------------------------------")
                print("List of National Sites in " + state_clean.title())
                print("-------------------------------------")

                park_number = 1
                for park in state_parks: 
                    print("[" + str(park_number) + "] " + park.info())
                    park_number = park_number + 1

                while True: 
                    park_num_input = input("\n Enter a park number to see nearby places, or type 'back' to find parks in a different state: ")
                    park_num_input_clean = park_num_input.lower().strip()
                    
                    if park_num_input_clean == "exit":
                        end_all = 1
                        break
                    
                    if park_num_input_clean == "back":
                        break

                    if (park_num_input_clean.isdigit() == False or int(park_num_input_clean) > (len(state_parks)) or int(park_num_input_clean) < 1):
                        print("\n ERROR. Accepts only an integer between 1 and " + str(len(state_parks)) + ",'back', or 'exit'. ")
                        continue 
                        

                    index = int(park_num_input_clean) -1
                    dict_of_places = get_nearby_places(state_parks[index])

                    print("\n -------------------------------------")
                    print("Places near " + state_parks[index].name)
                    print("-------------------------------------")

                    for counter in range(len(dict_of_places['result_count'])):
                        place_index = counter + 1 
                        print(dict_of_places['result_count'][place_index])
                        
            except: 
                print("\n ERROR. Accepts only a US state or 'exit'.")
                

if __name__ == "__main__":
   user_inut_to_list()

