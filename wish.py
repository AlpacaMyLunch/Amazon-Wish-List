import sys
import linecache
import json
import os
import time
import smtplib
import ssl
import re


from getpass import getpass
from random import randint
from bs4 import BeautifulSoup, SoupStrainer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

CHROME_DRIVER = None
CHROME_DRIVER_PATH = 'chromedriver.exe'

EMAIL_SENDER_ADDRESS = None
EMAIL_RECIPIENT_ADDRESS = None
EMAIL_PORT = None
EMAIL_CONTEXT = None
EMAIL_PASSWORD = ''

HOMEPAGE_URL = 'https://www.amazon.com'

WISH_LIST = []

# Keep track of the item's we've alerted on.
ALERTED_LIST = []

def Main():
    global CHROME_DRIVER
    global EMAIL_PASSWORD
    global EMAIL_SENDER_ADDRESS
    global EMAIL_RECIPIENT_ADDRESS
    global EMAIL_PORT
    global WISH_LIST

    try:
        email_config = JSONFromFile('email-config.json')
        EMAIL_SENDER_ADDRESS = email_config['sender address']
        EMAIL_RECIPIENT_ADDRESS = email_config['recipient address']
        EMAIL_PORT = email_config['port']

        EMAIL_PASSWORD = getpass('Password for {}: '.format(EMAIL_SENDER_ADDRESS))


        # Initialize Chromedriver
        InitChrome()
        Login()

        while True:

            LlamaPrint('Loading wish list...')
            OpenWishList()
            
            LlamaPrint('Scrolling to the bottom...')
            ScrollToBottom()

            LlamaPrint('Parsing...')
            ParseWishList()

            LlamaPrint('Verifying available items...')
            VerifyItemAvailability()

            LlamaPrint('Alerting...')
            AlertOnAvailableItems()

            JSONToFile('wish-list.json', WISH_LIST)
            JSONToFile('alerted.json', ALERTED_LIST)
            
            LlamaPrint('Waiting...')
            RandomPause(30, 300)

 

    except:
        PrintException()

    finally:
        if CHROME_DRIVER != None:
            CHROME_DRIVER.quit()
        exit()

def BuildEmailBody(items):
    output = {
        'plain': '',
        'html': ''
    }
    try:

        item_text_list = []
        for item in items:
            item_text = '<a href="{}{}">{}</a><br>${}'.format(HOMEPAGE_URL, item['url'], item['name'], item['price'])
            item_text_list.append(item_text)

        html = """\
            <html>
                <body>
                    <p>Items are available</p>
                    <br>
                    {}
                </body>
            </html>""".format("<br><br>".join(item_text_list))

        plain = """\
            Items are available.

            {}""".format("\n\n".join(item_text_list))

        output['plain'] = plain
        output['html'] = html
    except:
        PrintException()

    finally:
        return output


def SendEmail(subject, plain_text, html):
    global EMAIL_CONTEXT

    try:
        if EMAIL_CONTEXT == None:
            EMAIL_CONTEXT = ssl.create_default_context()

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_SENDER_ADDRESS
        message["To"] = EMAIL_RECIPIENT_ADDRESS
        part_1 = MIMEText(plain_text, 'plain')
        part_2 = MIMEText(html, 'html')
        message.attach(part_1)
        message.attach(part_2)


        
        with smtplib.SMTP_SSL('smtp.gmail.com', EMAIL_PORT, context=EMAIL_CONTEXT) as server:
            server.login(EMAIL_SENDER_ADDRESS, EMAIL_PASSWORD)
            LlamaPrint('Sending email...')
            server.sendmail(EMAIL_SENDER_ADDRESS, EMAIL_RECIPIENT_ADDRESS, message.as_string())
            LlamaPrint('Sent.')



    except:
        PrintException()


def AlertOnAvailableItems():
    global WISH_LIST
    global ALERTED_LIST

    try:
        available = []
        for item in WISH_LIST:
            if item['status'] == 'Available':
                if item['url'] not in ALERTED_LIST:
                    available.append(item)
                    LlamaPrint('Preparing to alert on {}'.format(item['name']))

        
        if len(available) > 0:
            body = BuildEmailBody(available)
            SendEmail('AMAZON ITEMS AVAILABLE', body['plain'], body['html'])
            for item in available:
                ALERTED_LIST.append(item['url'])


    except:
        PrintException()


def VerifyItemAvailability():
    global CHROME_DRIVER
    global WISH_LIST

    try:

        main_tab = CHROME_DRIVER.current_window_handle

        for item in WISH_LIST:
            if item['price'] != None:

                # item has a price.  Let's verify that it's available.
                LlamaPrint('Verifying {}...'.format(item['name']))
                CHROME_DRIVER.execute_script('window.open("{}","_blank");'.format(HOMEPAGE_URL + item['url']))
                RandomPause(10, 15)
                new_tab_handle = CHROME_DRIVER.window_handles[1]
                CHROME_DRIVER.switch_to.window(new_tab_handle)
                buy_box = CHROME_DRIVER.find_element_by_id('buybox')
                buy_box_html = buy_box.get_attribute('outerHTML')
                if 'Prioritized for organizations' in buy_box_html:
                    item['status'] = 'Prioritized for organizations'
                elif 'Currently unavailable.' in buy_box_html:
                    item['status'] = 'Currently unavailable'
                elif 'Add to Cart' in buy_box_html:
                    item['status'] = 'Available'
                else:
                    item['status'] = 'Unknown'

                
                # close that tab
                CHROME_DRIVER.close()

                # switch back to main tab
                CHROME_DRIVER.switch_to.window(main_tab)
                RandomPause(1, 5)
            else:
                item['status'] = 'Currently unavailable.'


    except:
        PrintException()



def ParseWishList():
    # Break down all of the wish list items into a JSON object
    global CHROME_DRIVER
    global WISH_LIST
    current_list = []

    try:
        main_div = CHROME_DRIVER.find_element_by_id('content-right')
        item_div = main_div.find_element_by_id('wl-item-view').find_element_by_id('item-page-wrapper')
        item_list = item_div.find_element_by_id('g-items')

        html = item_list.get_attribute('outerHTML')
        soup = BeautifulSoup(html, 'html.parser')

        list_items = soup.find_all('li')

        # Gather all of those items on the wish list right now
        for item in list_items:

            price = item.get('data-price')
            if price == '-Infinity':
                price = None

            details_div = item.find('div', {'id': re.compile('itemInfo_')})
            name_link = details_div.find('a', {'id': re.compile('itemName_')})
            product_url = name_link.get('href')
            name = name_link.get('title')
            current_list.append({
                'name': name,
                'price': price,
                'url': product_url
            })


        # Let's add new items to our WISH_LIST variable
        # and let's remove any items from the WISH_LIST that are not on this current_list

        # add new:
        for item in current_list:
            if IsURLInList(item['url'], WISH_LIST) == False:
                WISH_LIST.append(item)


        # remove:
        for item in WISH_LIST:
            url = item['url']
            if IsURLInList(url, current_list) == False:
                WISH_LIST[:] = [d for d in WISH_LIST if d.get('url') != url]


    except:
        PrintException()


def ScrollToBottom():
    # Need to scroll to the bottom of the page to load all items
    global CHROME_DRIVER
    try:
        scrolls = 4
        while True:
            CHROME_DRIVER.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            scrolls -= 1
            time.sleep(5)
            if scrolls == 0:
                break


    except:
        PrintException()

def OpenWishList():
    global CHROME_DRIVER

    try:
        nav_div = CHROME_DRIVER.find_element_by_id('nav-belt')
        accounts_and_lists_menu = nav_div.find_element_by_id('nav-link-accountList')
        hover = ActionChains(CHROME_DRIVER).move_to_element(accounts_and_lists_menu)
        hover.perform()
        RandomPause(3, 8)

        wish_list_link = CHROME_DRIVER.find_element_by_xpath("//a[contains(@href, 'type=wishlist')]")
        wish_list_link.click()


    except:
        PrintException()

def Login():
    global CHROME_DRIVER

    try:
        FetchPage(HOMEPAGE_URL)


        # Click the "Account & Lists" link in the top nav
        nav_div = CHROME_DRIVER.find_element_by_id('nav-belt')
        accounts_and_lists_menu = nav_div.find_element_by_id('nav-link-accountList')
        accounts_and_lists_menu.click()


        # email_input_box = CHROME_DRIVER.find_element_by_id('ap_email')
        # continue_button = CHROME_DRIVER.find_element_by_id('continue')

        # # Input email address and click continue
        # email_address = input('Email address: ')
        # email_input_box.send_keys(email_address)
        # continue_button.click()
        # time.sleep(1)
        
        
        # password_input_box = CHROME_DRIVER.find_element_by_id('ap_password')
        # sign_in_button = CHROME_DRIVER.find_element_by_id('signInSubmit')

        # # Input password and click sign-in
        # password = getpass.getpass('Password: ')
        # password_input_box.send_keys(password)
        # sign_in_button.click()
        

        # I've commented out the code above and am replacing it with this.
        # The user will handle login manually and press ENTER for this script to continue.
        # Reason:  I don't want to handle 2FA
        wait = input('Press ENTER after login is complete')
        

        # Let's wait an additional __ seconds
        # To make sure things have loaded and so our activity isn't too quick
        RandomPause(3, 10)


    except:
        PrintException()

def FetchPage(url):
    # perform a GET request to a page.
    # Wait an extra __ seconds to avoid detection

    global CHROME_DRIVER
    CHROME_DRIVER.get(url)
    RandomPause(3, 15)

def InitChrome():
    global CHROME_DRIVER
    chrome_options = Options()
    chrome_options.add_argument('--log-level=3') 
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--no-sandbox')
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-gpu")
    
    CHROME_DRIVER = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)

    # Let's slow the script down even more to avoid detection
    # Wait __ seconds when doing a find_element before continuing
    CHROME_DRIVER.implicitly_wait(2)

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    file_name = f.f_code.co_filename
    linecache.checkcache(file_name)
    line = linecache.getline(file_name, lineno, f.f_globals)
    print ('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(file_name, lineno, line.strip(), exc_obj))

def JSONFromFile(file_name):
    with open(file_name) as json_file:
        json_data = json.load(json_file)
    return json_data

def JSONToFile(file_name, json_data):
    with open(file_name, 'w') as out_file:
        json.dump(json_data, out_file)

def RandomPause(min = 1, max = 30):
    # Use this to pause the script for a random number of seconds.

    value = randint(min, max)
    # LlamaPrint('Sleep {} seconds...'.format(value))
    time.sleep(value)

def IsURLInList(url, lst):
    # Item names might not be unique but the URL's probably are

    for item in lst:
        if item['url'] == url:
            return True

    return False

def LlamaPrint(msg: str):
    last_msg_length = len(LlamaPrint.last_msg) if hasattr(LlamaPrint, 'last_msg') else 0
    print(' ' * last_msg_length, end='\r')
    print(msg, end='\r')
    sys.stdout.flush()  
    LlamaPrint.last_msg = msg

if __name__ == '__main__':
    Main()