# What does it do?
This script logs into your Amazon account and checks if items in your "Wish List" are available.  If an item is found to be available the script will send an email with a link to the product.

# Why tho?
Finding cleaning supplies is very difficult right now.  I have my wish list loaded with various out-of-stock cleaning supplies and hopefully this will alert me as soon as something becomes available.  I hope it will help you, too.

# Why is it so slow?
The script will frequently pause for a semi-random amount of time.  This is to avoid script/bot detection by Amazon.

# Getting Started

The script uses Gmail to send notifications.
1. [Python 3](https://www.python.org/downloads/)
2. Install dependencies (pip install -r requirements.txt)
3. Set up a burner Gmail account.
4. Turn [Allow less secure apps](https://myaccount.google.com/lesssecureapps) to ON.
5. Save that burner address into the email-config.json file.


# Running the script
The first thing that the script will do is ask for the password to the burner Gmail account you set up.  The password is not stored anywhere - just saved to a variable so the script can send an email when it finds an available item on your wish list.

Next, the script will open Amazon.com using it's own browser window.  After a pause of somewhere between 3 and 15 seconds (random) the script will then bring the browser to the login page.  From here you will manually log into your Amazon account from the browser.

The script is waiting for login to complete.  After you have finished logging into your Amazon account please return to the script and press ENTER.  This tells the script that you've finished and that it may now take over.

**IMPORTANT:  DO NOT USE THE BROWSER FOR OTHER PURPOSES.  JUST LET IT RUN IN THE BACKGROUND.**

The script will then loop through the following steps, with semi-random pauses between each step.

1. Open the Wish List
2. Scroll to the bottom (to make sure all items are loaded)
3. Parse the items on the Wish List
4. If an item on the Wish List has a price listed, visit the item's page to see if "Add to Cart" is an option.
5. If an item appears to be available, send an email to the address listed in the email-config.json file.
6. Save our current view of the Wish List to wish-list.json
7. Save a list of items we've emailed to alerted.json
8. Repeat.